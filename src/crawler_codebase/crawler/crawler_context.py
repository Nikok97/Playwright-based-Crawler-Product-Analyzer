from logging import Logger

class CrawlerContext:
    def __init__(self, db: dict, paths_dict: dict, site_config: tuple, seed_url: str, site_name: str , pages_to_crawl: int, logger: Logger, error_logger: Logger):
        self.db = db
        self.paths_dict = paths_dict
        self.specific_site_config = site_config
        self.seed_url = seed_url
        self.site_name = site_name
        self.pages_to_crawl = pages_to_crawl
        self.logger = logger
        self.error_logger = error_logger
