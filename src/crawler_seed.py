import json
import os

from db import db_initialization, insert_url, now, already_fetched_checker, update_url_status
from utils import setup_loggers, setup_directories
from specific_sites import site_registry

#Config setup and directories
BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR = setup_directories()

#Load config
config_path = os.path.join(BASE_DIR, "config.json")
with open(config_path) as f:
    config = json.load(f)
    config_db_path = config.get("database_path", "mini.sqlite") 
    end_position = config["end_position"]
    site_name = config["site"]

#Specific site config
SITE_REGISTRY = site_registry()
if site_name not in SITE_REGISTRY:
    raise ValueError(f"Unsupported site: {site_name}")
specific_site_config = SITE_REGISTRY[site_name]()
seed_url = specific_site_config.seed_urls[0]

#Logging setup
logger, error_logger = setup_loggers()

#DB setup
db_path = os.path.join(DATA_DIR, config_db_path)
db = db_initialization(db_path)

#Pagination
pagination_mode = specific_site_config.pagination_mode
if pagination_mode == "dynamic":
    try:
        canonical_url = specific_site_config.discover_first_paginated_url(seed_url)
    except Exception as e:
        error_logger.critical(
            f"[{site_name}] Dynamic pagination discovery failed for seed URL: {seed_url}"
        )
        raise RuntimeError(
            f"[{site_name}] Cannot determine canonical pagination base. Aborting."
        ) from e
else:
    canonical_url = seed_url

list_of_urls = list()
for i in range(1, end_position):
    url = specific_site_config.build_pagination_url(canonical_url, i)
    list_of_urls.append(url)

#URL DB inserting
page_counter = 1

for i in range(len(list_of_urls)):
        
        #Check if URL has been already fetched
        if already_fetched_checker(list_of_urls[i], db):
            logger.info(f"Skipping already fetched URL: {list_of_urls[i]}")
            continue

        date = str(now())
        try:
            insert_url(list_of_urls[i], db)
            print(f"{page_counter}. Inserted URL: {list_of_urls[i]}")
            update_url_status(list_of_urls[i], db, status="pending")
            print(f"{page_counter}. Marked pending status for URL: {list_of_urls[i]}")
            page_counter += 1
        except Exception as e:
            print(f"Failed to insert URL: {list_of_urls[i]} in DB for reason {e}")
            page_counter += 1

db["conn"].close()


