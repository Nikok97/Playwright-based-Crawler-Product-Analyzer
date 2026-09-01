import logging
import pytest

from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock
from playwright.sync_api import Page

from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll, write_html
from crawler.crawler_product_scraper import update_fetch_status_in_product_pages
from crawler.crawler_product_html_parser import run_crawler_product_html_parser, create_folder_with_date_of_parse_in_output_dir, update_parse_status, reset_stuck_parsing_jobs, get_fetched_product
from crawler.crawler_search_html_parser import insert_product_url
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

class FakeSiteConfig:
    def __init__(self, selector_to_start_process : str) -> None:
        self.selector_to_start_process : str = selector_to_start_process
        self.count = 1

    def individual_product_data_extraction(self, soup):

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

    
fake_site_config = FakeSiteConfig('dummy_selector')

# Fake Playwright page
class FakePage:
    def __init__(self) -> None:
        pass
    def goto(self, url, timeout=0):
        pass
    def reload(self, timeout=0):
        pass
    def wait_for_selector(self, wait_selector, timeout=0):
        pass
fake_page = FakePage()

@pytest.fixture
def url_for_testing():
    test_url = "www.mdp.com"
    return test_url

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

@pytest.fixture
def products_for_testing() -> list[dict]:
    test_product = {
        'link': 'product_1.com',
        'slug': 'product_1_com',
        'currency': '$',
        "price": 5,
        "product_code": 'TEST_CODE',
        "reviews": "review",
        "images": ["image.com"]
    }
    test_product_2 = {
        'link': 'product_2.com',
        'slug': 'product_2_com',
        'currency': '$',
        "price": 5,
        "product_code": 'TEST_CODE',
        "reviews": "review",
        "images": ["image.com"]
    }
    test_products = [test_product, test_product_2]

    return test_products

@pytest.fixture
def date_for_testing():
    date_for_testing = "22.5.1997"
    return date_for_testing

@pytest.fixture
def tmp_output_dir(tmp_path):

    dir = tmp_path / 'data_dir' / 'output_dir'
    dir.mkdir(parents= True, exist_ok=True)
    path_dict = {'output_dir': dir}

    return path_dict

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)


def test_run_crawler_product_html_parser(tmp_db, tmp_output_dir, product_for_testing):

    filename = 'product_1.html'

    html = 'html_content'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    write_html(html_path, filename, html)

    run_crawler_product_html_parser(tmp_db, fake_site_config, tmp_output_dir, logger, error_logger)

    tmp_db['cur'].execute('SELECT product_name, parse_status from ProductPages WHERE product_url = ? ', (product_for_testing["link"],))

    assert html_path.exists()

    row = tmp_db['cur'].fetchone()

    assert row == ('product_1_com','parsed_succeeded')

def test_failed_archiving_does_not_invalidate_successful_state_of_parsing_of_a_product(tmp_db, tmp_output_dir, product_for_testing):

    filename = 'product_1.html'

    html = 'html_content'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    file_path_of_archived_html = create_folder_with_date_of_parse_in_output_dir(tmp_output_dir)
    file_path_of_archived_html = file_path_of_archived_html / filename

    write_html(html_path, filename, html)

    with patch.object(Path, "rename") as patched_rename:

        patched_rename.side_effect = OSError("archive failed")

        run_crawler_product_html_parser(tmp_db, fake_site_config, tmp_output_dir, logger, error_logger)


    tmp_db['cur'].execute('SELECT product_name, parse_status from ProductPages WHERE product_url = ? ', (product_for_testing["link"],))

    assert not file_path_of_archived_html.exists()

    row = tmp_db['cur'].fetchone()

    assert row == ('product_1_com','parsed_succeeded')

def test_failed_archiving_does_not_impede_loop_from_continuing(tmp_db, tmp_output_dir, products_for_testing):

    filename = 'product_1.html'
    filename_2 = 'product_2.html'

    html_content = 'html_content'
    html_content_2 = 'html_content_2'

    insert_product_url(tmp_db, products_for_testing[0], 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    insert_product_url(tmp_db, products_for_testing[1], 2, error_logger)

    update_fetch_status_in_product_pages(2, tmp_db , filename_2, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    file_path_of_archived_html = create_folder_with_date_of_parse_in_output_dir(tmp_output_dir)
    file_path_of_archived_html = file_path_of_archived_html / filename

    write_html(html_path, filename, html_content)
    write_html(html_path, filename_2, html_content_2)

    class FakeSiteConfig:
        def __init__(self, selector_to_start_process : str) -> None:
            self.selector_to_start_process : str = selector_to_start_process
            self.count = 1

        def individual_product_data_extraction(self, soup):
            test_product = {
            'link': 'product_1.com',
            'slug': 'product_1_com',
            'currency': '$',
            "price": 5,
            "product_code": 'TEST_CODE',
            "reviews": "review",
            "images": ["image.com"]
        }

            test_product_2 = {
            'link': 'product_2.com',
            'slug': 'product_2_com',
            'currency': '$',
            "price": 5,
            "product_code": 'TEST_CODE',
            "reviews": "review",
            "images": ["image.com"]
        }
            if self.count == 1:
                self.count += 1
                return test_product
            elif self.count == 2:
                return test_product_2

    fake_site_config_for_this_test = FakeSiteConfig('dummy_selector')

    with patch.object(Path, "rename") as patched_rename:

        patched_rename.side_effect = [OSError("archive failed"), 
        None]

        run_crawler_product_html_parser(tmp_db, fake_site_config_for_this_test, tmp_output_dir, logger, error_logger)

    # 1st product
    tmp_db['cur'].execute('SELECT product_name, parse_status from ProductPages WHERE product_url = ? ', ('product_1.com',))

    assert not file_path_of_archived_html.exists()

    row = tmp_db['cur'].fetchone()

    assert row == ('product_1_com','parsed_succeeded')
   
    # 2nd product
    tmp_db['cur'].execute('SELECT product_name, parse_status from ProductPages WHERE product_url = ? ', ('product_2.com',))

    #assert file_path_of_archived_html.exists()

    row = tmp_db['cur'].fetchone()

    assert row == ('product_2_com','parsed_succeeded')

def test_database_transaction_rollback_when_product_update_succeeds_but_update_status_fails(tmp_db, tmp_output_dir, product_for_testing):

    """
    product row starts:
    product fields = old/empty values
    parse_status = parsing

    update_product_data(...)               ✓
    update_parse_status("parsed_succeeded") ✗
    ROLLBACK

    recovery:
    update_parse_status("parsing_failed")   ✓
    COMMIT

    """

    filename = 'product_1.html'

    html_content = 'html_content'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    write_html(html_path, filename, html_content)

    fake_site_config_for_this_test = FakeSiteConfig('dummy_selector')


    def fake_update_product_parse_status(row_id, db, status):

        if status == ("parsed_succeeded"):

            raise Exception()

        else:

            print(f'STATUS RECEIVED IS {status}')

            return update_parse_status(row_id, db, status)

    
    with patch('crawler.crawler_product_html_parser.update_parse_status') as mock:

        mock.side_effect = fake_update_product_parse_status

        run_crawler_product_html_parser(tmp_db, fake_site_config_for_this_test, tmp_output_dir, logger, error_logger)

    # 1st product
    tmp_db['cur'].execute('SELECT product_name, parse_status from ProductPages WHERE product_url = ? ', ('product_1.com',))

    row = tmp_db['cur'].fetchone()

    assert row == (None,'parsing_failed')

def test_parser_recovery_logic_for_fetched_and_parsing_product_pages(tmp_db, product_for_testing):

    filename = 'product_1.html'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    update_parse_status(1, tmp_db, 'parsing')

    tmp_db["conn"].commit()

    reset_stuck_parsing_jobs(tmp_db)

    # 1st product
    tmp_db['cur'].execute('SELECT fetch_status, parse_status from ProductPages WHERE product_url = ? ', ('product_1.com',))

    row = tmp_db['cur'].fetchone()

    assert (row == ('fetched', None))


def test_parser_state_management_for_fetched_and_parsed_suceeded_product_pages(tmp_db, product_for_testing):
    '''
    Arrange:
    row has fetch_status = "fetched"
    and parse_status = "parsed_succeeded"

    Act:
    call get_fetched_product(db)

    Assert:
    that row is not returned
    and its state remains ("fetched", "parsed_succeeded")
    '''

    filename = 'product_1.html'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    update_parse_status(1, tmp_db, 'parsed_succeeded')

    tmp_db["conn"].commit()

    get_fetched_product(tmp_db)

    # 1st product
    tmp_db['cur'].execute('SELECT product_name, fetch_status, parse_status from ProductPages WHERE product_url = ? ', ('product_1.com',))

    row = tmp_db['cur'].fetchone()

    assert row == (None, 'fetched', 'parsed_succeeded')

def test_parser_state_management_for_fetched_and_unparsed_product_pages(tmp_db, product_for_testing):

    """
    Arrange:
    one row with fetch_status="fetched"
    and parse_status=NULL

    Act:
    call get_fetched_product(db)

    Assert:
    1. it returns that product
    2. its database state is now ("fetched", "parsing")
    """

    filename = 'product_1.html'

    insert_product_url(tmp_db, product_for_testing, 1, error_logger)

    update_fetch_status_in_product_pages(1, tmp_db , filename, status='fetched')

    tmp_db["conn"].commit()

    product = get_fetched_product(tmp_db)

    # 1st product
    tmp_db['cur'].execute('SELECT fetch_status, parse_status from ProductPages WHERE product_url = ? ', ('product_1.com',))

    row = tmp_db['cur'].fetchone()

    assert product == (1, 'product_1.com', None, 'product_1.html')

    assert row == ('fetched', 'parsing')