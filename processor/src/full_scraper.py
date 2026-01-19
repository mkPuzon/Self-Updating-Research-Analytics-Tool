'''full_scraper.py

Scrapes papers from arXiv using Python's urllib library while respecting rate limits.

Sep 2025
'''
import os
import sys
import time
import json
import urllib.request

from pathlib import Path
from pypdf import PdfReader
from scrapers import get_arxiv_metadata_batch

def download_pdf(pdf_url, save_dir, output_filename=None):
    
    if output_filename is None:
        try:
            # extract article ID from the URL path for use as the filename
            arxiv_id = pdf_url.split('/')[-1]
            output_filename = f"{arxiv_id}.pdf"
        except IndexError:
            print("Error: Could not derive filename from URL.")
            return False

    # print(f"Attempting to download PDF from: {pdf_url}")
    # print(f"Saving file as: {output_filename}")
    
    try:
        # download file and store locally; grabs file, not byte object
        urllib.request.urlretrieve(pdf_url, os.path.join(save_dir, output_filename))
        # print(f"Download successful! File saved at: {os.path.abspath(os.path.join(save_dir, output_filename))}")
        return True
    
    except Exception as e:
        print(f"Error downloading {pdf_url}: {e}")
        return False

def scrape_papers(query, date, max_results=2, verbose=False):
    # for naming conventions
    try:
        year, month, day = date.split("-")
        date_clean = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        raise ValueError("Date must be in the form YYYY_MM_DD")
    pdf_save_dir = f"../../mkpuzo-data/AURA_pdfs/papers_{date_clean}"
    os.makedirs(pdf_save_dir, exist_ok=True)
    
    # get metadata
    metadata_dict = get_arxiv_metadata_batch(query=query, date=date, max_results=max_results)
    num_papers_metadata = len(metadata_dict.keys())
    
    # download PDFs
    num_pdfs = num_papers_metadata
    for paper_id, info in metadata_dict.items():
        pdf_url = info.get("pdf_url")
        
        # if pdf doesn't already exist in the pdf_save dir folder:
        if pdf_url:
            arxiv_id = pdf_url.split('/')[-1]
            pdf_filename = f"{arxiv_id}.pdf"
            pdf_filepath = os.path.join(pdf_save_dir, pdf_filename)
            
            if not os.path.exists(pdf_filepath): 
                time.sleep(3) # The API manual recommends a 3-second delay when calling the API multiple times
                try:
                    download_pdf(pdf_url, pdf_save_dir)
                except Exception as e:
                    print(f"ERROR: Issue downloading PDF {pdf_url}: {e}")
                    num_pdfs -= 1
        else:
            if verbose: print(f"Skipping downloading paper {arxiv_id}, pdf already downloaded.")

    # extract text from each downloaded PDF using PyPDF
    for paper_id, info in metadata_dict.items():
        pdf_url = info.get("pdf_url")
        if pdf_url:
            arxiv_id = pdf_url.split('/')[-1]
            pdf_filename = f"{arxiv_id}.pdf"
            pdf_filepath = os.path.join(pdf_save_dir, pdf_filename)
            
            if os.path.exists(pdf_filepath):
                try:
                    reader = PdfReader(pdf_filepath)
                    clean_pages = []
                    for page in reader.pages:
                        lines = (page.extract_text() or "").splitlines()
                        cleaned = [line for line in lines if len(line) >= 3]
                        clean_pages.append("\n".join(cleaned))
                    text = "\n".join(clean_pages)        
                    metadata_dict[paper_id]["full_text"] = text
                except Exception as e:
                    print(f"Error extracting text for {arxiv_id}: {e}")
    
    # save results to JSON
    os.makedirs("./metadata", exist_ok=True)
    with open(f"./metadata/metadata_{date_clean}.json", "w") as f:
        json.dump(metadata_dict, f, indent=2)
        
    return num_papers_metadata, num_pdfs
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python full_scraper.py <date>")
        sys.exit(1)
    num_metadata, num_pdfs = scrape_papers(query="cs.AI", date=sys.argv[1], max_results=200, verbose=False)
    print(f"[{sys.argv[1]}] {(num_pdfs/num_metadata)*100:.2f}% of initial papers usable | {num_pdfs} full papers scraped | Metadata entries={num_metadata}, PDFs scraped={num_pdfs}")