import logging
import pytest

from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock
from playwright.sync_api import Page

from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll
from crawler.crawler_search_scraper import get_pending_url_and_update, run_crawler_search_scraper, reset_stuck_fetch_jobs, scrape_urls
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

class FakeSiteConfig:
    def __init__(self, products : list[dict[str, str]], selector_to_start_process : str) -> None:
        self.products = products
        self.selector_to_start_process : str = selector_to_start_process

    def product_extraction(self, soup):
        return self.products

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
def date_for_testing():
    date_for_testing = "22.5.1997"
    return date_for_testing

@pytest.fixture
def tmp_data_dir(tmp_path):

    data_dir = tmp_path / 'data_dir'
    data_dir.mkdir(parents= True, exist_ok=True)
    path_dict = {'data_dir': data_dir}

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

def test_get_pending_url_and_update(tmp_db):

    test_url = 'www.mardelplata.com'

    insert_url(test_url, tmp_db, date='5.2.22')

    update_url_status(test_url, tmp_db, status='pending')

    returned_id, returned_url = get_pending_url_and_update(tmp_db)

    tmp_db["cur"].execute('SELECT id, url_name FROM Urls WHERE status = ?', ('in_progress', ) )

    url_and_id = tmp_db["cur"].fetchone()

    assert test_url == returned_url
    assert url_and_id == (returned_id, test_url)


def update_filename_for_url(url: str, db: dict, filename: str):
    """Insert filename for crawled URL."""
    db["cur"].execute('SELECT filename FROM Urls WHERE url_name=?', (url,))
    row = db["cur"].fetchone()
    if row[0] is None:
        db["cur"].execute('UPDATE Urls SET filename = ? WHERE url_name = ?', (filename, url))
    db["conn"].commit()

def test_update_filename_for_url(tmp_db):

    test_url = "www.mdp.com"
    filename = "page_1.html"

    insert_url(test_url, tmp_db, date='1.1.1')

    update_filename_for_url(test_url, tmp_db, filename)

    tmp_db["cur"].execute("SELECT url_name, filename from Urls where url_name = ? LIMIT 1", (test_url,))

    result = tmp_db["cur"].fetchall()

    assert result[0] == ("www.mdp.com", "page_1.html")

def test_update_filename_for_url_filename_already_exists(tmp_db):
    """
    If the URL already has a filename:
        preserve the existing filename.
    """
    test_url = "www.mdp.com"
    filename = "page_1.html"

    insert_url(test_url, tmp_db, date='1.1.1')

    tmp_db["cur"].execute("UPDATE Urls SET filename = ? where url_name = ?", (filename, test_url))

    update_filename_for_url(test_url, tmp_db, filename="test.html")

    tmp_db["cur"].execute("SELECT url_name, filename from Urls where url_name = ? LIMIT 1", (test_url,))

    result = tmp_db["cur"].fetchall()

    assert result[0] == ("www.mdp.com", "page_1.html")

def test_stuck_fetch_jobs_resets_jobs(tmp_db, url_for_testing,date_for_testing):

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='in_progress')

    reset_stuck_fetch_jobs(tmp_db)

    tmp_db["cur"].execute('SELECT url_name, status from Urls where url_name = ?', (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result == (url_for_testing, 'pending')

def test_stuck_fetch_jobs_there_are_no_in_progress_jobs(tmp_db, url_for_testing,date_for_testing):

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='fetched')

    reset_stuck_fetch_jobs(tmp_db)

    tmp_db["cur"].execute('SELECT url_name, status from Urls where url_name = ?', (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result == (url_for_testing, 'fetched')


def test_scrape_urls_with_playwright(tmp_db, url_for_testing,date_for_testing, tmp_data_dir):

    """
    Responsibility: 
    
    / 1. reset stuck fetched pages.
    2. open up a playwright session with the stealth context on.
    3. fetch all the urls (along with their ids) and mark them as in pending.
    4. process each url.
    5. if an html is elegible according to the selectors passed by the specific_site_config, donwload the html with 'page_url_id' filename.
    6. update the filename of the url to that filename and its status to fetched.

    Contract:

    Dependencies:

    Evidence that the contract was fulfilled:

    """

    return

    fake_config = FakeSiteConfig(products=[{'test' : 'test'}], selector_to_start_process='"p.price_color"' )

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='in_progress')

    run_crawler_search_scraper(
    tmp_db, 
    fake_config,
    logger,
    error_logger,
    tmp_data_dir)

    tmp_db["cur"].execute('SELECT url_name, status from Urls where url_name = ?', (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result == (url_for_testing, 'pending')

def test_scrape_urls_success_path(tmp_db, tmp_data_dir, url_for_testing, date_for_testing):

    """
    Tests whether scrape_urls succesfully handles the correct output of its functions.
    HTML returned:
    → file written
    → filename stored
    → status = fetched
    """

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='pending')

    fake_config = FakeSiteConfig(products=[{'test' : 'test'}], selector_to_start_process="p.price_color")

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        fake_html = '<p class="price_color">test</p>'
        return fake_html

    scrape_urls(tmp_db, tmp_data_dir, fake_page, fake_config, logger, error_logger, fetch_html=fake_fetch_html)

    with open(tmp_data_dir['data_dir'] / 'page_1.html', 'r', encoding='utf-8') as file:
        html = file.read()

    # file contains expected HTML
    assert html == '<p class="price_color">test</p>'

    #DB filename in DB is page_1.html
    tmp_db["cur"].execute("SELECT filename from Urls where url_name= ? LIMIT 1", (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result[0] == "page_1.html"

    #DB status is fetched
    tmp_db["cur"].execute("SELECT status from Urls where url_name= ? LIMIT 1", (url_for_testing,))
    result = tmp_db["cur"].fetchone()
    assert result[0] == "fetched"

def test_scrape_urls_failure_path(tmp_db, tmp_data_dir, url_for_testing, date_for_testing):

    """
    # file was not written
    # DB filename remains None
    # DB status is failed
    """

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='pending')

    fake_config = FakeSiteConfig(products=[{'test' : 'test'}], selector_to_start_process="p.price_color")

    def fake_fetch_html_failure(page, url, logger, selector_to_start_process)-> None: 
        return None

    scrape_urls(tmp_db, tmp_data_dir, fake_page, fake_config, logger, error_logger, fetch_html=fake_fetch_html_failure)

    html_path = tmp_data_dir["data_dir"] / "page_1.html"

    # file path does NOT exist
    assert not html_path.exists()

    #DB filename in DB is None
    tmp_db["cur"].execute("SELECT filename from Urls where url_name= ? LIMIT 1", (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result[0] is None

    #DB status is failed
    tmp_db["cur"].execute("SELECT status from Urls where url_name= ? LIMIT 1", (url_for_testing,))
    result = tmp_db["cur"].fetchone()
    assert result[0] == "failed"

def test_scrape_urls_two_successes(tmp_db, tmp_data_dir, url_for_testing, date_for_testing):

    """
    Tests whether the loop of scrape_urls succesfully handles the correct output of its functions with two urls.
    HTML returned:
    → file written
    → filename stored
    → status = fetched
    """

    url_2 = 'www.sea.com'

    insert_url(url_for_testing, tmp_db, date_for_testing)

    insert_url(url_2, tmp_db, date_for_testing)

    update_url_status(url_for_testing, tmp_db, status='pending')

    update_url_status(url_2, tmp_db, status='pending')

    fake_config = FakeSiteConfig(products=[{'test' : 'test'}], selector_to_start_process="p.price_color")

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        fake_html = ''
        if url == url_for_testing:
            fake_html = '<p class="price_color">test</p>'
        if url == url_2:
            fake_html = '<p class="sea">test>/p>'
        return fake_html

    scrape_urls(tmp_db, tmp_data_dir, fake_page, fake_config, logger, error_logger, fetch_html=fake_fetch_html)

    with open(tmp_data_dir['data_dir'] / 'page_1.html', 'r', encoding='utf-8') as file:
        html = file.read()

    with open(tmp_data_dir['data_dir'] / 'page_2.html', 'r', encoding='utf-8') as file:
        html_2 = file.read()
    
    # file contains expected HTML
    assert html == '<p class="price_color">test</p>'
    assert html_2 == '<p class="sea">test>/p>'

    #DB filename in DB is page_1.html
    tmp_db["cur"].execute("SELECT filename from Urls where url_name= ? LIMIT 1", (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result[0] == "page_1.html"

    #DB filename in DB is page_1.html
    tmp_db["cur"].execute("SELECT filename from Urls where url_name= ? LIMIT 1", (url_2,))

    result = tmp_db["cur"].fetchone()

    assert result[0] == "page_2.html"

    #DB status is fetched

    tmp_db["cur"].execute("SELECT status from Urls where url_name= ? LIMIT 1", (url_for_testing,))

    result = tmp_db["cur"].fetchone()

    assert result[0] == "fetched"

    tmp_db["cur"].execute("SELECT status from Urls where url_name= ? LIMIT 1", (url_2,))

    result = tmp_db["cur"].fetchone()

    assert result[0] == "fetched"

def test_scrape_urls_one_failure_one_success(
    tmp_db,
    tmp_data_dir,
    url_for_testing,
    date_for_testing
):

    """
    Tests whether scrape_urls continues processing pending URLs after one URL fails.

    First URL:
    → HTML retrieval fails
    → no file is written
    → filename remains None
    → status becomes failed

    Second URL:
    → HTML is returned
    → file is written
    → filename is stored
    → status becomes fetched
    """

    url_2 = 'www.sea.com'

    insert_url(url_2, tmp_db, date_for_testing)

    insert_url(url_for_testing, tmp_db, date_for_testing)

    update_url_status(url_2, tmp_db, status='pending')

    update_url_status(url_for_testing, tmp_db, status='pending')

    fake_config = FakeSiteConfig(
        products=[{'test': 'test'}],
        selector_to_start_process="p.price_color"
    )

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        if url == url_for_testing:
            fake_html = '<p class="price_color">test</p>'
            return fake_html
        if url == url_2:
            return None

    scrape_urls(
        tmp_db,
        tmp_data_dir,
        fake_page,
        fake_config,
        logger,
        error_logger,
        fetch_html=fake_fetch_html
    )

    failed_html_file_path = tmp_data_dir['data_dir'] / 'page_1.html'

    with open(
        tmp_data_dir['data_dir'] / 'page_2.html',
        'r',
        encoding='utf-8'
    ) as file:
        html = file.read()

    # The failed first URL does not produce an HTML file.
    assert not failed_html_file_path.exists()

    # The successful second URL produces the expected HTML file.
    assert html == '<p class="price_color">test</p>'

    # The failed first URL has no filename stored.
    tmp_db["cur"].execute(
        "SELECT filename FROM Urls WHERE url_name = ? LIMIT 1",
        (url_2,)
    )

    result = tmp_db["cur"].fetchone()

    assert result[0] is None

    # The successful second URL has its filename stored.
    tmp_db["cur"].execute(
        "SELECT filename FROM Urls WHERE url_name = ? LIMIT 1",
        (url_for_testing,)
    )

    result = tmp_db["cur"].fetchone()

    assert result[0] == "page_2.html"

    # The failed first URL is marked as failed.
    tmp_db["cur"].execute(
        "SELECT status FROM Urls WHERE url_name = ? LIMIT 1",
        (url_2,)
    )

    result = tmp_db["cur"].fetchone()

    assert result[0] == "failed"

    # The successful second URL is marked as fetched.
    tmp_db["cur"].execute(
        "SELECT status FROM Urls WHERE url_name = ? LIMIT 1",
        (url_for_testing,)
    )

    result = tmp_db["cur"].fetchone()

    assert result[0] == "fetched"


def test_process_single_url_happy_html_path(url_for_testing):

    def fake_load_page(page, url, wait_selector, max_attempts=2):
        return True
    
    def fake_perform_scroll(page, url):
        return True

    def fake_extract_html(page, url):
        html = "dummy_content"
        return html

    test_html = "dummy_content"
    
    with patch("utilities.utils.time.sleep"):
        html = process_single_url(
            fake_page,
            url_for_testing,
            logger,
            wait_selector="dummy_wait_selector",
            page_loading=fake_load_page,
            perform_scrolling=fake_perform_scroll,
            html_extracting=fake_extract_html,
        )

    assert html == test_html

def test_process_single_url_load_page_fails(url_for_testing):

    def fake_load_page(page, url, wait_selector, max_attempts=2):
        return False
    
    def fake_perform_scroll(page, url):
        return True

    def fake_extract_html(page, url):
        html = "dummy_content"
        return html

    with patch("utilities.utils.time.sleep"):
        html = process_single_url(
            fake_page,
            url_for_testing,
            logger,
            wait_selector="dummy_wait_selector",
            page_loading=fake_load_page,
            perform_scrolling=fake_perform_scroll,
            html_extracting=fake_extract_html,
        )

    assert html is None

def test_process_single_url_perform_scroll_fails(url_for_testing):

    def fake_load_page(page, url, wait_selector, max_attempts=2):
        return True
    
    def fake_perform_scroll(page, url):
        return False

    def fake_extract_html(page, url):
        html = "dummy_content"
        return html
    
    with patch("utilities.utils.time.sleep"):
        html = process_single_url(
            fake_page,
            url_for_testing,
            logger,
            wait_selector="dummy_wait_selector",
            page_loading=fake_load_page,
            perform_scrolling=fake_perform_scroll,
            html_extracting=fake_extract_html,
        )

    assert html is None

def test_process_single_url_html_extraction_fails(url_for_testing):

    def fake_load_page(page, url, wait_selector, max_attempts=2):
        return True
    
    def fake_perform_scroll(page, url):
        return True

    def fake_extract_html(page, url):
        return None
    
    with patch("utilities.utils.time.sleep"):
        html = process_single_url(
            fake_page,
            url_for_testing,
            logger,
            wait_selector="dummy_wait_selector",
            page_loading=fake_load_page,
            perform_scrolling=fake_perform_scroll,
            html_extracting=fake_extract_html,
        )

    assert html is None

###############################################

def test_load_page_happy_path(url_for_testing):

    fake_page = FakePage()

    result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert result is True

def test_load_page_reload_on_first_retry(url_for_testing):

    class FakePage:
        def __init__(self) -> None:
            pass
        def goto(self, url, timeout=0):
            raise Exception
        def reload(self, timeout=0):
            pass
        def wait_for_selector(self, wait_selector, timeout=0):
            pass

    fake_page = FakePage()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert result is True

def test_load_page_returns_false_when_selector_always_fails(url_for_testing):

    class FakePage:
        def goto(self, url, timeout=0):
            pass
        def reload(self, timeout=0):
            pass
        def wait_for_selector(self, wait_selector, timeout=0):
            raise Exception

    fake_page = FakePage()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert result is False

def test_load_page_returns_true_when_selector_succeeds_on_first_retry(url_for_testing):

    """
    first selector call fails
    second selector call succeeds
    → load_page returns True
    """

    class FakePage:
        def __init__(self) -> None:
            self.wait_for_selector_count = 0
        def goto(self, url, timeout=0):
            pass
        def reload(self, timeout=0):
            pass
        def wait_for_selector(self, wait_selector, timeout=0):
            self.wait_for_selector_count += 1
            if (self.wait_for_selector_count == 1):
                raise Exception
            else:
                pass

    fake_page = FakePage()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert result is True

def test_load_page_unhappy_path(url_for_testing):
    class FakePage:
            def goto(self, url, timeout=0):
                raise Exception
            def reload(self, timeout=0):
                raise Exception
            def wait_for_selector(self, wait_selector, timeout=0):
                raise Exception
    
    fake_page = FakePage()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert result is False

def test_load_page_does_not_call_reload_in_happy_path(url_for_testing):

    fake_page = Mock()

    result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_not_called()

    assert result is True


def test_load_page_calls_reload_in_retry_happy_path(url_for_testing):

    fake_page = Mock()

    result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_not_called()

    assert result is True

def test_load_page_reload_on_first_retry_manual_version(url_for_testing):

    class FakePage:
        def __init__(self) -> None:
            self.goto_calls = 0
            self.reload_calls = 0
        def goto(self, url, timeout=0):
            self.goto_calls += 1
            raise Exception
        def reload(self, timeout=0):
            self.reload_calls += 1
            pass
        def wait_for_selector(self, wait_selector, timeout=0):
            pass

    fake_page = FakePage()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    assert fake_page.goto_calls == 1
    assert fake_page.reload_calls == 1
    assert result is True

def test_load_page_reload_on_first_retry_mock_version(url_for_testing):

    fake_page = Mock()

    fake_page.goto.side_effect = Exception()

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_called_once()
    fake_page.wait_for_selector.assert_called_once()

    assert result is True

def test_load_page_selector_loads_on_first_retry(url_for_testing):

    """
    Test path:     
    goto succeeds
    wait_for_selector fails once
    reload succeeds
    wait_for_selector succeeds
    → returns True
    """

    fake_page = Mock()

    fake_page.wait_for_selector.side_effect = [
    Exception(), 
    True
    ]

    with patch("utilities.utils.time.sleep"):
        result = load_page(fake_page, url_for_testing, 'dummy_wait_selector')

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_called_once()

    assert fake_page.wait_for_selector.call_count == 2
    assert result is True

def test_successful_html_retrieval_with_mock(url_for_testing):

    fake_page = Mock()

    fake_page.content.return_value = "<html>test</html>"

    result = extract_html(fake_page, url_for_testing)

    fake_page.content.assert_called_once()

    assert result == "<html>test</html>"

def test_unsuccessful_html_retrieval_with_mock(url_for_testing):

    fake_page = Mock()

    fake_page.content.side_effect = Exception()

    result = extract_html(fake_page, url_for_testing)

    fake_page.content.assert_called_once()

    assert result is None

def test_perform_scroll_happy_path(url_for_testing):

    fake_page = Mock()

    with patch("utilities.utils.human_scroll") as mock_human_scroll:
        result = perform_scroll(fake_page, url_for_testing)

    mock_human_scroll.assert_called_once()
    assert result is True

def test_perform_scroll_failed_path(url_for_testing):

    fake_page = Mock()

    with patch("utilities.utils.human_scroll") as mock_human_scroll:
        mock_human_scroll.side_effect = Exception()
        result = perform_scroll(fake_page, url_for_testing)

    mock_human_scroll.assert_called_once()

    assert result is False

def test_perform_scroll_returns_false_on_playwright_timeout(url_for_testing):

    fake_page = Mock()

    with patch("utilities.utils.human_scroll") as mock_human_scroll:
        mock_human_scroll.side_effect = PlaywrightTimeoutError("Timeout")
        result = perform_scroll(fake_page, url_for_testing)

    mock_human_scroll.assert_called_once()

    assert result is False


    






