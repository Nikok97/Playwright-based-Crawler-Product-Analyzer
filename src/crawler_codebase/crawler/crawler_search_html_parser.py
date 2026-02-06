from bs4 import BeautifulSoup
from pathlib import Path
from utilities.utils import list_of_html_files_compiler

def insert_product_url(db, individual_product, url_id):
    """Stores product information related to a product URL in the database.
    """
    try:
        db["cur"].execute('''
        INSERT OR IGNORE INTO ProductPages (product_url, product_name, fetch_status)
        VALUES ( ?, ?, ? )
        ''', (individual_product["link"], individual_product["slug"], "pending"))
        db["conn"].commit()
        return True
    except Exception as e:
        print(f"Unknown DB error for {url_id}: {e}")
        return False


########################################################

def run_crawler_search_html_parser(
        db, 
        paths_dict, 
        specific_site_config, 
        logger, 
        error_logger
    ):

    list_of_html_files = list_of_html_files_compiler(paths_dict['data_dir'])
    if not list_of_html_files:
        logger.info("Failed to create list of html files in data dir")
        return

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

                #DB Product insertion
                total_number_of_products_in_page = len(products_of_page)

                for idx, individual_product in enumerate(products_of_page, start=1):

                    if insert_product_url(db, individual_product, url_id):
                        logger.info(
                            f"Inserted product {idx} of {total_number_of_products_in_page} for URL {url_id}"
                        )
                    else:
                        logger.info(
                            f"Failed to insert product {idx} of {total_number_of_products_in_page} for URL {url_id}"
                        )

        except Exception:
            error_logger.error(f"Unhandled exception for {file}", exc_info=True)












