# test_vertical_slice.py

import logging
import pytest

from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll, write_html, now_with_hours
from utilities.specific_sites import BooksToScrape

from crawler.crawler_search_scraper import scrape_urls
from crawler.crawler_search_html_parser import insert_product_url, crawler_search_html_parser
from crawler.crawler_product_scraper import update_fetch_status_in_product_pages, scrape_product_urls
from crawler.crawler_product_html_parser import run_crawler_product_html_parser, create_folder_with_date_of_parse_in_output_dir, update_parse_status, reset_stuck_parsing_jobs, get_fetched_product, parse_product_html_files

from unittest.mock import Mock, create_autospec, patch, call
from pathlib import Path


"""
pending Urls row
→ scrape_urls()
→ page_1.html
→ crawler_search_html_parser()
→ ProductPages pending product URL
→ scrape_product_urls()
→ product_1.html
→ run_crawler_product_html_parser()
→ ProductPages contains parsed slug/price
"""

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

# Fake Playwright page
class FakePage:
    def goto(self, url, timeout=0):
        pass
    def reload(self, timeout=0):
        pass
    def wait_for_selector(self, wait_selector, timeout=0):
        pass
fake_page = FakePage()

# fakesite config
class FakeSiteConfig:
    def __init__(self, wait_selector : str) -> None:
        self.products = []
        self.products_for_product_parser = None
        self.wait_selector : str = wait_selector
        self.selector_to_start_process = ''
    def add_products(self, list_of_products : dict[str, str]):
        self.products.append(list_of_products)
    def add_products_for_crawler_product_parser(self, product : dict[str, str]):
        self.products_for_product_parser = product
    def add_selector_to_start_process(self, selector):
        self.selector_to_start_process = selector

    def product_extraction(self, soup):
        return self.products

    def individual_product_data_extraction(self, soup):
        return self.products_for_product_parser

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)

@pytest.fixture
def tmp_paths_dict(tmp_path):

    data_dir = tmp_path / 'data_dir'
    data_dir.mkdir(parents= True, exist_ok=True)
    output_dir = data_dir / 'output_dir'
    output_dir.mkdir(parents=True, exist_ok=True)
    paths_dict = {'data_dir': data_dir,
                 'output_dir' : output_dir}

    return paths_dict


def test_vertical_slice_of_crawler_no_seed_phase(tmp_db, tmp_paths_dict):

    TEST_URL = "www.product_1.com"

    # Search scraper
    fake_page = FakePage()
    fake_website_config = FakeSiteConfig('dummy_wait_selector')
    fake_website_config.add_selector_to_start_process('dummy_start_selector')


    # This (insert url and update url status) sets the db like Seed stage has to put it
    insert_url(
            TEST_URL,
            tmp_db,
            'X/X/X'
    )

    update_url_status(
        TEST_URL,
        tmp_db,
        status='pending'
    )

    fake_fetch_html = create_autospec(process_single_url)

    FAKE_SEARCH_HTML = """<article class="product_pod"><a href="catalogue/test-product/index.html"></a></article>"""

    fake_fetch_html.return_value = FAKE_SEARCH_HTML

    with patch('crawler.crawler_search_scraper.countdown_sleep_timer'):
        scrape_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page, # type: ignore
            BooksToScrape(),
            logger,
            error_logger,
            page_counter=1,
            fetch_html=fake_fetch_html
        )

    file_path = tmp_paths_dict['data_dir'] / 'page_1.html'

    assert file_path.exists()

    # assert html file existis with the right content at the right location in disk
    with open(file_path,'r', encoding='utf-8') as file:
        html = file.read()
        # html has the right content
        assert html == """<article class="product_pod"><a href="catalogue/test-product/index.html"></a></article>"""

    tmp_db['cur'].execute('SELECT url_name, status from Urls')

    urls_in_db = tmp_db['cur'].fetchone()

    assert urls_in_db == ("www.product_1.com", "fetched")

    # Search parser
    list_of_html_files : list[str] = ['page_1.html']

    #fake_website_config_search_parser = FakeSiteConfig('dummy_wait_selector')
    #fake_website_config_search_parser.add_products({"link": "www.product_1.com"})

    crawler_search_html_parser(
        list_of_html_files,
        tmp_paths_dict,
        BooksToScrape(),
        tmp_db,
        logger,
        error_logger
    )

    tmp_db['cur'].execute('SELECT product_url, fetch_status from ProductPages')

    search_info_in_db : (tuple[str | str] | None) = tmp_db['cur'].fetchone()

    assert search_info_in_db == ("https://books.toscrape.com/catalogue/catalogue/test-product/index.html", 'pending')

    # Product parser

    fake_fetch_product_html = create_autospec(process_single_url)

    FAKE_PRODUCT_HTML = """<h1>Product1</h1>"""

    fake_fetch_product_html.return_value = FAKE_PRODUCT_HTML

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db, 
            tmp_paths_dict, 
            fake_page, 
            BooksToScrape(), 
            logger, 
            error_logger, 
            page_counter=1, 
            fetch_html=fake_fetch_product_html
        )

    file_path_product_parser = tmp_paths_dict['output_dir'] / 'product_1.html'

    assert file_path_product_parser.exists()

    content = file_path_product_parser.read_text()

    assert content == """<h1>Product1</h1>"""

    # Product scraper
    counter_of_products = 1
    
    parse_product_html_files(
        tmp_db,
        tmp_paths_dict,
        BooksToScrape(),
        counter_of_products,
        logger,
        error_logger
    )

    tmp_db['cur'].execute("SELECT product_name, parse_status FROM ProductPages LIMIT 1")

    product_html_info = tmp_db['cur'].fetchone()

    assert product_html_info == ('product1', 'parsed_succeeded')

    # i have yet to assert that the archiving part works
    date_for_archiving = now_with_hours()[0:10]
    file_path_of_archiving : Path = tmp_paths_dict['output_dir'] / f'parse_{date_for_archiving}'

    # assert that the archiving path folder
    assert file_path_of_archiving.exists()
    # assert that the html is there
    file_path_of_archived_file = file_path_of_archiving / 'product_1.html'
    assert file_path_of_archived_file.exists()
    # assert that the html there has the right content
    content_of_archived_file =  file_path_of_archived_file.read_text()
    assert content_of_archived_file == """<h1>Product1</h1>"""