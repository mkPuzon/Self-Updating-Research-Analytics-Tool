'''processor/main.py

Jan 2026
'''
import os
import time
import logging
import schedule
from src import db_functions, full_scraper, process_text, scrapers, utils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def job():
    '''Main workflow for data scraping, processing, and uploading.'''
    try:
        print("[S] Job working in main.py")
    except Exception as e:
        logger.error(f"Job failed: {e}")

# schedule job pipeline each day at 2am
schedule.every().day.at("02:00").do(job)
# TEST: run immediaty on startup to verify its working
job()

logger.info("Scheduler started. Waiting for 2:00 AM...")

while True:
    # check if a scheduled task is pending
    schedule.run_pending()
    # sleep to save CPU cycles
    time.sleep(120)