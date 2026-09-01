# main.py
import json

from crawler.crawler_context import CrawlerContext
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


def load_config(config_path):
    # Loads the config file and returns it
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
        return config
    
def close_db(db):
    # Closes the database if it exists
    if db:
        db["cur"].close()
        db["conn"].close()

def get_default_stages():
    # Returns the stages with the default value True to run the whole program as default setting
    
    stages = {
        "seed": True,
        "search_scraper": True,
        "search_parser": True,
        "product_scraper": True,
        "product_parser": True,
    }

    return stages


class SeedStage:
    # Class that runs the Crawler_seed with its context
    key = "seed"
    display_name = "Crawler seed"
    def run(self, context):
        print("Started stage: Crawler seed")
        run_crawler_seed(
            context.db, 
            context.specific_site_config, 
            context.seed_url, 
            context.site_name, 
            context.pages_to_crawl, 
            context.logger, 
            context.error_logger )

class SearchScraperStage:
    # Class that runs the Crawler_search_scraper with its context
    key = "search_scraper"
    display_name = "Crawler search scraper"
    # Run Crawler_search_scraper
    def run(self, context):
        print("Started stage: Crawler search scraper")
        run_crawler_search_scraper(
            context.db,
            context.specific_site_config,
            context.paths_dict,
            context.logger,         
            context.error_logger
        )
        
class SearchParserStage:
    # Class that runs the Crawler_search_html_parser with its context
    key = "search_parser"
    display_name = "Crawler search parser"
    # Run Crawler_search_html_parser
    def run(self, context):
        print("Started stage: Crawler search parser")
        run_crawler_search_html_parser(
            context.db,
            context.specific_site_config, 
            context.paths_dict, 
            context.logger, 
            context.error_logger,
        )

class ProductScraperStage:
    # Class that runs the Crawler_product_scraper with its context
    key = "product_scraper"
    display_name = "Crawler product scraper"
    # Run Crawler_product_scraper
    def run(self, context):
        print("Started stage: Crawler product scraper")
        run_crawler_product_scraper(
            context.db,
            context.specific_site_config,
            context.paths_dict, 
            context.logger,
            context.error_logger
        )

class ProductParserStage:
    # Class that runs the Crawler_product_html_parser with its context
    key = "product_parser"
    display_name = "Crawler product parser"
    # Run Crawler_product_html_parser
    def run(self, context):
        print("Started stage: Crawler product parser")
        run_crawler_product_html_parser(
            context.db, 
            context.specific_site_config,
            context.paths_dict,  
            context.logger, 
            context.error_logger
        )

        
def load_site_setup(site_name):
    # Loads the site registry, specific site config and seed url
    registry = site_registry()
    specific_site_config, seed_url = specific_site_setup(registry, site_name)

    return specific_site_config, seed_url

def get_stage_pipeline() -> list:
    # Returns the stage pipeline composed of the stage objects
    return [
        SeedStage(),
        SearchScraperStage(),
        SearchParserStage(),
        ProductScraperStage(),
        ProductParserStage(),
    ]

def run_pipeline(stages : dict, stage_pipeline : list, context : CrawlerContext):

    # Runs the stage pipeline
    for stage in stage_pipeline:

        # if stage's key is False, skip

        if not stages[stage.key]:

            context.logger.info("Skipped stage: %s", stage.display_name)

            continue

        # else stage runs
        context.logger.info("Started stage: %s", stage.display_name)
        
        stage.run(context)

        context.logger.info("Finished stage: %s", stage.display_name)

# Def main
def main():

    # Gets the stages
    stages = get_default_stages()

    # Shows the simple decision helper UI
    interactive_decision_helper(stages)

    # Resolve project directory structure
    paths_dict = setup_directories_pathlib()

    # Load runtime configuration
    config_path = paths_dict["base_dir"] / "config.json"
    config = load_config(config_path)
    db_path = config.get("database_path", "mini.sqlite")
    site_name = config["site"]
    pages_to_crawl = config["pages_to_crawl"]

    # Initialize logging
    logger, error_logger = setup_loggers()

    # Specific site config
    specific_site_config, seed_url = load_site_setup(site_name)

    # DB variables setup
    db = None
    db_path = paths_dict['data_dir'] / db_path

    try:
        # DB init
        db = db_initialization(db_path)

        # Context
        context = CrawlerContext(db, paths_dict, specific_site_config, seed_url, site_name, pages_to_crawl, logger, error_logger)

        # Pipeline
        stage_pipeline = get_stage_pipeline()

        run_pipeline(stages, stage_pipeline, context)
        
    except Exception:
        error_logger.error("The following error occurred when running main module: ", exc_info=True)
            
    finally:
        close_db(db)

# Entry point
if __name__ == "__main__":
    main()

