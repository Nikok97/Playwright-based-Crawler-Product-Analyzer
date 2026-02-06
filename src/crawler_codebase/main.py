# main.py
import json

from crawler.crawler_seed import run_crawler_seed
from crawler.crawler_search_scraper import run_crawler_search_scraper
from crawler.crawler_search_html_parser import run_crawler_search_html_parser
from crawler.crawler_product_scraper import run_crawler_product_scraper
from crawler.crawler_product_html_parser import run_crawler_product_html_parser

from utilities.utils import (
    setup_loggers,
    setup_directories_pathlib,
    interactive_decision_helper
)
from utilities.specific_sites import (
    site_registry, 
    specific_site_setup
)
from utilities.database import db_initialization

# Entry point
if __name__ == "__main__":

    #Run flags
    STAGES = {
        "seed": True,
        "search_scraper": True,
        "search_parser": True,
        "product_scraper": True,
        "product_parser": True,
    }

    # Entry UI, ask user
    interactive_decision_helper(STAGES)

    # Resolve project directory structure
    paths_dict = setup_directories_pathlib()

    # Load runtime configuration
    config_path = paths_dict["base_dir"] / "config.json"
    with open(config_path) as f:
        config = json.load(f)
        db_path = config.get("database_path", "mini.sqlite")
        site_name = config["site"]
        pages_to_crawl = config["pages_to_crawl"]

    # Initialize logging
    logger, error_logger = setup_loggers()

    # Specific site config
    SITE_REGISTRY = site_registry()
    specific_site_config, seed_url = specific_site_setup(SITE_REGISTRY, site_name)

    # DB variables setup
    db = None
    db_path = paths_dict['data_dir'] / db_path

    try:
        # DB init
        db = db_initialization(db_path)

        # Run Crawler_seed
        if STAGES['seed']:
            logger.info("Started Crawler_seed")

            run_crawler_seed(
            specific_site_config,
            seed_url,
            site_name,
            logger,
            error_logger,
            pages_to_crawl,
            db
        )

        # Run Crawler_search_scraper
        if STAGES["search_scraper"]:
            logger.info("Started crawler_search_scraper")
            run_crawler_search_scraper(
                db, 
                specific_site_config,
                logger,
                error_logger,
                paths_dict
            )
            
        # Run Crawler_search_html_parser
        if STAGES["search_parser"]:
            logger.info("Started crawler_search_html_parser")
            run_crawler_search_html_parser(
                db, 
                paths_dict, 
                specific_site_config, 
                logger, 
                error_logger,
            )
        
        # Run Crawler_product_scraper
        if STAGES["product_scraper"]:
            logger.info("Started crawler_product_scraper")
            run_crawler_product_scraper(
                db,
                paths_dict, 
                logger,
                error_logger
            )

        # Run Crawler_product_html_parser
        if STAGES["product_parser"]:
            logger.info("Started crawler_product_html_parser")
            run_crawler_product_html_parser(
                db, 
                paths_dict, 
                specific_site_config, 
                logger, 
                error_logger
            )
    
    except Exception:
        error_logger.error("The following error ocurred when running main module: ", exc_info=True)
            
    finally:
        if db:
            db["cur"].close()
            db["conn"].close()