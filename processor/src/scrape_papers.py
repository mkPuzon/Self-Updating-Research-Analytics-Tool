'''scrape_papers.py

Scrapes papers using the scraper options in scrapers.py

Last updated: Jan 2026
'''
import os
import sys
import time
import json
import urllib.request
from docling.document_converter import DocumentConverter

# from pathlib import Path
from pypdf import PdfReader
from src.scrapers import get_arxiv_metadata

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
        print(f"[Error] downloading {pdf_url}: {e}")
        return False

def clean_text(text: str):
    
    if not text:
        return ""

    # --- 1. Remove control characters (except newline and tab) ---
    cleaned_chars = []
    for ch in text:
        code = ord(ch)
        if ch in ("\n", "\t") or code >= 32:
            cleaned_chars.append(ch)
    text = "".join(cleaned_chars)

    # --- 2. Normalize common Unicode punctuation ---
    replacements = {
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201C": '"',  # left double quote
        "\u201D": '"',  # right double quote
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2212": "-",  # minus sign
        "\u2026": "...",# ellipsis
        "\u00A0": " ",  # non-breaking space
    }

    for src, tgt in replacements.items():
        text = text.replace(src, tgt)

    # --- 3. Fix hyphenation at line breaks (e.g., "exam-\nple") ---
    lines = text.splitlines()
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1].lstrip()
            fixed_lines.append(line[:-1] + next_line)
            i += 2
        else:
            fixed_lines.append(line)
            i += 1
    text = "\n".join(fixed_lines)

    # --- 4. Normalize whitespace ---
    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")

    # Collapse excessive newlines (3+ → 2)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    # Strip leading/trailing whitespace
    text = text.strip()

    return text
    
def extract_text_pypdf(pdf_filepath: str):
    
    try:
        reader = PdfReader(pdf_filepath)
        clean_pages = []
        for page in reader.pages:
            lines = (page.extract_text() or "").splitlines()
            cleaned = [line for line in lines if len(line) >= 3]
            clean_pages.append("\n".join(cleaned))
        text = "\n".join(clean_pages)        
        return text
    
    except Exception as e:
        print(f"[Error] extracting text for {pdf_filepath}: {e}")
        
def extract_text_docling(pdf_filepath: str):
    
    try:
        doc = DocumentConverter().convert(pdf_filepath).document
        return doc.export_to_markdown()
    
    except Exception as e:
        print(f"[Error] extracting text for {pdf_filepath}: {e}")

def extract_text(metadata_dict: dict, pdf_save_dir: str, method: str = 'pypdf') -> None:
    '''Populates the passed metadata_dict with full paper texts.'''
    
    # extract text from each downloaded PDF using PyPDF
    for paper_id, info in metadata_dict.items():
        pdf_url = info.get("pdf_url")
        if pdf_url:
            arxiv_id = pdf_url.split('/')[-1]
            pdf_filename = f"{arxiv_id}.pdf"
            pdf_filepath = os.path.join(pdf_save_dir, pdf_filename)
            
            if os.path.exists(pdf_filepath):
                if method == 'pypdf':
                    text = extract_text_pypdf(pdf_filepath=pdf_filepath)
                    text = clean_text(text)
                elif method == 'docling':
                    text = extract_text_docling(pdf_filepath=pdf_filepath)
                else:
                    raise ValueError(f"[ERROR] Unknown text extraction method '{method}'. Valid options: 'pypdf', 'docling'")
                
                
                metadata_dict[paper_id]['full_text'] = text
    
def scrape_papers(query, date, max_results=2, method='pypdf', verbose=False):
    
    # date needed for naming conventions & storage
    try:
        year, month, day = date.split("-")
        date_clean = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        raise ValueError("Date must be in the form YYYY-MM-DD")
    
    pdf_save_dir = f"./data/pdfs/papers_{date_clean}"
    print(f"[DEBUG] Saving pdfs to {pdf_save_dir}")
    os.makedirs(pdf_save_dir, exist_ok=True)
    
    # get metadata
    metadata_dict = get_arxiv_metadata(query=query, max_results=max_results)
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
                time.sleep(3) # The arXiv API manual recommends a 3-second delay when calling the API multiple times
                try:
                    download_pdf(pdf_url, pdf_save_dir)
                except Exception as e:
                    print(f"[ERROR] Issue downloading PDF {pdf_url}: {e}")
                    num_pdfs -= 1
        else:
            if verbose: print(f"[WARNING] Skipping downloading paper {arxiv_id}, pdf already downloaded.")

    # extract text from each downloaded PDF
    extract_text(metadata_dict=metadata_dict, pdf_save_dir=pdf_save_dir, method=method)
    
    # save results from Python dict to JSON
    os.makedirs("./data/metadata", exist_ok=True)
    with open(f"./data/metadata/metadata_{date_clean}.json", "w") as f:

        json.dump(metadata_dict, f, indent=2)
        print(f"[DEBUG] Data saved to ./data/metadata/metadata_{date_clean}.json")

    return num_papers_metadata, num_pdfs
    
    
if __name__ == "__main__":
    import time
    
    def test_scraper_pipline():

        date = "2026-01-12"
        assert os.path.exists('metadata')

        print("---- Testing pypdf paper processing...")
        start = time.time()
        num_metadata, num_pdf = scrape_papers("cs.AI", date, max_results=3, method='pypdf',verbose=True)
        end = time.time() - start
        print(f"---- {num_metadata} metadata entries and {num_pdf} pdfs processed in {end:.2f}s!")

        print("\n---- Testing docling paper processing...")
        start = time.time()
        num_metadata, num_pdf = scrape_papers("cs.AI", date, max_results=3, method='docling', verbose=True)
        end = time.time() - start
        print(f"---- {num_metadata} metadata entries and {num_pdf} pdfs processed in {end:.2f}s!")