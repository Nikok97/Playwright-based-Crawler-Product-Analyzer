import logging
import pytest
import sqlite3

from unittest.mock import patch, Mock, create_autospec, call

from utilities.database import Database
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll
from crawler.crawler_product_scraper import scrape_product_urls, process_single_url, occasional_long_pause_to_simulate_browsing

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

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
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()


def test_get_pending_product_url_happy_path(tmp_db, individual_product_page_for_testing):

    tmp_db.insert_product_url(individual_product_page_for_testing)

    result = tmp_db.get_pending_product_url()

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("SELECT fetch_status from ProductPages where product_url = ? ", (individual_product_page_for_testing['link'],))
        status = cur.fetchone()

        assert status[0] == 'fetching'
        assert result == (1,'www.product.com' )

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_get_pending_product_url_no_product_url(tmp_db, individual_product_page_for_testing):

    result = tmp_db.get_pending_product_url()

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("SELECT fetch_status from ProductPages where product_url = ? ", (individual_product_page_for_testing['link'],))
        status = cur.fetchone()

        assert status is None
        assert result == (None, None)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_happy_path(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(
            page, 
            url, 
            logger, 
            wait_selector, 
            page_loading=load_page, 
            perform_scrolling=perform_scroll, 
            html_extracting=extract_html):
        return 'html_content'

    conn, cur = None, None

    tmp_db.insert_product_url(individual_product_page_for_testing)

    with patch('utilities.utils.countdown_sleep_timer'):
        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site, logger, error_logger, fetch_html=fake_html_fetching)

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    # file path exists
    assert html_path.exists()

    # assert html contains the right content 
    assert html_path.read_text() == 'html_content'

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        # assert fetch status in product pages is fetched
        cur.execute('SELECT fetch_status from ProductPages where product_url=?', (individual_product_page_for_testing['link'],))
        result = cur.fetchone()

        assert result[0] == 'fetched'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_unhappy_path_failed_html_fetching(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return None

    tmp_db.insert_product_url(individual_product_page_for_testing)

    with patch('utilities.utils.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            error_logger,
            fetch_html=fake_html_fetching,
        )

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    assert not html_path.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            (individual_product_page_for_testing['link'],),
        )
        result = cur.fetchone()

        assert result[0] == 'failed'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_unhappy_path_failed_html_writing(tmp_db, tmp_paths_dict, individual_product_page_for_testing):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return 'test_html_content'

    tmp_db.insert_product_url(individual_product_page_for_testing)

    with (
        patch('crawler.crawler_product_scraper.countdown_sleep_timer'),
        patch('crawler.crawler_product_scraper.write_html') as mock_write_html,
    ):
        mock_write_html.return_value = False

        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            error_logger,
            fetch_html=fake_html_fetching,
        )

    mock_write_html.assert_called_once()

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"
    assert not html_path.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            (individual_product_page_for_testing['link'],),
        )
        result = cur.fetchone()

        assert result[0] == 'failed'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_unhappy_path_no_product_url_in_db(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return 'test_html_content'

    fake_html_fetching = Mock(fake_html_fetching)

    tmp_db.insert_product_url({'link': None})

    with (
        patch('crawler.crawler_product_scraper.countdown_sleep_timer'),
        patch('crawler.crawler_product_scraper.write_html') as mock_write_html,
    ):
        mock_write_html.return_value = False

        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            error_logger,
            fetch_html=fake_html_fetching,
        )

    fake_html_fetching.assert_not_called()
    mock_write_html.assert_not_called()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute('SELECT fetch_status FROM ProductPages WHERE id = 1')
        result = cur.fetchone()

        assert result[0] == 'failed_unfetchable'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_unhappy_path_fetch_html_interrupted_by_keyboard(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching)
    fake_html_fetching.side_effect = KeyboardInterrupt()

    tmp_db.insert_product_url({'link': 'product.com'})

    with pytest.raises(KeyboardInterrupt):
        with (
            patch('crawler.crawler_product_scraper.countdown_sleep_timer'),
            patch('crawler.crawler_product_scraper.write_html') as mock_write_html,
        ):
            mock_write_html.return_value = False

            scrape_product_urls(
                tmp_db,
                tmp_paths_dict,
                fake_page,
                fake_site,
                logger,
                error_logger,
                fetch_html=fake_html_fetching,
            )

        fake_html_fetching.assert_called_once()
        mock_write_html.assert_not_called()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product.com',),
        )
        result = cur.fetchone()

        assert result[0] == 'pending'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_unhappy_path_fetch_html_produces_exception(tmp_db, tmp_paths_dict):

    """
    first selected row
    → fetch_html raises Exception
    → row becomes "failed"
    → write_html is skipped
    → error_logger.error(...) is called
    """

    fake_site = FakeSiteConfig('dummy_wait_selector')

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching, side_effect=Exception())
    mock_error_logger = Mock(error_logger)

    tmp_db.insert_product_url({'link': 'product.com'})

    with (
        patch('crawler.crawler_product_scraper.countdown_sleep_timer'),
        patch('crawler.crawler_product_scraper.write_html') as mock_write_html,
    ):
        mock_write_html.return_value = False

        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            mock_error_logger,
            fetch_html=fake_html_fetching,
        )

    assert fake_html_fetching.call_count == 1
    assert mock_write_html.call_count == 0
    mock_error_logger.error.assert_called_once_with(
        'Unhandled error in product scraper',
        exc_info=True,
    )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product.com',),
        )
        result = cur.fetchone()

        assert result[0] == 'failed'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_no_product_url_does_not_impede_loop_from_continuing(tmp_db, individual_product_page_for_testing, tmp_paths_dict):

    mock_fake_html_fetching = create_autospec(process_single_url)

    tmp_db.insert_product_url({'link': None})
    tmp_db.insert_product_url(individual_product_page_for_testing)

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'), patch('crawler.crawler_product_scraper.write_html') as mock_write_html:

        mock_fake_html_fetching.side_effect = ['test_html_content']

        mock_write_html.return_value = 'Function_successfully_called'

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, FakeSiteConfig('dummy_selector'), logger, error_logger, fetch_html=mock_fake_html_fetching)

    mock_fake_html_fetching.assert_called_once()

    mock_write_html.assert_called_once_with(tmp_paths_dict['output_dir'], 'product_2.html', 'test_html_content')

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

    def fake_html_fetching(page, product_url, logger, wait_selector):
        return 'html_content'

    fake_html_fetching = Mock(fake_html_fetching)
    fake_html_fetching.side_effect = [Exception(), 'html_content']

    mock_error_logger = Mock(error_logger)

    tmp_db.insert_product_url({'link': 'product.com'})
    tmp_db.insert_product_url({'link': 'product_2.com'})

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            mock_error_logger,
            fetch_html=fake_html_fetching,
        )

    assert fake_html_fetching.call_count == 2
    mock_error_logger.error.assert_called_once_with(
        'Unhandled error in product scraper',
        exc_info=True,
    )

    html_path = tmp_paths_dict["output_dir"] / "product_2.html"
    assert html_path.exists()
    assert html_path.read_text() == 'html_content'

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT product_url, fetch_status FROM ProductPages WHERE product_url = ?',
            ('product.com',),
        )
        result = cur.fetchone()
        assert result == ('product.com', 'failed')

        cur.execute(
            'SELECT product_url, fetch_status FROM ProductPages WHERE product_url = ?',
            ('product_2.com',),
        )
        result = cur.fetchone()
        assert result == ('product_2.com', 'fetched')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_scrape_urls_special_wait_time_is_triggered(tmp_db, tmp_paths_dict):

    fake_html_fetching : Mock = create_autospec(process_single_url)

    fake_html_fetching.return_value = 'html_content'

    fake_site_config = FakeSiteConfig('dummy_wait_selector')

    tmp_db.insert_product_url({'link': 'product.com'})
    with (patch('crawler.crawler_product_scraper.countdown_sleep_timer') as mock_countdown_sleep_timer, patch('crawler.crawler_product_scraper.occasional_long_pause_to_simulate_browsing') as fake_occasional_pause, patch('crawler.crawler_product_scraper.random.uniform') as mock_random_uniform):

        mock_random_uniform.return_value = 6

        scrape_product_urls(tmp_db, tmp_paths_dict, fake_page, fake_site_config, logger, error_logger, page_counter=5, fetch_html=fake_html_fetching)

    assert fake_occasional_pause.call_count == 1

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"

    assert html_path.exists()
    assert html_path.read_text() == 'html_content'

def test_long_pause_to_simulate_browsing():

    """
    If page_counter is not divisible by 5, the special wait must not occur.
    """
    with patch('crawler.crawler_product_scraper.random.uniform') as mock_random_uniform, patch('crawler.crawler_product_scraper.countdown_sleep_timer') as mock_sleep:

        mock_random_uniform.return_value = 1

        occasional_long_pause_to_simulate_browsing(5)

        occasional_long_pause_to_simulate_browsing(4)

    not_expected = [call(1), call(1)]
    expected = [call(1)]

    assert mock_sleep.call_args_list != not_expected
    assert mock_sleep.call_args_list == expected

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

    tmp_db.insert_product_url({'link': 'product.com'})
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

    tmp_db.insert_product_url({'link': 'product.com'})
    tmp_db.insert_product_url({'link': 'product_2.com'})

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site_config,
            logger,
            error_logger,
            page_counter=1,
            fetch_html=fake_html_fetching_mock,
        )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product.com',),
        )
        result = cur.fetchone()
        assert result[0] == 'failed'

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product_2.com',),
        )
        result = cur.fetchone()
        assert result[0] == 'fetched'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    html_path = tmp_paths_dict["output_dir"] / "product_2.html"
    assert html_path.exists()
    assert html_path.read_text() == 'html_content'

def test_scrape_urls_happy_path_two_urls(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')

    fake_html_fetching: Mock = create_autospec(process_single_url)
    fake_html_fetching.return_value = 'html_content'

    expected_calls = [
        call(fake_page, 'product_1.com', logger, wait_selector='dummy_wait_selector'),
        call(fake_page, 'product_2.com', logger, wait_selector='dummy_wait_selector'),
    ]

    tmp_db.insert_product_url({'link': 'product_1.com'})
    tmp_db.insert_product_url({'link': 'product_2.com'})

    with patch('utilities.utils.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            fake_site,
            logger,
            error_logger,
            fetch_html=fake_html_fetching,
        )

    html_path = tmp_paths_dict["output_dir"] / "product_1.html"
    html_path_2 = tmp_paths_dict["output_dir"] / "product_2.html"

    assert fake_html_fetching.call_args_list == expected_calls

    assert html_path.exists()
    assert html_path_2.exists()
    assert html_path.read_text() == 'html_content'
    assert html_path_2.read_text() == 'html_content'

    # Independent sqlite3 connection verifies the committed state.
    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product_1.com',),
        )
        result = cur.fetchone()
        assert result[0] == 'fetched'

        cur.execute(
            'SELECT fetch_status FROM ProductPages WHERE product_url = ?',
            ('product_2.com',),
        )
        result = cur.fetchone()
        assert result[0] == 'fetched'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_filenaming_of_html_uses_row_ids_and_not_page_counter(tmp_db, tmp_paths_dict):

    fake_site = FakeSiteConfig('dummy_wait_selector')
    fake_html_fetching: Mock = create_autospec(process_single_url)
    fake_html_fetching_round_2: Mock = create_autospec(process_single_url)

    tmp_db.insert_product_url({'link': 'product_1.com'})

    fake_html_fetching.return_value = 'html_content'

    try:

        with patch('utilities.utils.countdown_sleep_timer'):
            scrape_product_urls(
                tmp_db,
                tmp_paths_dict,
                fake_page,
                fake_site,
                logger,
                error_logger,
                fetch_html=fake_html_fetching,
            )

        html_path = tmp_paths_dict["output_dir"] / "product_1.html"

        assert html_path.exists()
        assert html_path.read_text() == 'html_content'

    finally:
        pass

    # 2nd round

    tmp_db.insert_product_url({'link': 'product_2.com'})
    fake_html_fetching_round_2.return_value = 'html_content_2'

    try:
        with patch('utilities.utils.countdown_sleep_timer'):
            scrape_product_urls(
                tmp_db,
                tmp_paths_dict,
                fake_page,
                fake_site,
                logger,
                error_logger,
                fetch_html=fake_html_fetching_round_2,
            )

        html_path_2 = tmp_paths_dict["output_dir"] / "product_2.html"

        assert html_path.read_text() == 'html_content' # this checks that the result from the first turn was not overwritten
        assert html_path_2.exists()
        assert html_path_2.read_text() == 'html_content_2'

    finally:
        pass
