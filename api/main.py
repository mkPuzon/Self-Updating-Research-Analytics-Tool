'''api/main.py

Allows the front end to query the SQLite database.

last updated: feb 2026
'''
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json
import ast  # generic parser for stringified lists

app = FastAPI()

# Allow Nginx to hit this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "/app/data/aura.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- HELPER: Parse the 'paper_references' column ---
# It's stored as TEXT, so we need to turn "['uuid1', 'uuid2']" into a real list
def parse_refs(ref_string):
    if not ref_string: return []
    try:
        # Try JSON first
        return json.loads(ref_string)
    except:
        try:
            # Try Python list syntax string
            return ast.literal_eval(ref_string)
        except:
            # Fallback to comma separation
            return [x.strip() for x in ref_string.split(',')]

# ---------------------------------------------------------
# 1. GET /terms (The River View)
# ---------------------------------------------------------
@app.get("/terms")
def get_terms(search: str = None):
    with get_db() as conn:
        cursor = conn.cursor()

        # We use SQLite's hidden 'rowid' to give the frontend the numeric ID it expects
        query = """
            SELECT rowid as id, keyword as term, definition, count 
            FROM keywords 
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (keyword LIKE ? OR definition LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Sort by count (importance) to show best terms first
        query += " ORDER BY count DESC LIMIT 50"

        cursor.execute(query, params)
        rows = cursor.fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "term": row["term"],
            "definition": row["definition"] or "No definition available.",
            "category": "Popular" if row["count"] > 5 else "Niche", # Derived category
        })
    
    return results

# ---------------------------------------------------------
# 2. GET /terms/{id} (The Detail/Overlay View)
# ---------------------------------------------------------
@app.get("/terms/{term_id}")
def get_term_details(term_id: int):
    with get_db() as conn:
        cursor = conn.cursor()

        # A. Get the Main Keyword Data
        cursor.execute("SELECT *, rowid as id FROM keywords WHERE rowid = ?", (term_id,))
        keyword_row = cursor.fetchone()

        if not keyword_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Term not found")

        # B. Find Associated Articles (Sources)
        # paper_references stores article_id integers (as strings)
        article_ids = parse_refs(keyword_row['paper_references'])

        sources = []
        rocks = [] # We'll use article tags as "Rocks"

        if article_ids:
            # Convert to ints for the query
            article_ids_int = [int(x) for x in article_ids]
            placeholders = ','.join(['?'] * len(article_ids_int))
            sql = f"SELECT title, abstract, tags, full_arxiv_url, date_submitted FROM articles WHERE article_id IN ({placeholders})"

            cursor.execute(sql, article_ids_int)
            articles = cursor.fetchall()

            for art in articles:
                # Map Article -> Source
                sources.append({
                    "title": art['title'],
                    "summary": (art['abstract'][:200] + "...") if art['abstract'] else "No abstract.",
                    "img": "https://placehold.co/100?text=PDF", # Placeholder or extract from PDF URL
                    "link": art['full_arxiv_url']
                })
                
                # Collect Tags for "Rocks"
                if art['tags']:
                    # Clean up tags (remove brackets/quotes if needed)
                    clean_tags = art['tags'].replace('[','').replace(']','').replace("'", "")
                    rocks.extend([t.strip() for t in clean_tags.split(',')])

        # C. Find Ripples (Related Keywords)
        # Simple logic: Find other keywords that appear in similar papers, 
        # OR just random popular ones for visual density if connections are sparse.
        cursor.execute("SELECT rowid as id, keyword as term FROM keywords WHERE rowid != ? ORDER BY RANDOM() LIMIT 5", (term_id,))
        ripples = [dict(row) for row in cursor.fetchall()]

    # Final JSON structure
    return {
        "id": keyword_row['id'],
        "term": keyword_row['keyword'],
        "definition": keyword_row['definition'],
        "category": "General",
        "sources": sources,
        "ripples": ripples,
        "rocks": [{"name": r} for r in list(set(rocks))[:5]] # Unique top 5 tags
    }