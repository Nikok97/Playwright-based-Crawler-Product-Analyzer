import random

from playwright.sync_api import sync_playwright, Page
from pathlib import Path
from logging import Logger

from utilities.stealth import stealth_context
from utilities.utils import countdown_sleep_timer, process_single_url, write_html
from utilities.specific_sites import WebsiteToScrape
from utilities.database import Database


def write_html_to_disk(url_id: int | None, paths_dict: dict[str, Path], url: str, html: str, db: Database) -> None:

    #Write HTML to disk
    filename = f"page_{url_id}.html"
    write_html(paths_dict['data_dir'], filename, html)
    db.update_filename_for_url(url, filename)
    db.update_url_status(url, status='fetched')

def simulate_natural_browsing_with_occasional_pause(page_counter: int):

    if (page_counter % 5 == 0) and (page_counter != 0):

        special_wait_time = random.uniform(5, 7)
        countdown_sleep_timer(special_wait_time)

#############################################################################

def scrape_urls_with_playwright(db: Database, logger: Logger, error_logger: Logger, specific_site_config, paths_dict: dict[str, Path]):

    #Main logic
    
    with sync_playwright() as p:

        browser = p.chromium.launch(
        headless=False
        )
        context = stealth_context(browser)
        page = context.new_page()

        scrape_urls(db, paths_dict, page, specific_site_config, logger, error_logger)

def scrape_urls(
    db: Database, 
    paths_dict: dict, 
    page : Page, 
    specific_site_config : WebsiteToScrape, 
    logger: Logger, 
    error_logger: Logger, 
    page_counter=1, 
    fetch_html=process_single_url
) -> None:

    #Main crawling loop

    while True:

        try:
            
            #Query the db, get one url, starting from the top, and mark them as in_progress

            url_id, url = db.get_pending_url_and_update(status='in_progress')
            
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

                db.update_url_status(url, status='failed')

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
    db : Database,
    specific_site_config : WebsiteToScrape,
    paths_dict : dict,
    logger : Logger, 
    error_logger : Logger
    ):

    # If there are any 'pending' Urls, set them as 'in_progress'
    db.reset_stuck_jobs_in_urls_table()

    # Open playwright session and scrape urls in it
    scrape_urls_with_playwright(
        db, 
        logger, 
        error_logger, 
        specific_site_config, 
        paths_dict
    )


