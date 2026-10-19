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
from utilities.database import Database, db_cur_and_conn_closer
from utilities.site_contract import (
    ConfigurationError,
    SiteCapability,
    SiteCapabilityError,
    SiteContractError,
    WebsiteToScrape
)

def load_config(config_path):
    # Loads the config file and returns it
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
        return config
    
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

    def required_capabilities(self, specific_site_config: WebsiteToScrape) -> frozenset:
        # Both pagination modes end in algorithmic pagination, and the mode
        # declared by the adapter adds its own requirement on top of it.
        return frozenset({
            SiteCapability.ALGORITHMIC_PAGINATION,
            specific_site_config.pagination_capability()
        })

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

    def required_capabilities(self, specific_site_config: WebsiteToScrape) -> frozenset:
        return frozenset({SiteCapability.SEARCH_PAGE_READINESS})

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

    def required_capabilities(self, specific_site_config: WebsiteToScrape) -> frozenset:
        return frozenset({SiteCapability.PRODUCT_URL_EXTRACTION})

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

    def required_capabilities(self, specific_site_config: WebsiteToScrape) -> frozenset:
        return frozenset({SiteCapability.PRODUCT_PAGE_READINESS})
    
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

    def required_capabilities(self, specific_site_config: WebsiteToScrape) -> frozenset:
        return frozenset({SiteCapability.PRODUCT_PAGE_PARSING})

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

def validate_stage_selection(
    stages : dict,
    stage_pipeline : list,
    specific_site_config : WebsiteToScrape):

    """
    Checks the stages selected for this run against the capabilities of the
    chosen site adapter, before any of them is executed.

    Adapters are allowed to be partial, so an unsupported combination is a
    configuration problem of the run, reported here instead of surfacing later as a missing attribute or a missing product URL in the middle of a crawl.
    """

    unsupported_stages = list()

    for stage in stage_pipeline:

        if stage.key not in stages:

            raise ConfigurationError(
                f"Stage {stage.display_name!r} ({stage.key}) is missing from the stage selection."
            )

        # Skipped stages are never validated: an adapter only has to support
        # what the run actually asks from it.
        if not stages[stage.key]:

            continue

        missing = specific_site_config.missing_capabilities(
            stage.required_capabilities(specific_site_config)
        )

        if missing:

            unsupported_stages.append(
                f"{stage.display_name} (requires: "
                f"{', '.join(sorted(capability.value for capability in missing))})"
            )

    if unsupported_stages:

        site_name = getattr(specific_site_config, "SITE_NAME", type(specific_site_config).__name__)

        raise SiteCapabilityError(
            f"[{site_name}] The following selected stages are not supported by this site: "
            f"{'; '.join(unsupported_stages)}. Deselect them for this run or extend the site adapter."
        )


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

    # Pipeline
    stage_pipeline = get_stage_pipeline()

    # Fail early: the selected stages have to be supported by the chosen site,
    # so unsupported combinations are rejected before anything is executed
    try:
        validate_stage_selection(stages, stage_pipeline, specific_site_config)

    except SiteContractError as error:
        error_logger.error(
            f"Invalid stage selection for site: {site_name}",
            exc_info=True
        )
        print(f"Invalid run configuration: {error}")
        return


    # DB variables setup
    database = None
    db_path = paths_dict['data_dir'] / db_path

    try:
        # DB init
        database = Database(db_path)

        # Context
        context = CrawlerContext(database, paths_dict, specific_site_config, seed_url, site_name, pages_to_crawl, logger, error_logger)

        run_pipeline(stages, stage_pipeline, context)
        
    except Exception:
        error_logger.error("The following error occurred when running main module: ", exc_info=True)
            
    finally:
        if database:
            db_cur_and_conn_closer(database)

# Entry point
if __name__ == "__main__":
    main()

