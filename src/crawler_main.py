import json
import time, random
import os

from playwright.sync_api import sync_playwright
from stealth import stealth_context
from db import db_initialization, get_and_update_pending_url, mark_url_as_failed, update_url_status
from utils import setup_loggers, setup_directories, countdown_sleep_timer, load_page, perform_scroll, extract_html, persist_result_in_db
from specific_sites import site_registry, specific_site_setup

#Config setup and directories
BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR = setup_directories()

#Load config
config_path = os.path.join(BASE_DIR, "config.json")
with open(config_path) as f:
    config = json.load(f)
    config_db_path = config.get("database_path", "mini.sqlite") 
    site_name = config["site"]

#Specific site config
SITE_REGISTRY = site_registry()
specific_site_config, _ = specific_site_setup(SITE_REGISTRY, site_name)

#DB setup
db_path = os.path.join(DATA_DIR, config_db_path)
db = db_initialization(db_path)

#Logging setup
logger, error_logger = setup_loggers()
page_counter = 1

#Playwright fetching    
with sync_playwright() as p:

    browser = p.chromium.launch(
    headless=False
    )
    try:
        context = stealth_context(browser)
        page = context.new_page()

        #Main crawling loop
        while True:

            try:
                #Query the db, get one url, starting from the top, and mark them as in_progress
                url_id, url = get_and_update_pending_url(db)
                if url is None:
                    print("URL not found. Exiting program")
                    break
            
                #Occasional long pause to simulate browsing
                if (page_counter % 5 == 0) and (page_counter != 0):
                    special_wait_time = random.uniform(50, 90)
                    countdown_sleep_timer(special_wait_time)

                #Navigation phase
                if not load_page(page, url, specific_site_config, max_attempts=2):
                    mark_url_as_failed(db, url)
                    continue
                print(f"{page_counter}. Target JavaScript selector detected in URL: {url}")

                #Scrolling phase
                if not perform_scroll(page, url):
                    mark_url_as_failed(db, url)
                    continue
 
                #Extra delay to let JS finish loading
                time.sleep(random.uniform(3, 5))

                #HTML extraction phase
                html = extract_html(page, url)
                if html is None:
                    mark_url_as_failed(db, url)
                    continue

                #DB persistence phase
                try:
                    persist_result_in_db(db, url, url_id, html, DATA_DIR)
                except Exception:
                    mark_url_as_failed(db, url)
                    continue

                page_counter += 1

                #Normal safe delay
                wait_time = random.uniform(30, 55)
                countdown_sleep_timer(wait_time)

            except KeyboardInterrupt:
                if url is not None: # type: ignore
                    update_url_status(url, db, status = 'pending') # type: ignore
                raise
    finally: 
    #Close DB cur, connection and browser
        db["cur"].close()
        db["conn"].close()
        browser.close()


