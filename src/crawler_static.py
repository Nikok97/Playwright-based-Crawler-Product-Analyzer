import json
import random
import os

from db import db_initialization, get_and_update_pending_url, update_url_status
from utils import setup_loggers, setup_directories_pathlib, countdown_sleep_timer, process_single_url, list_of_html_files_compiler
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
specific_site_config, _ = specific_site_setup(SITE_REGISTRY, site_name)

#DB setup
db_path = paths_dict["data_dir"] / config_db_path
db = db_initialization(db_path)

#Logging setup
logger, error_logger = setup_loggers()
page_counter = 1

#List builder
list_of_html_files = list_of_html_files_compiler(paths_dict["data_dir"])
if not list_of_html_files:
    error_logger.error(f"List bulding failed", exc_info=True)
    raise RuntimeError

#Static fetching
try:
    for file in list_of_html_files:  
            try:
                filename = file
                file_path = paths_dict["data_dir"] / file
                print(file_path)

                with open(filename, "r", encoding="utf-8") as f:
                    
                    #Main crawling loop
                    while True:

                        try:
                            #Query the db, get one url, starting from the top, and mark them as in_progress
                            url_id, url = get_and_update_pending_url(db)
                            if url is None:
                                print("URL not found. Exiting program")
                                break
                        
                            #Occasional long pause to simulate browsing
                            if (page_counter % 5 == 0) and (page_counter != 0):
                                special_wait_time = random.uniform(50, 90)
                                countdown_sleep_timer(special_wait_time)

                            #Process a single URL
                            if not process_single_url(db=db, url=url, url_id=url_id, page=filename, specific_site_config=specific_site_config, page_counter=page_counter, DATA_DIR=paths_dict["data_dir"]):
                                pass # URL already marked failed inside the function

                            page_counter += 1

                            #Normal safe delay
                            wait_time = random.uniform(30, 55)
                            countdown_sleep_timer(wait_time)

                        except KeyboardInterrupt:
                            if url is not None: # type: ignore
                                update_url_status(url, db, status = "pending") # type: ignore
                            raise
            except:
                pass #PLACEHOLDER
finally:
#Close DB cur, connection and browser
    db["cur"].close()
    db["conn"].close()


