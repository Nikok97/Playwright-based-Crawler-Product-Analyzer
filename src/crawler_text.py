from bs4 import BeautifulSoup
import json
from db import db_initialization, insert_product, get_url_and_id_using_filename
from utils import setup_loggers, setup_directories_pathlib, list_of_html_files_compiler
from specific_sites import site_registry, specific_site_setup

#Config directories
paths_dict = setup_directories_pathlib()

#Load config
config_path = paths_dict["base_dir"] / "config.json"
with open(config_path) as f:
    config = json.load(f)
    config_db_path = config.get("database_path", "mini.sqlite")
    site_name = config["site"]

#Specific site config
SITE_REGISTRY = site_registry()
specific_site_config, seed_url = specific_site_setup(SITE_REGISTRY, site_name)

#DB setup
db_path = paths_dict["data_dir"] / config_db_path
db = db_initialization(db_path)

#Logging setup
logger, error_logger = setup_loggers()

#List builder
list_of_html_files = list_of_html_files_compiler(paths_dict["data_dir"])
if not list_of_html_files:
    error_logger.error(f"List bulding failed", exc_info=True)
    raise RuntimeError

#Main logic
try:
    for file in list_of_html_files:            
        try:
            filename = file
            file_path = paths_dict["data_dir"] / file
            print(file_path)

            with open(file_path, "r", encoding="utf-8") as f:

                #1. Get URL id using filename
                url_id, url = get_url_and_id_using_filename(db, filename)

                #2. Extract soup
                soup = BeautifulSoup(f, 'html.parser')

                #3. Containers, price, currency and name extraction
                
                products_of_page = specific_site_config.product_extraction(soup)
                counter_of_products_per_page = 1

                #DB Product insertion
                for individual_product in products_of_page:

                    total_number_of_products_in_page = int(len(products_of_page))

                    #Go over the list products of page and insert the product with the corresponding URL_ID in the DB
                    insert_product(db, individual_product, url_id)
                    print(f"Inserted product {counter_of_products_per_page} of {total_number_of_products_in_page} for URL {url_id}")
                    counter_of_products_per_page += 1

        except Exception:
            error_logger.error(f"Parsing failed for {file}", exc_info=True)
finally:
    db["cur"].close()
    db["conn"].close()











