'''scrapers.py

Contains functions to get relevant research papers from the web. Currently can query:
- arXiv

Last updated: Feb 2026
'''
import time
import uuid
import feedparser # parse/extract from RSS and Atom feeds
import urllib.request # opening URLs
import urllib.error

from typing import Dict, List, Tuple, Any
from src.logger_config import get_logger

logger = get_logger(__name__)

def date_conv(date_str):
    year, month, day = date_str.split("-")
    return f"{year}{month}{day}0000"

def get_arxiv_metadata(query: str, max_results: int = 2) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch paper metadata from arXiv API.

    Args:
        query: arXiv category query (e.g., "cs.AI")
        max_results: Maximum number of papers to fetch

    Returns:
        Tuple of (records_dict, errors_list)
        - records_dict: Dictionary mapping paper_id to metadata
        - errors_list: List of error dictionaries with context
    """
    errors = []

    if " " in query:
        query = query.replace(" ", "+")

    api_url = f"http://export.arxiv.org/api/query?search_query=cat:{query}&sortBy=submittedDate&max_results={max_results}"
    logger.info(f"Querying arXiv API", extra={"query": query, "max_results": max_results, "url": api_url})

    # fetch from arXiv 
    try:
        with urllib.request.urlopen(api_url, timeout=30) as url:
            response = url.read()
            logger.debug(f"arXiv API response received", extra={"size_bytes": len(response)})

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}: {e.reason}"
        logger.error(f"arXiv API HTTP error: {error_msg}", extra={"query": query, "url": api_url})
        errors.append({
            "type": "HTTPError",
            "message": error_msg,
            "query": query,
            "url": api_url
        })
        return {}, errors

    except urllib.error.URLError as e:
        error_msg = f"URL Error: {e.reason}"
        logger.error(f"arXiv API URL error: {error_msg}", extra={"query": query, "url": api_url})
        errors.append({
            "type": "URLError",
            "message": error_msg,
            "query": query,
            "url": api_url
        })
        return {}, errors

    except TimeoutError as e:
        error_msg = "Request timeout (30s)"
        logger.error(f"arXiv API timeout", extra={"query": query, "url": api_url})
        errors.append({
            "type": "TimeoutError",
            "message": error_msg,
            "query": query,
            "url": api_url
        })
        return {}, errors

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"arXiv API unexpected error: {error_msg}", extra={"query": query, "url": api_url})
        errors.append({
            "type": type(e).__name__,
            "message": error_msg,
            "query": query,
            "url": api_url
        })
        return {}, errors

    # parse response
    try:
        feed = feedparser.parse(response)
    except Exception as e:
        error_msg = f"Feed parsing error: {type(e).__name__}: {str(e)}"
        logger.error(f"Failed to parse arXiv response", extra={"error": error_msg})
        errors.append({
            "type": "ParseError",
            "message": error_msg,
            "query": query
        })
        return {}, errors

    # check for empty results
    if not hasattr(feed, 'entries') or len(feed.entries) == 0:
        logger.warning(f"No papers found for query", extra={"query": query})
        return {}, errors

    logger.info(f"Found {len(feed.entries)} papers from arXiv")

    # extract metadata from feed entries
    records = {}
    paper_num = 0
    for entry in feed.entries:
        try:
            # get relevant info from feedparser and add to records dict
            title = entry.title.strip() if hasattr(entry, 'title') else "Unknown Title"
            date_submitted = entry.published[:10] if hasattr(entry, 'published') else None
            tags = ', '.join(t['term'] for t in entry.tags) if hasattr(entry, 'tags') and entry.tags else None
            abstract = entry.summary.strip() if hasattr(entry, 'summary') else ""

            full_arxiv_url = entry.link if hasattr(entry, 'link') else None

            pdf_url = None
            if hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('title') == 'pdf' and link.get('rel') == 'related':
                        pdf_url = link.get('href')
                        break

            authors = None
            if hasattr(entry, 'authors'):
                try:
                    authors = ', '.join(author.name for author in entry.authors)
                except AttributeError:
                    authors = str(entry.authors) if entry.authors else None
            elif hasattr(entry, 'author'):
                authors = entry.author

            records[paper_num] = {
                "uuid": str(uuid.uuid4()),
                "title": title,
                "date_submitted": date_submitted,
                "date_scraped": time.time(),
                "tags": tags,
                "authors": authors,
                "abstract": abstract,
                "pdf_url": pdf_url,
                "full_arxiv_url": full_arxiv_url,
                "full_text": None
            }
            paper_num += 1

        except Exception as e:
            error_msg = f"Failed to parse entry: {type(e).__name__}: {str(e)}"
            logger.warning(f"Error parsing paper entry", extra={"paper_num": paper_num, "error": error_msg})
            errors.append({
                "type": "EntryParseError",
                "message": error_msg,
                "paper_num": paper_num
            })
            continue

    logger.info(f"Successfully parsed {len(records)} papers")

    return records, errors

if __name__ == "__main__":
    
    def test_arxiv_scraper():
        max_results = 3
        records = get_arxiv_metadata("cs.AI", max_results=max_results) 
        
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