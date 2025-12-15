import json
import time, random
import os

from playwright.sync_api import sync_playwright
from stealth import stealth_context, human_scroll
from db import db_initialization, insert_url, now, update_url_date, update_filename_for_url
from utils import setup_loggers, setup_directories
from specific_sites import MercadoLibreConfig, AmazonConfig

#Config setup and directories
BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR = setup_directories()

#Load config
config_path = os.path.join(BASE_DIR, "config.json")

with open(config_path) as f:
    config = json.load(f)
    config_db_path = config.get("database_path", "mini.sqlite") 
    start_position = config["start_position"]
    end_position = config["end_position"]

#Specific site config
specific_site_config = MercadoLibreConfig()
seed_url = specific_site_config.seed_urls[0]

#DB setup
db_path = os.path.join(DATA_DIR, config_db_path)
db = db_initialization(db_path)

#Logging setup
logger, error_logger = setup_loggers()

#Pagination
list_of_urls = list()
for i in range(start_position, end_position):
    url = specific_site_config.build_pagination_url(seed_url, i)
    list_of_urls.append(url)

page_counter = 1

#Playwright fetching    
with sync_playwright() as p:

    browser = p.chromium.launch(
    headless=False
    )
    context = stealth_context(browser)
    page = context.new_page()

    for i in range(len(list_of_urls)):

        #Occasional long pause to simulate natural browsing
        if (i % 5 == 0) and (i != 0):
            time.sleep(random.uniform(50, 90))  

        try:
            page.goto(list_of_urls[i], timeout=30000)
            page.wait_for_selector(specific_site_config.selector_to_start_process, timeout=8000)
            print(f'Target JavaScript selector detected in URL: {list_of_urls[i]}')
        except Exception as e:
            logger.info(f"Retrying {list_of_urls[i]}: {e}")
            time.sleep(random.uniform(15, 25))

        #2nd try
        try:
            time.sleep(random.uniform(11, 14))
            page.reload(timeout=30000)
            page.wait_for_selector(specific_site_config.selector_to_start_process, timeout=8000)
        except Exception as e:
            error_logger.warning(f"Second failure on {list_of_urls[i]}: {e}")
            continue

        #Scroll
        print("Scrolling")
        human_scroll(page)
        
        time.sleep(random.uniform(1.0, 2.2))

        try:
            #Delay to let JS finish loading
            time.sleep(random.uniform(3, 5))

            #Fetch HTML
            print("Fetching for: ", list_of_urls[i])
            html = page.content()
            logger.info(f"Fetched HTML content for {list_of_urls[i]}")

            filename = f"page{page_counter}.html"
            output_path = os.path.join(DATA_DIR, filename)

            #HTML writing
            with open(output_path, "w", encoding="utf-8") as f:

                f.write(html)

            #Insert link to DB
            if html:
                try:

                    date = str(now())
                    print(f"1. Attempting to insert URL: {list_of_urls[i]}")
                    insert_url(list_of_urls[i], db)
                    print(f"2. Inserted URL: {list_of_urls[i]}")
                    print(f"3. Attempting to update date of URL: {list_of_urls[i]}")
                    update_url_date(list_of_urls[i], db, date)
                    print(f"4. Date updated for URL: {list_of_urls[i]}")
                    print(f"5. Attempting to update filename of URL: {list_of_urls[i]}")
                    update_filename_for_url(list_of_urls[i], db, filename)
                    print(f"6. Filename updated for URL: {list_of_urls[i]}")

                except Exception as e:
                    error_logger.warning(f"Unknown DB error for {list_of_urls[i]}: {e}")
            
            page_counter += 1

            print("Now waiting...")
            time.sleep(random.uniform(30, 55))

        except Exception as e:
            error_logger.warning(f"Unknown error for {list_of_urls[i]}: {e}")
            
    #Close the browser 
    browser.close()


