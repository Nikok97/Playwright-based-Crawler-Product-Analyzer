import logging
import re
import pytest

from pathlib import Path
from logging import Logger
from bs4 import BeautifulSoup

from utilities.database import db_initialization, db_cur_and_conn_closer

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
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)

def list_of_html_files_compiler(directory: Path) -> list | None:
    page_pattern = re.compile(r"^page_(\d+)\.html$")
    html_files = []

    for path in directory.iterdir():
        if not path.is_file():
            continue

        match = page_pattern.match(path.name)
        if match:
            html_files.append(path.name)

    if not html_files:
        return None

    return sorted(
        html_files,
        key=lambda f: int(page_pattern.match(f).group(1))  # type: ignore
    )

def insert_product_url(db: dict, individual_product: dict, url_id: int, error_logger) -> bool:
    """Stores product information related to a product URL in the database.
    """
    try:
        db["cur"].execute('''
        INSERT OR IGNORE INTO ProductPages (product_url, fetch_status)
        VALUES ( ?, ?)
        ''', (individual_product["link"], "pending"))
        db["conn"].commit()
        return True
    except Exception as e:
        error_logger.error(f"Unknown DB error for {url_id}: {e}")
        return False
    
def crawler_search_html_parser(
    list_of_html_files: list,
    paths_dict: dict,
    specific_site_config ,
    db : dict,
    logger: Logger,
    error_logger: Logger
):

    #Main logic
    for file in list_of_html_files:
        
        try:

            file = Path(file)
            url_id = int(file.stem.split("_")[1])
            file_path = paths_dict['data_dir'] / file

            with open(file_path, "r", encoding="utf-8") as file:

                #2. Extract soup
                soup = BeautifulSoup(file, 'html.parser')

                #3. Extract product data from search results into a list of dict objects
                products_of_page = specific_site_config.product_extraction(soup)

                # DB Product insertion
                total_number_of_products_in_page = len(products_of_page)

                for idx, individual_product in enumerate(products_of_page, start=1):

                    if insert_product_url(db, individual_product, url_id, error_logger):
                        logger.info(
                            f"Inserted product {idx} of {total_number_of_products_in_page} for URL {url_id}")
                    else:
                        logger.info(
                            f"Failed to insert product {idx} of {total_number_of_products_in_page} for URL {url_id}")
                        
        except Exception:
            error_logger.error(f"Unhandled exception for {file}", exc_info=True)

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

    tmp_db['cur'].execute('SELECT product_url, fetch_status from ProductPages LIMIT 1')

    url_in_db = tmp_db['cur'].fetchall()

    assert url_in_db[0] == ('book1.html', 'pending')


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

    crawler_search_html_parser(
    list_of_html_files,
    temp_data_dir,
    fake_config,
    tmp_db ,
    logger,
    error_logger)

    tmp_db['cur'].execute('SELECT product_url, fetch_status from ProductPages ORDER BY product_url')

    urls_in_db = tmp_db['cur'].fetchall()

    assert urls_in_db == [('book1.html', 'pending'),
                        ('book2.html', 'pending')]



