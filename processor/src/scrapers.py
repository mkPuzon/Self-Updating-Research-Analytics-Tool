'''scrapers.py

Contains functions to get relevant research papers from the web. Currently can query:
- arXiv

Sep 2025
'''
import time
import uuid
import feedparser # parse/extract from RSS and Atom feeds
import urllib.request # opening URLs

def date_conv(date_str):
    year, month, day = date_str.split("-")
    return f"{year}{month}{day}0000"

def get_arxiv_metadata_batch(query, date, max_results=2):
    if " " in query:
        query = query.replace(" ", "+")

    # date_formatted = date_conv(date)
    # print(f"Date passed in query: {date}, {date_formatted}")
    request = f"http://export.arxiv.org/api/query?search_query=cat:{query}&sortBy=submittedDate&max_results={max_results}"
    # arXiv search by date: https://groups.google.com/g/arxiv-api/c/mAFYT2VRpK0?pli=1
    # request = f"http://export.arxiv.org/api/query?search_query=cat:{query}&submittedDate:[{date_formatted}+TO+{date_formatted}]&max_results={max_results}"
    
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

