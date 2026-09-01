import random

from playwright.sync_api import sync_playwright, Page
from pathlib import Path
from logging import Logger

from utilities.stealth import stealth_context
from utilities.utils import countdown_sleep_timer, process_single_url, write_html
from utilities.specific_sites import WebsiteToScrape


def get_pending_url_and_update (db: dict, status="in_progress") -> tuple[int, str] | tuple[None, None]:
    """
    Retrieves URLs that are marked as pending, along with their IDs, and stamps them as in_progress.
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

def update_filename_for_url(url: str, db: dict, filename: str):
    """Insert filename for crawled URL."""
    db["cur"].execute('SELECT filename FROM Urls WHERE url_name=?', (url,))
    row = db["cur"].fetchone()
    if row[0] is None:
        db["cur"].execute('UPDATE Urls SET filename = ? WHERE url_name = ?', (filename, url))
    db["conn"].commit()

def update_url_status(url: str, db: dict, status: str):
    """Sets the crawling status of an URL: pending / fetched / failed."""
    db["cur"].execute(
        'UPDATE Urls SET status = ? WHERE url_name = ?',
        (status, url)
    )
    db["conn"].commit()

def reset_stuck_fetch_jobs(db):
    db["cur"].execute(
        '''
        UPDATE Urls
        SET status = 'pending'
        WHERE status = 'in_progress'
        '''
    )
    db["conn"].commit()

def write_html_to_disk(url_id: int | None, paths_dict: dict[str, Path], url: str, html: str, db: dict) -> None:

    #Write HTML to disk

    filename = f"page_{url_id}.html"
    write_html(paths_dict['data_dir'], filename, html)
    update_filename_for_url(url, db, filename)
    update_url_status(url, db, status='fetched')

def simulate_natural_browsing_with_occasional_pause(page_counter: int):

    if (page_counter % 5 == 0) and (page_counter != 0):

        special_wait_time = random.uniform(5, 7)
        countdown_sleep_timer(special_wait_time)

def scrape_urls_with_playwright(db: dict, logger: Logger, error_logger: Logger, specific_site_config, paths_dict: dict[str, Path]):

    #Main logic
    
    with sync_playwright() as p:

        browser = p.chromium.launch(
        headless=False
        )
        context = stealth_context(browser)
        page = context.new_page()

        scrape_urls(db, paths_dict, page, specific_site_config, logger, error_logger)


def scrape_urls(db: dict, paths_dict: dict, page : Page, specific_site_config : WebsiteToScrape, logger: Logger, error_logger: Logger, page_counter=1, fetch_html =process_single_url) -> None:

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
            simulate_natural_browsing_with_occasional_pause(page_counter)

            #Process a single URL
            html = fetch_html(
                page, 
                url, 
                logger,
                specific_site_config.selector_to_start_process
            )
            
            if not html:

                error_logger.error(f"No HTML found for {url}")

                update_url_status(url, db, status='failed')

                continue

            else:

                # If HTML, Write HTML to disk
                write_html_to_disk(url_id, paths_dict, url, html, db)

                #Increase page counter
                page_counter += 1

                #Normal safe delay
                wait_time = random.uniform(1, 5)

                countdown_sleep_timer(wait_time)

        except KeyboardInterrupt:
            logger.info("Program interrupted with KeyboardInterrupt")
            raise

#########################################################

def run_crawler_search_scraper(
    db,
    specific_site_config,
    paths_dict,
    logger, 
    error_logger
    ):

    # If there are any 'pending' Urls, set them as 'in_progress'
    reset_stuck_fetch_jobs(db)

    # Open playwright session and scrape urls in it
    scrape_urls_with_playwright(db, logger, error_logger, specific_site_config, paths_dict)


