import logging
import pytest
import sqlite3

from utilities.database import Database

from crawler.crawler_search_html_parser import crawler_search_html_parser

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

class FakeSiteConfig:
    def __init__(self, products : list[dict[str, str]]) -> None:
        self.products = products

    def product_extraction(self, soup):
        return self.products

@pytest.fixture
def temp_data_dir(tmp_path):

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

####################################
#TESTS
####################################

def test_url_insertion_from_scraped_html_file(temp_data_dir, tmp_db):

    product_html = """
    <article>
    <mock so that test has a valid file
    </article>
    """

    file_path = temp_data_dir['data_dir'] / 'page_1.html'
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(product_html)
        
    list_of_html_files = [file_path]

    fake_config = FakeSiteConfig([{'link': 'book1.html' }])

    crawler_search_html_parser(
    list_of_html_files,
    temp_data_dir,
    fake_config,
    tmp_db ,
    logger,
    error_logger)

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute('SELECT product_url, fetch_status from ProductPages LIMIT 1')

        url_in_db = cur.fetchall()

        assert url_in_db[0] == ('book1.html', 'pending')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_two_urls_insertions_from_scraped_html_file(temp_data_dir, tmp_db):

    product_html = """
    <article>
    <mock so the test has a valid file
    </article>
    """

    file_path = temp_data_dir['data_dir'] / 'page_1.html'
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(product_html)
        
    list_of_html_files = [file_path]
    fake_config = FakeSiteConfig(
    [{'link': 'book1.html'}, {'link': 'book2.html'}])

    conn, cur = None, None

    crawler_search_html_parser(
    list_of_html_files,
    temp_data_dir,
    fake_config,
    tmp_db ,
    logger,
    error_logger)

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute('SELECT product_url, fetch_status from ProductPages ORDER BY product_url')

        urls_in_db = cur.fetchall()

        assert urls_in_db == [('book1.html', 'pending'),
                            ('book2.html', 'pending')]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()



