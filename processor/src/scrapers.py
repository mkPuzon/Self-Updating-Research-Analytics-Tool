'''scrapers.py

Contains functions to get relevant research papers from the web. Currently can query:
- arXiv

Last updated: Jan 2026
'''
import time
import uuid
import feedparser # parse/extract from RSS and Atom feeds
import urllib.request # opening URLs

def date_conv(date_str):
    year, month, day = date_str.split("-")
    return f"{year}{month}{day}0000"

def get_arxiv_metadata_batch(query, max_results=2):
    if " " in query:
        query = query.replace(" ", "+")

    request = f"http://export.arxiv.org/api/query?search_query=cat:{query}&sortBy=submittedDate&max_results={max_results}"
   
    with urllib.request.urlopen(request) as url:
        response = url.read()
        
    feed = feedparser.parse(response) # returns a feedparser.util.FeedParserDict    
    
    records = {}
    paper_num = 0
    for entry in feed.entries:
        
        # get relevant info from feedparser and add to records list Python dict
        title = entry.title.strip()
        date_submitted = entry.published
        tags = ', '.join(t['term'] for t in entry.tags) if entry.tags else None
        abstract = entry.summary.strip()
        
        full_arxiv_url = entry.link
        pdf_url = None
        for link in entry.links:
            # PDF link is identified by rel="related" and title="pdf" 
            if link.get('title') == 'pdf' and link.get('rel') == 'related':
                pdf_url = link.get('href')
                break
        
        try:
            authors = ', '.join(author.name for author in entry.authors)
        except AttributeError:
            authors = entry.author
            
        records[paper_num] = {
            "uuid" : str(uuid.uuid4()),
            "title": title,
            "date_submitted": date_submitted[:10],
            "date_scraped": time.time(),
            "tags": tags,
            "authors": authors,
            "abstract": abstract,
            "pdf_url": pdf_url,
            "full_arxiv_url": full_arxiv_url,
            "full_text": None
        }   
        paper_num += 1
        
    return records

if __name__ == "__main__":
    
    def test_arxiv_scraper():
        max_results = 3
        records = get_arxiv_metadata_batch("cs.AI", max_results=max_results) 
        
        assert type(records) == dict
        assert list(records.keys()) == list(range(max_results))
        assert list(records[0].keys()) == ['uuid', 'title', 'date_submitted', 'date_scraped', 'tags', 'authors', 'abstract', 'pdf_url', 'full_arxiv_url', 'full_text']
        
        # working as expected; print info
        print(f"---- Number of papers scraped: {len(records)}")
        print(f"---- 'records' is a Python dictionary")
        print(f"---- Keys correspond to each paper's index: {records.keys()}")
        print(f"---- Each paper is a dictionary itself too; keys: {records[0].keys()}")
        print(f"---- Example entry:\n{records[0]}")
        print(f"\n---- NOTE: Here the 'full_text' attribute should be empty! It needs to be extracted from the pdf.")
        
    test_arxiv_scraper()