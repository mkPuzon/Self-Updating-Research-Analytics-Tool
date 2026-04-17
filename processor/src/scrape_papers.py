'''scrape_papers.py

Scrapes papers using the scraper options in scrapers.py

Last updated: Feb 2026
'''
import os
import sys
import time
import json
import urllib.request
from typing import Tuple, Optional, Dict, Any
from docling.document_converter import DocumentConverter

# from pathlib import Path
from pypdf import PdfReader
from src.scrapers import get_arxiv_metadata
from src.metrics import PipelineMetrics, ErrorCategory
from src.logger_config import get_logger

logger = get_logger(__name__)

def download_pdf(pdf_url: str, save_dir: str, output_filename: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Download a PDF from arXiv.

    Args:
        pdf_url: URL to the PDF file
        save_dir: Directory to save the PDF
        output_filename: Optional filename (defaults to arxiv_id.pdf)

    Returns:
        Tuple of (success: bool, error_message: str | None)
    """
    if output_filename is None:
        try:
            # extract article ID from the URL path for use as the filename
            arxiv_id = pdf_url.split('/')[-1]
            output_filename = f"{arxiv_id}.pdf"
        except IndexError:
            error_msg = "Could not derive filename from URL"
            logger.error(f"Failed to parse arxiv_id from URL: {pdf_url}")
            return False, error_msg

    save_path = os.path.join(save_dir, output_filename)
    logger.debug(f"Attempting to download PDF from: {pdf_url}")

    try:
        # download file and store locally; grabs file, not byte object
        urllib.request.urlretrieve(pdf_url, save_path)
        logger.info(f"Downloaded PDF successfully", extra={"arxiv_id": output_filename.replace('.pdf', ''), "url": pdf_url})
        return True, None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Failed to download PDF: {error_msg}", extra={"url": pdf_url, "arxiv_id": output_filename.replace('.pdf', '')})
        return False, error_msg

def clean_text(text: str):
    
    if not text:
        return ""

    # Remove control characters (except newline and tab) 
    cleaned_chars = []
    for ch in text:
        code = ord(ch)
        if ch in ("\n", "\t") or code >= 32:
            cleaned_chars.append(ch)
    text = "".join(cleaned_chars)

    # Normalize common Unicode punctuation 
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

    # Fix hyphens at line breaks
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
    
def extract_text_pypdf(pdf_filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text from PDF using pypdf.

    Args:
        pdf_filepath: Path to PDF file

    Returns:
        Tuple of (text: str | None, error_message: str | None)
    """
    try:
        reader = PdfReader(pdf_filepath)
        clean_pages = []
        for page in reader.pages:
            lines = (page.extract_text() or "").splitlines()
            cleaned = [line for line in lines if len(line) >= 3]
            clean_pages.append("\n".join(cleaned))
        text = "\n".join(clean_pages)
        logger.debug(f"Extracted text using pypdf: {len(text)} characters", extra={"file": os.path.basename(pdf_filepath)})
        return text, None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"pypdf extraction failed: {error_msg}", extra={"file": pdf_filepath})
        return None, error_msg
        
def extract_text_docling(pdf_filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text from PDF using docling.

    Args:
        pdf_filepath: Path to PDF file

    Returns:
        Tuple of (text: str | None, error_message: str | None)
    """
    try:
        doc = DocumentConverter().convert(pdf_filepath).document
        text = doc.export_to_markdown()
        logger.debug(f"Extracted text using docling: {len(text)} characters", extra={"file": os.path.basename(pdf_filepath)})
        return text, None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"docling extraction failed: {error_msg}", extra={"file": pdf_filepath})
        return None, error_msg

def extract_text(metadata_dict: Dict[str, Any], pdf_save_dir: str, method: str = 'pypdf',
                 metrics: Optional[PipelineMetrics] = None) -> None:
    """
    Populates the passed metadata_dict with full paper texts.

    Args:
        metadata_dict: Dictionary of paper metadata
        pdf_save_dir: Directory containing downloaded PDFs
        method: Extraction method ('pypdf' or 'docling')
        metrics: Optional PipelineMetrics object for tracking
    """
    # extract text from each downloaded PDF
    for paper_id, info in metadata_dict.items():
        pdf_url = info.get("pdf_url")
        if not pdf_url:
            continue

        arxiv_id = pdf_url.split('/')[-1]
        pdf_filename = f"{arxiv_id}.pdf"
        pdf_filepath = os.path.join(pdf_save_dir, pdf_filename)

        if not os.path.exists(pdf_filepath):
            logger.warning(f"PDF not found for text extraction", extra={"arxiv_id": arxiv_id, "file": pdf_filepath})
            continue

        if metrics:
            metrics.increment("scraping.text_extraction_attempted")

        # Extract text based on method
        text, error = None, None
        if method == 'pypdf':
            text, error = extract_text_pypdf(pdf_filepath=pdf_filepath)
            if text:
                text = clean_text(text)
        elif method == 'docling':
            text, error = extract_text_docling(pdf_filepath=pdf_filepath)
        else:
            raise ValueError(f"Unknown text extraction method '{method}'. Valid options: 'pypdf', 'docling'")

        # Track results
        if text:
            metadata_dict[paper_id]['full_text'] = text
            if metrics:
                metrics.increment("scraping.text_extraction_succeeded")
        else:
            metadata_dict[paper_id]['full_text'] = None
            if metrics:
                metrics.increment("scraping.text_extraction_failed")
                metrics.record_error(
                    ErrorCategory.SCRAPING_ERROR,
                    f"Text extraction failed: {error or 'Unknown error'}",
                    {"arxiv_id": arxiv_id, "paper_id": paper_id, "method": method, "file": pdf_filepath}
                )
    
def scrape_papers(query: str, date: str, max_results: int = 2, method: str = 'pypdf',
                  metrics: Optional[PipelineMetrics] = None, verbose: bool = False) -> Tuple[int, int]:
    """
    Scrape papers from arXiv, download PDFs, and extract text.

    Args:
        query: arXiv query string (e.g., "cs.AI")
        date: Date string in YYYY-MM-DD format
        max_results: Maximum number of papers to fetch
        method: Text extraction method ('pypdf' or 'docling')
        metrics: Optional PipelineMetrics object for tracking
        verbose: Enable verbose logging

    Returns:
        Tuple of (num_metadata_fetched, num_pdfs_downloaded)
    """
    # date needed for naming conventions & storage
    try:
        year, month, day = date.split("-")
        date_clean = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        raise ValueError("Date must be in the form YYYY-MM-DD")

    pdf_save_dir = f"./data/pdfs/papers_{date_clean}"
    logger.info(f"Starting paper scraping", extra={"query": query, "max_results": max_results, "date": date_clean, "save_dir": pdf_save_dir})
    os.makedirs(pdf_save_dir, exist_ok=True)

    # Track papers requested
    if metrics:
        metrics.increment("scraping.papers_requested", max_results)

    # get metadata from arXiv
    logger.info(f"Fetching metadata from arXiv", extra={"query": query, "max_results": max_results})
    metadata_dict, api_errors = get_arxiv_metadata(query=query, max_results=max_results)
    num_papers_metadata = len(metadata_dict.keys())

    # Record any API errors
    if api_errors and metrics:
        for error in api_errors:
            metrics.record_error(
                ErrorCategory.SCRAPING_ERROR,
                f"arXiv API error: {error.get('message', 'Unknown error')}",
                error
            )

    if metrics:
        metrics.increment("scraping.metadata_fetched", num_papers_metadata)

    logger.info(f"Fetched {num_papers_metadata} papers from arXiv")

    # download PDFs
    num_pdfs_downloaded = 0
    for paper_id, info in metadata_dict.items():
        pdf_url = info.get("pdf_url")

        if not pdf_url:
            logger.warning(f"No PDF URL for paper", extra={"paper_id": paper_id})
            continue

        arxiv_id = pdf_url.split('/')[-1]
        pdf_filename = f"{arxiv_id}.pdf"
        pdf_filepath = os.path.join(pdf_save_dir, pdf_filename)

        # Check if PDF already exists
        if os.path.exists(pdf_filepath):
            logger.debug(f"PDF already exists, skipping download", extra={"arxiv_id": arxiv_id})
            num_pdfs_downloaded += 1
            continue

        if metrics:
            metrics.increment("scraping.pdfs_attempted")

        # Rate limiting: arXiv recommends 3-second delay between requests
        time.sleep(3)

        # Download PDF
        success, error_msg = download_pdf(pdf_url, pdf_save_dir)

        if success:
            num_pdfs_downloaded += 1
            if metrics:
                metrics.increment("scraping.pdfs_downloaded")
        else:
            if metrics:
                metrics.increment("scraping.pdfs_failed")
                metrics.record_error(
                    ErrorCategory.SCRAPING_ERROR,
                    f"PDF download failed: {error_msg}",
                    {"arxiv_id": arxiv_id, "paper_id": paper_id, "url": pdf_url}
                )

    logger.info(f"Downloaded {num_pdfs_downloaded}/{num_papers_metadata} PDFs")

    # extract text from each downloaded PDF
    logger.info(f"Extracting text using {method} method")
    extract_text(metadata_dict=metadata_dict, pdf_save_dir=pdf_save_dir, method=method, metrics=metrics)

    # Count successful extractions
    num_with_text = sum(1 for info in metadata_dict.values() if info.get('full_text'))
    logger.info(f"Extracted text from {num_with_text}/{num_pdfs_downloaded} PDFs")

    # save results from Python dict to JSON
    os.makedirs("./data/metadata", exist_ok=True)
    metadata_file = f"./data/metadata/metadata_{date_clean}.json"

    with open(metadata_file, "w") as f:
        json.dump(metadata_dict, f, indent=2)

    logger.info(f"Saved metadata to {metadata_file}")

    return num_papers_metadata, num_pdfs_downloaded
    
    
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