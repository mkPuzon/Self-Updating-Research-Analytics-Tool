'''processor/main.py

Timing statistics (scraping and processing):
- time | # papers  |   keyword model    | definition model
- 2m7s | 10 papers | gemma3:12b (local) | gpt-4.1-nano 

Jan 2026
'''
import os
import sys
import shutil
import time
import logging
import schedule
from datetime import datetime, timedelta

from src.scrape_papers import scrape_papers
from src.process_text import generate_keywords_and_defs
from src.db_functions import dump_metadata_to_db, setup_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def job():
    '''Main workflow for data scraping, processing, and uploading.'''
    try:

        today = datetime.today().strftime('%Y-%m-%d')

        # scrape papers & extract text           
        num_metadata, num_pdfs = scrape_papers(query="cs.AI", date=today, max_results=10, method='pypdf', verbose=True)
        print(f"[{today}] {(num_pdfs/num_metadata)*100:.2f}% of initial papers usable | {num_pdfs} full papers scraped | Metadata entries={num_metadata}, PDFs scraped={num_pdfs}")

        # pull keywords & definitions
        file_path = f"./data/metadata/metadata_{today}.json"
        num_papers, num_kwds, num_dicts = generate_keywords_and_defs(file_path, kwd_model="gemma3:12b", def_model="OPENAI", openai=True, verbose=True)
        print(f"[{today}] {(num_kwds/(num_papers*3))*100:.2f}% keyword extraction rate | Out of {num_papers} total papers: num papers w/ definitions={num_dicts}, num keywords extracted={num_kwds}")

        # add data to db
        DATA_DIR = f'data/metadata/metadata_{today}.json'
        DB_NAME = 'data/tests.db'
        setup_db(DATA_DIR)
        dump_metadata_to_db(DATA_DIR, DB_NAME, verbose=True)

    except Exception as e:
        logger.error(f"job() failed: {e}")

def clean_papers():
    ''' Deletes locally stored papers after 7 days; only stored for immediate quality checks and troubleshooting.'''
    try:
        expired = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
        if os.path.exists(f"./data/pdfs/papers_{expired}"):
            shutil.rmtree(f"./data/pdfs/papers_{expired}")
            
    except Exception as e:
        logger.error(f"clean_papers() failed: {e}")
    
# TEST: run immediaty on startup to verify its working
job()
clean_papers()

# schedule job pipeline each day at 2am
# schedule.every().day.at("02:00").do(job)
# schedule.every().day.at("01:45").do(clean_papers)

# logger.info("Scheduler started. Waiting for 2:00 AM...")

# while True:
#     # check if a scheduled task is pending
#     schedule.run_pending()
#     # sleep to save CPU cycles
#     time.sleep(60)