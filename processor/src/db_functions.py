'''db_functions.py

Dumps metadata from .json file to PostgreSQL database with modular design and verbose logging.

Aug 2025'''
import os
import sys
import json
import sqlite3
import re
from datetime import datetime
from dotenv import load_dotenv

# ===== Utility Functions =====
def get_db_connection(db_config, verbose=False):
    """Create and return a database connection."""
    try:
        conn = sqlite3.connect("app/data/db.sqlite3")
        # use Write-Ahead-Logging (WAL)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        if verbose:
            print(f"[INFO] Connected to database {DB_CONFIG['dbname']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        return conn
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        raise e

def clean_text(text):
    """Remove null bytes and other problematic characters from text."""
    if not isinstance(text, str):
        return text
    try:
        # First, handle surrogate pairs by replacing them
        text = text.encode('utf-8', 'surrogatepass').decode('utf-8', 'replace')
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\uFFFD]', '', text)
        # Replace any remaining problematic Unicode characters
        text = text.encode('ascii', 'ignore').decode('ascii', 'ignore')
        return text
    except Exception as e:
        # If any error occurs during cleaning, return an empty string
        print(f"Warning: Error cleaning text: {str(e)}")
        return ""

def dump_metadata_to_db(json_filepath, db_config, verbose=False):
    '''Main function to update DB with metadata from a .json file.'''

    conn = get_db_connection(db_config=db_config, verbose=verbose)
    try:
        with conn.cursor() as cur:
            with open(json_filepath, "r") as f:
                data = json.load(f)
                # Prepare the SELECT statement to check for duplicate titles and uuids
                sql_check_duplicate = """
                    SELECT article_id FROM articles WHERE title = %s OR uuid = %s
                """
                                
                # Prepare the INSERT statement
                # We use to_timestamp() to convert the epoch number in the database
                sql_insert_articles = """
                    INSERT INTO articles (
                        uuid, title, date_submitted, date_scraped, tags, authors,
                        abstract, pdf_url, full_arxiv_url, full_text, keywords
                    ) VALUES (
                        %s, %s, %s, to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING article_id
                """
                
                # Upsert keywords: 
                #   if new, then insert; otherwise update count and append paper_id if exists
                sql_upsert_keywords = """
                    INSERT INTO keywords (keyword, definition, count, paper_references)
                    VALUES (%s, %s, 1, ARRAY[%s::text])
                    ON CONFLICT (keyword) 
                    DO UPDATE SET 
                        count = keywords.count + 1,
                        paper_references = array_append(keywords.paper_references, EXCLUDED.paper_references[1]);
                """
                
                # iterate through each paper in the JSON object's values
                for paper in data.values():
                    # handle definitions to ensure it's a dictionary and contains clean None values
                    definitions = paper.get('definitions', {})
                    if not isinstance(definitions, dict):
                        definitions = {}
                    
                    # clean up definitions dictionary
                    definitions = {
                        str(k).strip(): str(v) if v is not None else ''
                        for k, v in definitions.items()
                        if v != "None" and v is not None and k is not None
                    }

                    # skip insertion code if no valid definitions
                    if not definitions: 
                        continue
                    
                    # prepare data for insertion; handle potential None values and convert to lists
                    tags_list = []
                    if paper.get('tags') and isinstance(paper['tags'], str):
                        tags_list = [tag.strip() for tag in paper['tags'].split(',') if tag.strip()]
                    
                    authors_list = []
                    if paper.get('authors') and isinstance(paper['authors'], str):
                        authors_list = [author.strip() for author in paper['authors'].split(',') if author.strip()]
                    
                    keywords_list = []
                    if isinstance(paper.get('keywords'), str):
                        keywords_list = [kw.strip() for kw in paper['keywords'].split(',') if kw.strip()]
                    elif isinstance(paper.get('keywords'), (list, tuple)):
                        keywords_list = [str(kw).strip() for kw in paper['keywords'] if kw and str(kw).strip()]

                    # clean all string fields before insertion
                    clean_string = lambda x: clean_text(x) if isinstance(x, str) else x
                    clean_list = lambda lst: [clean_string(item) for item in lst] if isinstance(lst, list) else lst
                    
                    # assemble tuple of data in correct order for the SQL statement
                    data_to_insert = (
                        clean_string(paper.get('uuid', '')),
                        clean_string(paper.get('title', '')),
                        clean_string(paper.get('date_submitted')),
                        paper.get('date_scraped'),  # a generated number, no need to clean
                        clean_list(tags_list),
                        clean_list(authors_list),
                        clean_string(paper.get('abstract')),
                        clean_string(paper.get('pdf_url')),
                        clean_string(paper.get('full_arxiv_url')),
                        clean_string(paper.get('full_text')),
                        clean_list(keywords_list)
                    )

                    # check if article already exists in db via title and uuid
                    cur.execute(sql_check_duplicate, (paper.get('title', ''), paper.get('uuid', '')))
                    existing_article = cur.fetchone()
                    
                    if existing_article:
                        if verbose:
                            print(f"Skipping duplicate article: {paper.get('uuid', '')} {paper.get('title', '')}")
                            pass
                        continue
                    
                    # execute the insert statement for articles
                    cur.execute(sql_insert_articles, data_to_insert)
                    article_id = cur.fetchone()[0]
                    
                    # handle keywords for this paper
                    paper_uuid = paper.get('uuid', '')
                    for keyword, definition in definitions.items():
                        if not keyword or not isinstance(definition, str):
                            continue
                            
                        try:
                            keyword_data = (
                                keyword.strip(),
                                definition.strip(),
                                str(article_id),  # ensure is a string
                            )
                            cur.execute(sql_upsert_keywords, keyword_data)
                        except Exception as e:
                            print(f"Failed to insert keyword '{keyword}': {e}")
                            
                    if verbose:
                        print(f"Inserted article {paper_uuid} (ID: {article_id}) with {len(definitions)} keywords")

                # commit the transaction to make changes permanent
                conn.commit()
                print(f"==== Successfully inserted records.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to or interacting with PostgreSQL: {error}")
        if conn:
            conn.rollback() # roll back the transaction on error
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python db_functions.py <date>")
        sys.exit(1)
        
    load_dotenv()
    DB_CONFIG = {
        'dbname': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASS"),
        'host': 'localhost',
        'port': '5432'
    }
    dump_metadata_to_db(f"metadata/metadata_{sys.argv[1]}.json", db_config=DB_CONFIG, verbose=True)