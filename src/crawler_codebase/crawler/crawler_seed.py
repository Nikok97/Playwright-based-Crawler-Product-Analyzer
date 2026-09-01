import logging

from utilities.database import insert_url, already_pending_or_fetched_url, update_url_status
from utilities.utils import now_with_hours

def resolve_pagination(
    specific_site_config, 
    seed_url: str, 
    site_name: str, 
    error_logger: logging.Logger) -> str | None:
    
    canonical_url = None

    # Pagination
    pagination_mode = specific_site_config.pagination_mode

    # If pagination is read from config as dynamic:
    if pagination_mode == "dynamic":
        try:
            canonical_url = specific_site_config.discover_first_paginated_url(seed_url)
        except Exception as e:
            error_logger.error(
                f"[{site_name}] Dynamic pagination discovery failed for seed URL: {seed_url}",
                exc_info=True
            )
            raise RuntimeError(
                f"[{site_name}] Cannot determine canonical pagination base. Aborting."
            ) from e
        
    # If it is read as static:
    elif pagination_mode == "algorithmic":
        canonical_url = seed_url

    return canonical_url

def alrogithmic_paginator(
    specific_site_config, 
    pages_to_crawl: int, 
    canonical_url: str | None) -> list[str]:

    # Algorithmic pagination as the end stage of both modes
    list_of_urls: list[str] = list()

    for i in range(1, pages_to_crawl + 1):
        url = specific_site_config.build_pagination_url(canonical_url, i)
        list_of_urls.append(url)

    return list_of_urls

def db_insert_paginated_urls(
    db: dict, 
    list_of_urls: list[str], 
    logger: logging.Logger, 
    error_logger: logging.Logger):

    # URL DB inserting
    page_counter = 1
    
    # Main loop
    for i in range(len(list_of_urls)):
            
            # Check if URL has been already fetched
            if already_pending_or_fetched_url(list_of_urls[i], db):

                logger.info(f"Skipping already fetched URL: {list_of_urls[i]}")
                continue

            date = str(now_with_hours())

            try:

                insert_url(list_of_urls[i], db, date)

                logger.info(f"{page_counter}. Inserted URL: {list_of_urls[i]}")

                update_url_status(list_of_urls[i], db, status="pending")

                logger.info(f"{page_counter}. Marked pending status for URL: {list_of_urls[i]}")

                page_counter += 1

            except Exception:

                error_logger.error(f"Failed to insert URL: {list_of_urls[i]} in DB for reason",
                exc_info = True)

                page_counter += 1

#######################################################

def run_crawler_seed(
    db: dict,
    specific_site_config,
    seed_url: str,
    site_name: str,
    pages_to_crawl: int,
    logger: logging.Logger,
    error_logger: logging.Logger
    ):

    canonical_url = resolve_pagination(
    specific_site_config, 
    seed_url, 
    site_name, 
    error_logger
    )

    print(canonical_url)

    list_of_urls = alrogithmic_paginator(
        specific_site_config,
        pages_to_crawl,
        canonical_url
    )

    db_insert_paginated_urls(
        db, 
        list_of_urls, 
        logger, 
        error_logger)
    
