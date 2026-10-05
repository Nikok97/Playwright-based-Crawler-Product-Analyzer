import random
import logging

from typing import Optional
from playwright.sync_api import sync_playwright
from utilities.stealth import stealth_context
from utilities.utils import countdown_sleep_timer, process_single_url, write_html
from utilities.database import Database

def occasional_long_pause_to_simulate_browsing(page_counter):
    if (page_counter % 5 == 0) and (page_counter != 0):
        special_wait_time = random.uniform(5, 7)
        countdown_sleep_timer(special_wait_time)

def scrape_product_urls(
        db : Database, 
        paths_dict, 
        page, 
        specific_site_config , 
        logger, 
        error_logger, 
        page_counter=1, 
        fetch_html=process_single_url) -> None:
    
    # Main crawling loop
    while True:

        row_id: Optional[int] = None 
        filename: Optional[str] = None 

        try:

            # Get each product URL, name and row_id
            row_id, product_url = db.get_pending_product_url()

            if row_id is None:

                logger.info("No more URLs found. Exiting program")
                break
            
            if product_url is None:

                db.update_fetch_status_in_product_pages(row_id, filename, status='failed_unfetchable')
                logger.info(f"URL not found for {row_id}. Continuing program")
                continue
            
            # Occasional long pause to simulate browsing
            occasional_long_pause_to_simulate_browsing(page_counter)

            # Process a single URL
            html = fetch_html(
                page, 
                product_url, 
                logger, 
                wait_selector=specific_site_config.wait_selector
            )

            # If the page did not return a HTML:            
            if not html:

                error_logger.error(f"HTML not fetched for URL: {product_url}")

                db.update_fetch_status_in_product_pages(row_id, filename, status='failed')

                continue
            
            # Write HTML to disk
            filename = f'product_{page_counter}.html'
            
            if write_html(paths_dict['output_dir'], filename, html):

                db.update_fetch_status_in_product_pages(row_id, filename, status='fetched')

                page_counter += 1

            else:

                db.update_fetch_status_in_product_pages(row_id, filename, status='failed')

            # Normal safe delay
            wait_time = random.uniform(1, 5)

            countdown_sleep_timer(wait_time)

        except KeyboardInterrupt:

            if row_id is not None:

                db.update_fetch_status_in_product_pages(row_id, filename, status='pending')

            raise KeyboardInterrupt()

        except Exception:

            if row_id is not None:
                
                db.update_fetch_status_in_product_pages(row_id, filename, status='failed')

            error_logger.error("Unhandled error in product scraper", exc_info=True)

def scrape_product_urls_with_playwright(
        db : Database, 
        paths_dict : dict, 
        specific_site_config, 
        logger, 
        error_logger):
    
    # Main loop
    with sync_playwright() as p:

        browser = p.chromium.launch(
        headless=False
        )
        context = stealth_context(browser)
        page = context.new_page()

        scrape_product_urls(db, paths_dict, page, specific_site_config , logger, error_logger, page_counter=1, fetch_html=process_single_url)

##########################################################

def run_crawler_product_scraper(
    db: Database,
    specific_site_config,
    paths_dict: dict,
    logger: logging.Logger,
    error_logger: logging.Logger,
    ):
    
    #Reset stuck parsing jobs
    db.reset_stuck_jobs()

    #Main loop
    scrape_product_urls_with_playwright(db, paths_dict, specific_site_config , logger, error_logger)





