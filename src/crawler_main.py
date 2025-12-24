import json
import time, random
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from stealth import stealth_context, human_scroll
from db import db_initialization, now, update_url_date, update_filename_for_url, update_url_status, get_and_update_pending_url
from utils import setup_loggers, setup_directories, countdown_sleep_timer
from specific_sites import site_registry

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
if site_name not in SITE_REGISTRY:
    raise ValueError(f"Unsupported site: {site_name}")
specific_site_config = SITE_REGISTRY[site_name]()
seed_url = specific_site_config.seed_urls[0]

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

                loaded = False
                tmp_path = None
            
                #Occasional long pause to simulate natural browsing
                if (page_counter % 5 == 0) and (page_counter != 0):
                    special_wait_time = random.uniform(50, 90)
                    countdown_sleep_timer(special_wait_time)

                #Navigation block
                #1st try
                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_selector(specific_site_config.selector_to_start_process, timeout=8000)
                    print(f"{page_counter}. Target JavaScript selector detected in URL: {url}")

                    loaded = True
                    logger.info(f"URL: {url} succesfully loaded")

                except PlaywrightTimeoutError as e:
                    logger.warning(f"Timeout while loading {url}")
                    time.sleep(random.uniform(15, 25))
                except Exception:
                    error_logger.error(
                        f"Unexpected navigation error on {url}",
                        exc_info=True
                    )
                    time.sleep(random.uniform(15, 25))

                #Second try
                if not loaded:
                    try:
                        time.sleep(random.uniform(11, 14))
                        page.reload(timeout=30000)
                        page.wait_for_selector(specific_site_config.selector_to_start_process, timeout=8000)

                        loaded = True
                        logger.info(f"URL: {url} succesfully loaded")
                    
                    except PlaywrightTimeoutError:
                        error_logger.warning(f"Reload timeout on {url}")
                        update_url_status(url, db, status="failed")
                        continue
                    except Exception as e:
                        error_logger.error(f"Second failure on {url}: {e}", exc_info=True)
                        update_url_status(url, db, status='failed')
                        continue
                
                #If page loaded, proceed and scroll
                try:
                    print(f"{page_counter}. Scrolling for {url}")
                    human_scroll(page, min_increment=200, max_increment=450,  timeout=15.0)
                except PlaywrightTimeoutError:
                    error_logger.warning(f"Scroll timeout on {url}")
                    update_url_status(url, db, status="failed")
                    continue
                except Exception:
                    error_logger.error(
                        f"Unexpected scroll error on {url}",
                        exc_info=True
                    )
                    update_url_status(url, db, status="failed")
                    continue
                           
                #Extra delay to let JS finish loading
                time.sleep(random.uniform(3, 5))
            
                #Fetch HTML
                logger.info(f"Fetching HTML for: {url}")
                try:
                    html = page.content()
                    logger.info(f"Fetched HTML content for {url}")
                except Exception:
                    error_logger.error(
                        f"HTML fetching error for {url}",
                        exc_info=True)
                    update_url_status(url, db, status="failed")
                    continue

                #File path setup
                filename = f"page{url_id}.html"
                output_path = os.path.join(DATA_DIR, filename)
                tmp_path = output_path + ".tmp"

                #HTML writing
                with open(tmp_path, "w", encoding="utf-8") as f:

                    f.write(html)

                #Insert link to DB
                try:
                    date = str(now())
                    update_url_date(url, db, date)
                    update_filename_for_url(url, db, filename)
                    update_url_status(url, db, status="fetched")
                    page_counter += 1
                    os.replace(tmp_path, output_path)

                except Exception as e:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    update_url_status(url, db, status="failed")
                    error_logger.error(f"DB or filesystem error while processing {url}", exc_info=True)

                wait_time = random.uniform(30, 55)
                countdown_sleep_timer(wait_time)

            except KeyboardInterrupt:
                if url is not None: # type: ignore
                    update_url_status(url, db, status="failed") # type: ignore
                raise
    finally: 
    #Close DB connection and browser
        db["conn"].close()
        browser.close()


