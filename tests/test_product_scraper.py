import logging
import pytest
import sqlite3

from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock, create_autospec, call, create_autospec
from playwright.sync_api import Page

from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status, insert_product_url
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll
from crawler.crawler_product_scraper import get_pending_product_url, scrape_product_urls, process_single_url
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

@pytest.fixture
def connection_number_two_on_same_db(tmp_path):

    # 1. Open connection (creates the file if it doesn't exist)
    temp_db_path = tmp_path / "temp_db.sqlite"

    conn = sqlite3.connect(temp_db_path)

    # 2. Open cursor
    cur = conn.cursor()

    db = {'conn': conn, 'cur': cur}

    yield db

    # 3. Close everything when done
    cur.close()
    conn.close()

# fakesite config
class FakeSiteConfig:
    def __init__(self, wait_selector : str) -> None:
        self.products = []
        self.wait_selector : str = wait_selector
    def add_products(self, list_of_products : list[dict[str, str]]):
        self.products.append(list_of_products)

    def product_extraction(self, soup):
        return self.products

# Fake Playwright page
class FakePage:
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
def date_for_testing():
    date_for_testing = "22.5.1997"
    return date_for_testing

@pytest.fixture
def individual_product_page_for_testing():
    dic = {'link': 'www.product.com'}
    return dic

@pytest.fixture
def tmp_paths_dict(tmp_path):

    data_dir = tmp_path / 'data_dir'
    data_dir.mkdir(parents= True, exist_ok=True)
    output_dir = data_dir / 'output_dir'
    output_dir.mkdir(parents=True, exist_ok=True)
    paths_dict = {'data_dir': data_dir,
                 'output_dir' : output_dir}

    return paths_dict

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)


def test_get_pending_product_url_happy_path(tmp_db, individual_product_page_for_testing):

    insert_product_url(tmp_db, individual_product_page_for_testing)

    result = get_pending_product_url(tmp_db)

    tmp_db['cur'].execute("SELECT fetch_status from ProductPages where product_url = ? ", (individual_product_page_for_testing['link'],))
    status = tmp_db['cur'].fetchone()

    assert status[0] == 'fetching'
    assert result == (1,'www.product.com' )

def test_get_pending_product_url_no_product_url(tmp_db, individual_product_page_for_testing):

    result = get_pending_product_url(tmp_db)

    tmp_db['cur'].execute("SELECT fetch_status from ProductPages where product_url = ? ", (individual_product_page_for_testing['link'],))
    status = tmp_db['cur'].fetchone()

    assert status is None
    assert result == (None, None)

def test_scrape_urls_happy_path(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, url, logger, wait_selector, page_loading=load_page, perform_scrolling=perform_scroll, html_extracting=extract_html):
        return 'html_content'

    insert_product_url(tmp_db, individual_product_page_for_testing)

    with patch('utilities.utils.countdown_sleep_timer'):
        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    # file path exists
    assert html_path.exists()

    # assert html contains the right content 
    assert html_path.read_text() == 'html_content'

    # assert fetch status in product pages is fetched
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', (individual_product_page_for_testing['link'],))
    result = tmp_db['cur'].fetchone()

    assert result[0] == 'fetched'

def test_scrape_urls_unhappy_path_failed_html_fetching(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector') 

    def fake_html_fetching( page, product_url, logger, wait_selector): 
        return None 

    insert_product_url(tmp_db, individual_product_page_for_testing) 

    with patch('utilities.utils.countdown_sleep_timer'): 
        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching) 

    html_path = tmp_paths_dict["output_dir"] / "product_1.html" 

    # file path exists 
    assert not html_path.exists() 

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', (individual_product_page_for_testing['link'],)) 
    result = tmp_db['cur'].fetchone() 
    assert result[0] == 'failed'

def test_scrape_urls_unhappy_path_failed_html_writing(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'test_html_content'

    insert_product_url(tmp_db, individual_product_page_for_testing)

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer'), 
          patch("crawler.crawler_product_scraper.write_html") as mock_write_html):

        mock_write_html.return_value = False

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    mock_write_html.assert_called_once()

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    # file path does not exist
    assert not html_path.exists()

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', (individual_product_page_for_testing['link'],))
    result = tmp_db['cur'].fetchone()

    assert (result[0] == 'failed')

def test_scrape_urls_unhappy_path_no_product_url_in_db(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'test_html_content'

    fake_html_fetching = Mock(fake_html_fetching)

    insert_product_url(tmp_db, {'link': None})

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer'), 
          patch("crawler.crawler_product_scraper.write_html") as mock_write_html):

        mock_write_html.return_value = False

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    fake_html_fetching.assert_not_called()
    mock_write_html.assert_not_called()

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where id=1')
    result = tmp_db['cur'].fetchone()

    assert (result[0] == 'failed_unfetchable')


def test_scrape_urls_unhappy_path_fetch_html_interrupted_by_keyboard(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching)

    fake_html_fetching.side_effect = KeyboardInterrupt()

    insert_product_url(tmp_db, {'link': 'product.com'})

    with pytest.raises(KeyboardInterrupt):

        with (patch('crawler.crawler_product_scraper.countdown_sleep_timer'), 
            patch("crawler.crawler_product_scraper.write_html") as mock_write_html):

            mock_write_html.return_value = False

            scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    fake_html_fetching.assert_called_once()
    mock_write_html.assert_not_called()

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', ('product.com',))
    result = tmp_db['cur'].fetchone()

    assert (result[0] == 'pending')

def test_scrape_urls_unhappy_path_fetch_html_produces_exception(tmp_db, tmp_paths_dict):

    """
    first selected row
    → fetch_html raises Exception
    → row becomes "failed"
    → write_html is skipped
    → error_logger.error(...) is called
    """

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching, side_effect= Exception())

    mock_error_logger = Mock(error_logger)

    insert_product_url(tmp_db, {'link': 'product.com'})
    #insert_product_url(tmp_db, {'link': 'product_2.com'})

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer'), 
        patch("crawler.crawler_product_scraper.write_html") as mock_write_html
    ):
        mock_write_html.return_value = False

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, mock_error_logger, fetch_html=fake_html_fetching)

    # assert right call count
    assert fake_html_fetching.call_count == 1
    assert mock_write_html.call_count == 0

    # assert error logger is called with x params
    mock_error_logger.error.assert_called_once_with("Unhandled error in product scraper", exc_info=True)

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', ('product.com',))

    result = tmp_db['cur'].fetchone()

    assert (result[0] == 'failed')

def test_no_product_url_does_not_impede_loop_from_continuing(tmp_db, individual_product_page_for_testing, tmp_paths_dict):

    mock_fake_html_fetching = create_autospec(process_single_url)

    insert_product_url(tmp_db, {'link': None})
    insert_product_url(tmp_db, individual_product_page_for_testing)

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'), patch('crawler.crawler_product_scraper.write_html') as mock_write_html:

        mock_fake_html_fetching.side_effect = ['test_html_content']

        mock_write_html.return_value = 'Function_successfully_called'

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, FakeSiteConfig('dummy_selector'), logger, error_logger, fetch_html=mock_fake_html_fetching)

    mock_fake_html_fetching.assert_called_once()

    mock_write_html.assert_called_once_with(tmp_paths_dict['output_dir'], 'product_1.html', 'test_html_content')

def test_scrape_urls_unhappy_path_fetch_html_produces_exception_but_continues(tmp_db, tmp_paths_dict):

    """
    first selected row
    → fetch_html raises Exception
    → row becomes "failed"
    → write_html is skipped
    → error_logger.error(...) is called
    → function continues rather than re-raising
    """

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching)

    fake_html_fetching.side_effect = [Exception(), "html_content"]

    mock_error_logger = Mock(error_logger)

    insert_product_url(tmp_db, {'link': 'product.com'})
    insert_product_url(tmp_db, {'link': 'product_2.com'})

    mock_error_logger.assert_called_with

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer'),
    ):

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, mock_error_logger, fetch_html=fake_html_fetching)

    # assert right call count
    assert fake_html_fetching.call_count == 2

    # assert error logger is called with x params
    mock_error_logger.error.assert_called_once_with("Unhandled error in product scraper", exc_info=True)

    # assert html file path and content for url 2
    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    # file path exists
    assert html_path.exists()

    # assert html contains the right content 
    assert html_path.read_text() == 'html_content'

    # assert fetch status in product pages is failed
    tmp_db['cur'].execute('SELECT product_url, fetch_status from ProductPages where product_url=?', ('product.com',))
    result = tmp_db['cur'].fetchone()
    assert (result == ('product.com', 'failed'))

    tmp_db['cur'].execute('SELECT product_url, fetch_status from ProductPages where product_url=?', ('product_2.com',))
    result = tmp_db['cur'].fetchone()
    assert (result == ('product_2.com', 'fetched'))

def test_scrape_urls_special_wait_time_is_triggered(tmp_db, tmp_paths_dict):

    """
    page_counter=5
    random.uniform patched to return 6
    countdown_sleep_timer patched as mock_countdown
    assert_any_call(6)
    """

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return 'html_content'

    fake_site_config = FakeSiteConfig('dummy_wait_selector')

    insert_product_url(tmp_db, {'link': 'product.com'})

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer') as mock_countdown_sleep_timer,
    patch('crawler.crawler_product_scraper.random.uniform') as mock_random_uniform):

        mock_random_uniform.return_value = 6

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site_config, logger, error_logger, page_counter=5, fetch_html=fake_html_fetching)

    mock_countdown_sleep_timer.assert_any_call(6)

    html_path = tmp_paths_dict["output_dir"] / "product_5.html"

    assert html_path.exists()
    assert html_path.read_text() == 'html_content'

def test_scrape_urls_special_wait_time_is_not_triggered(tmp_db, tmp_paths_dict):

    """
    page_counter = 4
    → condition is false
    → special wait should not happen
    """

    def fake_html_fetching(
                page, 
                product_url, 
                logger, 
                wait_selector):
        return None

    fake_site_config = FakeSiteConfig('dummy_wait_selector')

    insert_product_url(tmp_db, {'link': 'product.com'})

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer') as mock_countdown_sleep_timer,
    patch('crawler.crawler_product_scraper.random.uniform') as mock_random_uniform):

        mock_random_uniform.return_value = 6

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site_config, logger, error_logger, page_counter=4, fetch_html=fake_html_fetching)

    mock_countdown_sleep_timer.assert_not_called()

    html_path = tmp_paths_dict["output_dir"] / "product_4.html"

    assert not html_path.exists()

def test_page_counter_does_not_advance(tmp_db, tmp_paths_dict):

    """
    first product:
    fetch_html returns None
    → scraper marks it failed
    → write_html is skipped
    → page_counter does not advance

    second product:
    fetch_html returns "html_content"
    → real write_html runs
    → product_1.html is created
    """

    fake_html_fetching_mock = create_autospec(process_single_url)

    fake_html_fetching_mock.side_effect = [None, 'html_content']

    fake_site_config = FakeSiteConfig('dummy_wait_selector')
    
    insert_product_url(tmp_db, {'link': 'product.com'})
    insert_product_url(tmp_db, {'link': 'product_2.com'})

    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer')):

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site_config, logger, error_logger, page_counter=1, fetch_html=fake_html_fetching_mock)

    tmp_db['cur'].execute('SELECT fetch_status FROM ProductPages WHERE product_url = ?', ('product.com',))

    result = tmp_db['cur'].fetchone()

    assert result[0] == 'failed'

    tmp_db['cur'].execute('SELECT fetch_status FROM ProductPages WHERE product_url = ?', ('product_2.com',))

    result = tmp_db['cur'].fetchone()

    assert result[0] == 'fetched'

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    assert html_path.exists()
    assert html_path.read_text() == 'html_content'

def test_scrape_urls_happy_path_two_urls(tmp_db, tmp_paths_dict, tmp_path, connection_number_two_on_same_db):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    fake_html_fetching : Mock = create_autospec(process_single_url)
    fake_html_fetching.return_value = 'html_content'

    expected_calls = [call(fake_page, "product_1.com", logger, wait_selector="dummy_wait_selector"), call(fake_page, "product_2.com", logger, wait_selector="dummy_wait_selector"),]

    insert_product_url(tmp_db, {'link': 'product_1.com'})
    insert_product_url(tmp_db, {'link': 'product_2.com'} )

    with patch('utilities.utils.countdown_sleep_timer'):
        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"
    html_path_2 = tmp_paths_dict["output_dir"] / "product_2.html"

    # assert call args
    assert fake_html_fetching.call_args_list == expected_calls

    # file path exists
    assert html_path.exists()
    assert html_path_2.exists()

    # assert html contains the right content 
    assert html_path.read_text() == 'html_content'
    assert html_path_2.read_text() == 'html_content'

    # assert fetch status in product pages is fetched for product 1
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', ('product_1.com',))
    result = tmp_db['cur'].fetchone()

    assert result[0] == 'fetched'

    # assert fetch status in product pages is fetched for product 2
    tmp_db['cur'].execute('SELECT fetch_status from ProductPages where product_url=?', ('product_2.com',))
    result = tmp_db['cur'].fetchone()

    assert result[0] == 'fetched'

    # assert status is commited using a second db connection
    connection_number_two_on_same_db["cur"].execute(
        "SELECT fetch_status FROM ProductPages WHERE product_url=?",
        ("product_2.com",)
    )
    result_2 = connection_number_two_on_same_db["cur"].fetchone()

    assert result_2[0] == "fetched"














    







    
















