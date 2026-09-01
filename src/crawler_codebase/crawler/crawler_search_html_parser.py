import re

from bs4 import BeautifulSoup
from pathlib import Path
from logging import Logger
from utilities.specific_sites import WebsiteToScrape

def list_of_html_files_compiler(directory: Path) -> list | None:

    page_pattern = re.compile(r"^page_(\d+)\.html$")
    html_files = []

    for path in directory.iterdir():
        if not path.is_file():
            continue

        match = page_pattern.match(path.name)
        if match:
            html_files.append(path.name)

    if not html_files:
        return None

    return sorted(
        html_files,
        key=lambda f: int(page_pattern.match(f).group(1))  # type: ignore
    )

def insert_product_url(db: dict, individual_product: dict, url_id: int, error_logger) -> bool:
    """Stores product information related to a product URL in the database.
    """
    try:
        db["cur"].execute('''
        INSERT OR IGNORE INTO ProductPages (product_url, fetch_status)
        VALUES ( ?, ?)
        ''', (individual_product["link"], "pending"))
        db["conn"].commit()
        return True
    except Exception as e:
        error_logger.error(f"Unknown DB error for {url_id}: {e}")
        return False


########################################################

def run_crawler_search_html_parser(
        db: dict, 
        specific_site_config,
        paths_dict: dict, 
        logger,
        error_logger
    ):

    list_of_html_files = list_of_html_files_compiler(paths_dict['data_dir'])
    
    if not list_of_html_files:
        logger.info("Failed to create list of html files in data dir")
        return

    #Main logic
    crawler_search_html_parser(
        list_of_html_files,
        paths_dict,
        specific_site_config,
        db,
        logger,
        error_logger
    )


########################################

def crawler_search_html_parser(
        list_of_html_files: list,
        paths_dict: dict,
        specific_site_config : WebsiteToScrape,
        db : dict,
        logger: Logger,
        error_logger: Logger
    ):

    #Main logic
    for file in list_of_html_files:
        
        try:

            file = Path(file)
            url_id = int(file.stem.split("_")[1])
            file_path = paths_dict['data_dir'] / file

            with open(file_path, "r", encoding="utf-8") as f:

                #2. Extract soup
                soup = BeautifulSoup(f, 'html.parser')

                #3. Extract product data from search results into a list of dict objects
                products_of_page = specific_site_config.product_extraction(soup)

                # DB Product insertion
                total_number_of_products_in_page = len(products_of_page)

                for idx, individual_product in enumerate(products_of_page, start=1):

                    if insert_product_url(db, individual_product, url_id, error_logger):
                        logger.info(
                            f"Inserted product {idx} of {total_number_of_products_in_page} for URL {url_id}")
                    else:
                        logger.info(
                            f"Failed to insert product {idx} of {total_number_of_products_in_page} for URL {url_id}")
        except Exception:
            error_logger.error(f"Unhandled exception for {file}", exc_info=True)












