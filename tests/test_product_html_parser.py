import logging
import sqlite3
import pytest

from pathlib import Path
from unittest.mock import patch

from utilities.database import Database
from utilities.utils import write_html

from crawler.crawler_product_html_parser import (
    run_crawler_product_html_parser,
    create_folder_with_date_of_parse_in_output_dir,
)
logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")


class FakeSiteConfig:
    def __init__(self, selector_to_start_process: str) -> None:
        self.selector_to_start_process: str = selector_to_start_process
        self.count = 1

    def individual_product_data_extraction(self, soup):
        test_product = {
            'link': 'product_1.com',
            'slug': 'product_1_com',
            'currency': '$',
            'price': 5,
            'product_code': 'TEST_CODE',
            'reviews': 'review',
            'images': ['image.com'],
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
        'price': 5,
        'product_code': 'TEST_CODE',
        'reviews': 'review',
        'images': ['image.com'],
    }
    return test_product


@pytest.fixture
def products_for_testing() -> list[dict]:
    test_product = {
        'link': 'product_1.com',
        'slug': 'product_1_com',
        'currency': '$',
        'price': 5,
        'product_code': 'TEST_CODE',
        'reviews': 'review',
        'images': ['image.com'],
    }
    test_product_2 = {
        'link': 'product_2.com',
        'slug': 'product_2_com',
        'currency': '$',
        'price': 5,
        'product_code': 'TEST_CODE',
        'reviews': 'review',
        'images': ['image.com'],
    }
    test_products = [test_product, test_product_2]

    return test_products


@pytest.fixture
def date_for_testing():
    date_for_testing = "22.5.1997"
    return date_for_testing


@pytest.fixture
def tmp_output_dir(tmp_path):
    directory = tmp_path / 'data_dir' / 'output_dir'
    directory.mkdir(parents=True, exist_ok=True)
    path_dict = {'output_dir': directory}

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


def test_run_crawler_product_html_parser(tmp_db, tmp_output_dir, product_for_testing):
    filename = 'product_1.html'
    html = 'html_content'

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])
    write_html(html_path, filename, html)

    run_crawler_product_html_parser(
        tmp_db,
        fake_site_config,
        tmp_output_dir,
        logger,
        error_logger,
    )

    assert html_path.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT product_name, parse_status FROM ProductPages WHERE product_url = ?',
            (product_for_testing['link'],),
        )
        row = cur.fetchone()

        assert row == ('product_1_com', 'parsed_succeeded')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_failed_archiving_does_not_invalidate_successful_state_of_parsing_of_a_product(
    tmp_db,
    tmp_output_dir,
    product_for_testing,
):
    filename = 'product_1.html'
    html = 'html_content'

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    file_path_of_archived_html = create_folder_with_date_of_parse_in_output_dir(tmp_output_dir)
    file_path_of_archived_html = file_path_of_archived_html / filename

    write_html(html_path, filename, html)

    with patch.object(Path, "rename") as patched_rename:
        patched_rename.side_effect = OSError("archive failed")

        run_crawler_product_html_parser(
            tmp_db,
            fake_site_config,
            tmp_output_dir,
            logger,
            error_logger,
        )

    assert not file_path_of_archived_html.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT product_name, parse_status FROM ProductPages WHERE product_url = ?',
            (product_for_testing['link'],),
        )
        row = cur.fetchone()

        assert row == ('product_1_com', 'parsed_succeeded')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_failed_archiving_does_not_impede_loop_from_continuing(
    tmp_db,
    tmp_output_dir,
    products_for_testing,
):
    filename = 'product_1.html'
    filename_2 = 'product_2.html'

    html_content = 'html_content'
    html_content_2 = 'html_content_2'

    tmp_db.insert_product_url(products_for_testing[0])
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')

    tmp_db.insert_product_url(products_for_testing[1])
    tmp_db.update_fetch_status_in_product_pages(2, filename_2, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])

    file_path_of_archived_html = create_folder_with_date_of_parse_in_output_dir(tmp_output_dir)
    file_path_of_archived_html = file_path_of_archived_html / filename

    write_html(html_path, filename, html_content)
    write_html(html_path, filename_2, html_content_2)

    class FakeSiteConfig:
        def __init__(self, selector_to_start_process: str) -> None:
            self.selector_to_start_process: str = selector_to_start_process
            self.count = 1

        def individual_product_data_extraction(self, soup):
            test_product = {
                'link': 'product_1.com',
                'slug': 'product_1_com',
                'currency': '$',
                'price': 5,
                'product_code': 'TEST_CODE',
                'reviews': 'review',
                'images': ['image.com'],
            }

            test_product_2 = {
                'link': 'product_2.com',
                'slug': 'product_2_com',
                'currency': '$',
                'price': 5,
                'product_code': 'TEST_CODE',
                'reviews': 'review',
                'images': ['image.com'],
            }

            if self.count == 1:
                self.count += 1
                return test_product
            elif self.count == 2:
                return test_product_2

    fake_site_config_for_this_test = FakeSiteConfig('dummy_selector')

    with patch.object(Path, "rename") as patched_rename:
        patched_rename.side_effect = [
            OSError("archive failed"),
            None,
        ]

        run_crawler_product_html_parser(
            tmp_db,
            fake_site_config_for_this_test,
            tmp_output_dir,
            logger,
            error_logger,
        )

    assert not file_path_of_archived_html.exists()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT product_name, parse_status FROM ProductPages WHERE product_url = ?',
            ('product_1.com',),
        )
        row_1 = cur.fetchone()

        cur.execute(
            'SELECT product_name, parse_status FROM ProductPages WHERE product_url = ?',
            ('product_2.com',),
        )
        row_2 = cur.fetchone()

        assert row_1 == ('product_1_com', 'parsed_succeeded')
        assert row_2 == ('product_2_com', 'parsed_succeeded')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_database_transaction_rollback_when_product_update_succeeds_but_update_status_fails(
    tmp_db,
    tmp_output_dir,
    product_for_testing,
):
    """
    product row starts:
    product fields = old/empty values
    parse_status = parsing

    update_product_data(...)                 ✓
    update_parse_status("parsed_succeeded")  ✗
    ROLLBACK

    recovery:
    update_parse_status("parsing_failed")    ✓
    COMMIT
    """

    filename = 'product_1.html'
    html_content = 'html_content'

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')

    html_path = Path(tmp_output_dir['output_dir'])
    write_html(html_path, filename, html_content)

    fake_site_config_for_this_test = FakeSiteConfig('dummy_selector')

    original_update_parse_status = tmp_db.update_parse_status

    def fake_update_product_parse_status(row_id, status):
        if status == 'parsed_succeeded':
            raise Exception()
        return original_update_parse_status(row_id, status)

    with patch("utilities.database.Database.update_parse_status") as mock:
        mock.side_effect = fake_update_product_parse_status

        run_crawler_product_html_parser(
            tmp_db,
            fake_site_config_for_this_test,
            tmp_output_dir,
            logger,
            error_logger,
        )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT product_name, parse_status FROM ProductPages WHERE product_url = ?',
            ('product_1.com',),
        )
        row = cur.fetchone()

        assert row == (None, 'parsing_failed')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_parser_recovery_logic_for_fetched_and_parsing_product_pages(
    tmp_db,
    product_for_testing,
):
    filename = 'product_1.html'

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')
    tmp_db.update_parse_status(1, 'parsing')

    tmp_db.reset_stuck_parsing_jobs()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status, parse_status FROM ProductPages WHERE product_url = ?',
            ('product_1.com',),
        )
        row = cur.fetchone()

        assert row == ('fetched', None)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_parser_state_management_for_fetched_and_parsed_suceeded_product_pages(
    tmp_db,
    product_for_testing,
):
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

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')
    tmp_db.update_parse_status(1, 'parsed_succeeded')

    tmp_db.get_fetched_product()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            '''
            SELECT product_name, fetch_status, parse_status
            FROM ProductPages
            WHERE product_url = ?
            ''',
            ('product_1.com',),
        )
        row = cur.fetchone()

        assert row == (None, 'fetched', 'parsed_succeeded')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_parser_state_management_for_fetched_and_unparsed_product_pages(
    tmp_db,
    product_for_testing,
):
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

    tmp_db.insert_product_url(product_for_testing)
    tmp_db.update_fetch_status_in_product_pages(1, filename, status='fetched')

    product = tmp_db.get_fetched_product()

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            'SELECT fetch_status, parse_status FROM ProductPages WHERE product_url = ?',
            ('product_1.com',),
        )
        row = cur.fetchone()

        assert product == (1, 'product_1.com', None, 'product_1.html')
        assert row == ('fetched', 'parsing')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
