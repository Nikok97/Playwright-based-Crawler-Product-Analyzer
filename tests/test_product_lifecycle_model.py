import logging
import pytest
import sqlite3

from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock, create_autospec, call
from playwright.sync_api import Page

from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status, insert_product_url
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll
from crawler.crawler_product_scraper import get_pending_product_url, scrape_product_urls, process_single_url, occasional_long_pause_to_simulate_browsing, update_fetch_status_in_product_pages
from crawler.crawler_product_html_parser import update_parse_status, get_fetched_product
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

"""
Your next exercise

Use one real temporary SQLite database and one product. The exercise should proceed like this:

Insert the product. Your independent model begins as ("pending", None). Read the real row and compare it with the model.
Insert the product. Compare again.
Call update_fetch_status_in_product_pages(..., status="fetched"). Update the model to ("fetched", None). Compare again.
Call get_fetched_product(). Update the model to ("fetched", "parsing"). Compare again.
Simulate parsing failure with update_parse_status(..., "parsing_failed") and commit. Update the model to ("fetched", "parsing_failed"). Compare one final time.

"""

def read_product_status_from_db(db : dict, url: str) -> tuple[str | None, str | None]:

    db['cur'].execute("SELECT fetch_status, parse_status FROM ProductPages where product_url=?", (url,))
    row = db['cur'].fetchone()
    return row

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
def product_for_testing():
    test_product = {
        'link': 'product_1.com',
        'slug': 'product_1_com',
        'currency': '$',
        "price": 5,
        "product_code": 'TEST_CODE',
        "reviews": "review",
        "images": ["image.com"]
    }
    return test_product

def test_crawler_product_lifecycle_model(tmp_db, product_for_testing):

    # 1. Insert product
    insert_product_url(tmp_db, product_for_testing)

    expected_state = ('pending', None)

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    assert result == expected_state

    # 2.

    get_pending_product_url(tmp_db)

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetching', None)
    
    assert result == expected_state

    # 3.
    update_fetch_status_in_product_pages(1, tmp_db, None, 'fetched')

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', None)

    assert result == expected_state

    # 4.

    get_fetched_product(tmp_db)

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', 'parsing')

    assert result == expected_state


    # 5

    update_parse_status(1, tmp_db, 'parsing_failed')

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', 'parsing_failed')

    assert result == expected_state

    











    #run_crawler_search_scraper()
    #run_crawler_search_html_parser()
    #run_crawler_product_scraper()
    #run_crawler_product_html_parser()


