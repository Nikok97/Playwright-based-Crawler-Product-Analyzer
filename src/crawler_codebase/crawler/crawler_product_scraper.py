import random
import logging
import sqlite3

from typing import Optional
from playwright.sync_api import sync_playwright
from utilities.stealth import stealth_context
from utilities.utils import countdown_sleep_timer, process_single_url, write_html

def update_fetch_status_in_product_pages(row_id: int, db: dict, filename: str | None, status: str):

    db["cur"].execute(
        "UPDATE ProductPages SET fetch_status = ?, filename = ? WHERE id = ?",
        (status, 
        filename, 
        row_id)
    )
    db["conn"].commit()

def reset_stuck_jobs(db: dict):
    # Resets stuck jobs: sets the fetch_status of product webpages from ProductPages where fetch_status is 'pending' to 'fetching'
    db["cur"].execute(
        '''
        UPDATE ProductPages
        SET fetch_status = 'pending'
        WHERE fetch_status = 'fetching'
        '''
    )
    db["conn"].commit()

def get_pending_product_url(db: dict) -> tuple[int, str] | tuple[None, None]:
    # Gets 1 product webpage (d, product_url) from ProductPages table that has not yet been scraped.
    db["cur"].execute(
        '''
        SELECT id, product_url
        FROM ProductPages
        WHERE fetch_status = ?
        ORDER BY id
        LIMIT 1
        ''',
        ('pending',)
    )
    row = db["cur"].fetchone()
    
    if row is None:
        return None, None
    
    row_id, product_url = row

    # Lock
    # Updates status to fetching
    db["cur"].execute(
        'UPDATE ProductPages SET fetch_status = ? WHERE id = ?',
        ('fetching', row_id)
    )

    db["conn"].commit()
    
    return row_id, product_url

def scrape_product_urls(db, paths_dict, page, specific_site_config , logger, error_logger, page_counter=1, fetch_html=process_single_url) -> None:
    
    # Main crawling loop
    while True:

        row_id: Optional[int] = None 
        filename: Optional[str] = None 

        try:
            # Get each product URL, name and row_id
            row_id, product_url = get_pending_product_url(db)

            if row_id is None:
                logger.info("No more URLs found. Exiting program")
                break
            
            if product_url is None:
                update_fetch_status_in_product_pages(row_id, db, filename, status='failed_unfetchable')
                logger.info(f"URL not found for {row_id}. Continuing program")
                continue
            
            # Occasional long pause to simulate browsing
            if (page_counter % 5 == 0) and (page_counter != 0):
                special_wait_time = random.uniform(5, 7)
                countdown_sleep_timer(special_wait_time)

            # Process a single URL
            html = fetch_html(
                page, 
                product_url, 
                logger, 
                wait_selector=specific_site_config.wait_selector
            )
            
            if not html:

                error_logger.error(f"HTML not fetched for URL: {product_url}")

                update_fetch_status_in_product_pages(row_id, db, filename, status='failed')

                continue
            
            # Write HTML to disk
            filename = f'product_{page_counter}.html'
            
            if write_html(paths_dict['output_dir'], filename, html):

                update_fetch_status_in_product_pages(row_id, db, filename, status='fetched')

                page_counter += 1

            else:

                update_fetch_status_in_product_pages(row_id, db, filename, status='failed')

            # Normal safe delay
            wait_time = random.uniform(1, 5)

            countdown_sleep_timer(wait_time)

        except KeyboardInterrupt:

            if row_id is not None:

                update_fetch_status_in_product_pages(row_id, db, filename, status='pending')

            raise KeyboardInterrupt()

        except Exception:

            if row_id is not None:
                
                update_fetch_status_in_product_pages(row_id, db, filename, status='failed')

            error_logger.error("Unhandled error in product scraper", exc_info=True)

def scrape_product_urls_with_playwright(db, paths_dict, specific_site_config , logger, error_logger):
    
    # Main loop
    with sync_playwright() as p:

        browser = p.chromium.launch(
        headless=False
        )
        context = stealth_context(browser)
        page = context.new_page()

        scrape_product_urls(db, paths_dict, page, specific_site_config , logger, error_logger, page_counter=1, fetch_html =process_single_url)

##########################################################

def run_crawler_product_scraper(
    db: dict,
    specific_site_config,
    paths_dict: dict,
    logger: logging.Logger,
    error_logger: logging.Logger,
    ):
    
    #Reset stuck parsing jobs
    reset_stuck_jobs(db)

    #Main loop
    scrape_product_urls_with_playwright(db, paths_dict, specific_site_config , logger, error_logger)





