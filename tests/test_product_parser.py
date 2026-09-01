import pytest
from bs4 import BeautifulSoup
from utilities.specific_sites import BooksToScrape
from urllib.parse import urljoin
from pathlib import Path

TESTS_DIR = Path(__file__).parent

@pytest.fixture
def test_product_html() -> str:
    with open(TESTS_DIR / 'test_book.html', 'r', encoding='utf-8') as file:
        html = file.read()
    return html

@pytest.fixture
def test_search_html() -> str:
    with open(TESTS_DIR / 'test_page.html', 'r', encoding='utf-8') as file:
        html = file.read()
    return html


def test_individual_product_data_extraction_dictionary_BooksToScrape(test_product_html):

    soup = BeautifulSoup(test_product_html, "html.parser")

    product = BooksToScrape().individual_product_data_extraction(soup)

    assert product == ({
            "name": "A Light in the Attic",
            "slug": "a_light_in_the_attic",
            "price": "51.77",
            "currency": "£",
            "product_code": "a897fe39b1053632",
            "product_url" : None,
            "reviews" : None,
            "images": [None]
        })

def test_search_results_product_parser(test_search_html):

    soup = BeautifulSoup(test_search_html, "html.parser")

    product_card = BooksToScrape().product_extraction(soup)

    assert product_card == [{'link' : urljoin(BooksToScrape().base_url, "a-light-in-the-attic_1000/index.html")}]

    



