import logging
import pytest

from utilities.database import db_initialization, db_cur_and_conn_closer
from utilities.utils import slugify

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
    return "www.mdp.com"

@pytest.fixture
def date_for_testing():
    return "22.5.1997"

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

@pytest.fixture
def loggers_for_testing():
    logger = logging.getLogger("test_logger")
    error_logger = logging.getLogger("test_error_logger")
    return [logger, error_logger]

@pytest.mark.parametrize(
    ('input_text', 'expected'),
    [
        (' www.mdp.com ', 'www_mdp_com'), 
        (' www.#mdp.com ', 'www_mdp_com'),
        ('www.árabesco.com', 'www_arabesco_com')
    ]
)

def test_slugify(input_text, expected):
    result = slugify(input_text)
    assert result == expected



