import logging
import pytest
import sqlite3

from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock
from playwright.sync_api import Page

#from utilities.database import db_initialization, db_cur_and_conn_closer, insert_url, update_url_status
from utilities.database import Database
from utilities.utils import process_single_url, load_page, extract_html, perform_scroll, human_scroll
from crawler.crawler_search_scraper import run_crawler_search_scraper, scrape_urls
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
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()


def test_get_pending_url_and_update(tmp_db):

    test_url = "www.mardelplata.com"

    tmp_db.insert_url(test_url, date="5.2.22")
    tmp_db.update_url_status(test_url, status="pending")

    returned_id, returned_url = tmp_db.get_pending_url_and_update()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, url_name FROM Urls WHERE status = ?",
            ("in_progress",),
        )

        url_and_id = cur.fetchone()

        assert test_url == returned_url
        assert url_and_id == (returned_id, test_url)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_update_filename_for_url(tmp_db):

    test_url = "www.mdp.com"
    filename = "page_1.html"

    tmp_db.insert_url(test_url, date="1.1.1")
    tmp_db.update_filename_for_url(test_url, filename)

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "SELECT url_name, filename FROM Urls WHERE url_name = ? LIMIT 1",
            (test_url,),
        )

        result = cur.fetchone()

        assert result == ("www.mdp.com", "page_1.html")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_update_filename_for_url_filename_already_exists(tmp_db):

    """
    If the URL already has a filename:
        preserve the existing filename.
    """

    test_url = "www.mdp.com"
    filename = "page_1.html"

    tmp_db.insert_url(test_url, date="1.1.1")

    # First filename is stored.
    tmp_db.update_filename_for_url(test_url, filename)

    # This should not overwrite it.
    tmp_db.update_filename_for_url(test_url, filename="test.html")

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "SELECT url_name, filename FROM Urls WHERE url_name = ? LIMIT 1",
            (test_url,),
        )

        result = cur.fetchone()

        assert result == ("www.mdp.com", "page_1.html")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_stuck_fetch_jobs_resets_jobs(
    tmp_db,
    url_for_testing,
    date_for_testing,
):

    tmp_db.insert_url(url_for_testing, date_for_testing)
    tmp_db.update_url_status(url_for_testing, status="in_progress")

    tmp_db.reset_stuck_jobs_in_urls_table()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "SELECT url_name, status FROM Urls WHERE url_name = ?",
            (url_for_testing,),
        )

        result = cur.fetchone()

        assert result == (url_for_testing, "pending")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_stuck_fetch_jobs_there_are_no_in_progress_jobs(
    tmp_db,
    url_for_testing,
    date_for_testing,
):

    tmp_db.insert_url(url_for_testing, date_for_testing)
    tmp_db.update_url_status(url_for_testing, status="fetched")

    tmp_db.reset_stuck_jobs()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "SELECT url_name, status FROM Urls WHERE url_name = ?",
            (url_for_testing,),
        )

        result = cur.fetchone()

        assert result == (url_for_testing, "fetched")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_scrape_urls_success_path(
    tmp_db,
    tmp_data_dir,
    url_for_testing,
    date_for_testing,
):

    """
    Tests whether scrape_urls successfully handles the correct output
    of its functions.

    HTML returned:
    → file written
    → filename stored
    → status = fetched
    """

    tmp_db.insert_url(url_for_testing, date_for_testing)
    tmp_db.update_url_status(url_for_testing, status="pending")

    fake_config = FakeSiteConfig(
        products=[{"test": "test"}],
        selector_to_start_process="p.price_color",
    )

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        return '<p class="price_color">test</p>'

    scrape_urls(
        tmp_db,
        tmp_data_dir,
        fake_page,
        fake_config,
        logger,
        error_logger,
        fetch_html=fake_fetch_html,
    )

    with open(
        tmp_data_dir["data_dir"] / "page_1.html",
        "r",
        encoding="utf-8",
    ) as file:
        html = file.read()

    assert html == '<p class="price_color">test</p>'

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT filename, status
            FROM Urls
            WHERE url_name = ?
            LIMIT 1
            """,
            (url_for_testing,),
        )

        result = cur.fetchone()

        assert result == ("page_1.html", "fetched")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_scrape_urls_failure_path(
    tmp_db,
    tmp_data_dir,
    url_for_testing,
    date_for_testing,
):

    """
    HTML retrieval fails:
    → file is not written
    → filename remains None
    → status = failed
    """

    tmp_db.insert_url(url_for_testing, date_for_testing)
    tmp_db.update_url_status(url_for_testing, status="pending")

    fake_config = FakeSiteConfig(
        products=[{"test": "test"}],
        selector_to_start_process="p.price_color",
    )

    def fake_fetch_html_failure(
        page,
        url,
        logger,
        selector_to_start_process,
    ):
        return None

    scrape_urls(
        tmp_db,
        tmp_data_dir,
        fake_page,
        fake_config,
        logger,
        error_logger,
        fetch_html=fake_fetch_html_failure,
    )

    html_path = tmp_data_dir["data_dir"] / "page_1.html"

    assert not html_path.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT filename, status
            FROM Urls
            WHERE url_name = ?
            LIMIT 1
            """,
            (url_for_testing,),
        )

        result = cur.fetchone()

        assert result == (None, "failed")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_scrape_urls_two_successes(
    tmp_db,
    tmp_data_dir,
    url_for_testing,
    date_for_testing,
):

    """
    Tests whether scrape_urls successfully handles two URLs.

    Both:
    → HTML returned
    → file written
    → filename stored
    → status = fetched
    """

    url_2 = "www.sea.com"

    tmp_db.insert_url(url_for_testing, date_for_testing)
    tmp_db.insert_url(url_2, date_for_testing)

    tmp_db.update_url_status(url_for_testing, status="pending")
    tmp_db.update_url_status(url_2, status="pending")

    fake_config = FakeSiteConfig(
        products=[{"test": "test"}],
        selector_to_start_process="p.price_color",
    )

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        if url == url_for_testing:
            return '<p class="price_color">test</p>'

        if url == url_2:
            return '<p class="sea">test>/p>'

    scrape_urls(
        tmp_db,
        tmp_data_dir,
        fake_page,
        fake_config,
        logger,
        error_logger,
        fetch_html=fake_fetch_html,
    )

    with open(
        tmp_data_dir["data_dir"] / "page_1.html",
        "r",
        encoding="utf-8",
    ) as file:
        html = file.read()

    with open(
        tmp_data_dir["data_dir"] / "page_2.html",
        "r",
        encoding="utf-8",
    ) as file:
        html_2 = file.read()

    assert html == '<p class="price_color">test</p>'
    assert html_2 == '<p class="sea">test>/p>'

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT url_name, filename, status
            FROM Urls
            ORDER BY id
            """
        )

        results = cur.fetchall()

        assert results == [
            (url_for_testing, "page_1.html", "fetched"),
            (url_2, "page_2.html", "fetched"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_scrape_urls_one_failure_one_success(
    tmp_db,
    tmp_data_dir,
    url_for_testing,
    date_for_testing,
):

    """
    Tests whether scrape_urls continues processing pending URLs
    after one URL fails.

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

    url_2 = "www.sea.com"

    tmp_db.insert_url(url_2, date_for_testing)
    tmp_db.insert_url(url_for_testing, date_for_testing)

    tmp_db.update_url_status(url_2, status="pending")
    tmp_db.update_url_status(url_for_testing, status="pending")

    fake_config = FakeSiteConfig(
        products=[{"test": "test"}],
        selector_to_start_process="p.price_color",
    )

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        if url == url_for_testing:
            return '<p class="price_color">test</p>'

        if url == url_2:
            return None

    scrape_urls(
        tmp_db,
        tmp_data_dir,
        fake_page,
        fake_config,
        logger,
        error_logger,
        fetch_html=fake_fetch_html,
    )

    failed_html_file_path = (
        tmp_data_dir["data_dir"] / "page_1.html"
    )

    with open(
        tmp_data_dir["data_dir"] / "page_2.html",
        "r",
        encoding="utf-8",
    ) as file:
        html = file.read()

    assert not failed_html_file_path.exists()
    assert html == '<p class="price_color">test</p>'

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT url_name, filename, status
            FROM Urls
            ORDER BY id
            """
        )

        results = cur.fetchall()

        assert results == [
            (url_2, None, "failed"),
            (url_for_testing, "page_2.html", "fetched"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


    






