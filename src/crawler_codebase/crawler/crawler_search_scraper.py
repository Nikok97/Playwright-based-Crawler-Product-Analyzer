import random

from playwright.sync_api import sync_playwright
from utilities.stealth import stealth_context
from utilities.utils import countdown_sleep_timer, process_single_url, write_html

def get_pending_url_and_update (db, status="in_progress"):
    """
    Retrieves URLs and their IDs marked as pending, and stamps them as in progress.
    """
    db["cur"].execute('SELECT id, url_name FROM Urls WHERE status=? ORDER BY id LIMIT 1', ("pending",))
    row = db["cur"].fetchone()
    if row is None:
        return None, None
    url_id = row[0]
    url = row[1]
    db["cur"].execute('UPDATE Urls SET status=? WHERE id=?', (status, url_id))
    db["conn"].commit()
    return url_id, url

def update_filename_for_url(url, db, filename):
    """Insert filename for crawled URL."""
    db["cur"].execute('SELECT filename FROM Urls WHERE url_name=?', (url,))
    row = db["cur"].fetchone()
    if row[0] is None:
        db["cur"].execute('UPDATE Urls SET filename = ? WHERE url_name = ?', (filename, url))
    db["conn"].commit()

def update_url_status(url, db: dict, status: str):
    """Sets the crawling status of an URL: pending / fetched / failed."""
    db["cur"].execute(
        'UPDATE Urls SET status = ? WHERE url_name = ?',
        (status, url)
    )
    db["conn"].commit()

#########################################################

def run_crawler_search_scraper(
    db, 
    specific_site_config,
    logger,
    error_logger,
    paths_dict,
    page_counter = 1):

    #Reset jobs
    def reset_stuck_fetch_jobs(db):
        db["cur"].execute(
            '''
            UPDATE Urls
            SET status = 'pending'
            WHERE status = 'in_progress'
            '''
        )
        db["conn"].commit()
        
    reset_stuck_fetch_jobs(db)

    #Main logic
    with sync_playwright() as p:

        browser = p.chromium.launch(
        headless=False
        )
        context = stealth_context(browser)
        page = context.new_page()

        #Main crawling loop
        while True:

            try:
                #Query the db, get one url, starting from the top, and mark them as in_progress
                url_id, url = get_pending_url_and_update(db, status='in_progress')
                logger.info(f'Retrieved {url} from DB')
                if url is None:
                    logger.info("Crawler_search_scraper program. URL not found. Exiting program")
                    break
            
                #Occasional long pause to simulate browsing
                if (page_counter % 5 == 0) and (page_counter != 0):
                    special_wait_time = random.uniform(50, 90)
                    countdown_sleep_timer(special_wait_time)

                #Process a single URL
                html = process_single_url(
                    page, 
                    url, 
                    logger,
                    wait_selector="li.ui-search-layout__item"
                )
                
                #CHECK INFINITE LOOP POSSIBILITIES HERE
                if not html:
                    error_logger.error(f"No HTML found for {url}")
                    update_url_status(url, db, status='failed')
                    continue
                
                #Write HTML to disk
                filename = f"page_{url_id}.html"
                write_html(paths_dict['data_dir'], filename, html)
                update_filename_for_url(url, db, filename)
                update_url_status(url, db, status='fetched')

                #Increase page counter
                page_counter += 1

                #Normal safe delay
                wait_time = random.uniform(30, 55)
                countdown_sleep_timer(wait_time)

            except KeyboardInterrupt:
                logger.info("Program interrupted with KeyboardInterrupt")
                raise


