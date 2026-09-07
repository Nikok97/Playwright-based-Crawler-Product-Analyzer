import pytest

from unittest.mock import patch, Mock, create_autospec
from playwright.sync_api import Page
from bs4 import BeautifulSoup
from pathlib import Path
from logging import Logger
from utilities.specific_sites import WebsiteToScrape, BooksToScrape, Amazon, MercadoLibre
from utilities.database import db_initialization, db_cur_and_conn_closer
from utilities.utils import process_single_url

@pytest.fixture
def url_for_testing():
    return 'www.url.com'

books_html = """<article class="product_pod">
        <a href="book1.html">Sapiens</a>
    </article>
    """

ml_html = """
    <li class="ui-search-layout__item">
        <a class="poly-component__title"SJ
           href="https://articulo.mercadolibre.com.ar/MLA-123">
            Sapiens
        </a>
    </li>
    """

amazon_html = """
    <div data-component-type="s-search-result">
    </div>
    """

@pytest.mark.parametrize(
    ("adapter_class", "test_html"),
    [
        (BooksToScrape, books_html),
        (MercadoLibre, ml_html),
        pytest.param(
            Amazon,
            amazon_html,
            marks=pytest.mark.xfail(
                reason="Amazon does not yet provide the product link contract"
            ),
        ),
    ],
)

def test_product_extraction_minimal_contract(adapter_class, test_html):

    adapter_to_test = adapter_class()

    html_2 = 'dummy_content'

    soup = BeautifulSoup(test_html, 'html.parser')
    soup_2 = BeautifulSoup(html_2, 'html.parser')

    result_with_products = adapter_to_test.product_extraction(soup)
    result_without_products = adapter_to_test.product_extraction(soup_2)

    assert isinstance(result_with_products, list)

    product = result_with_products[0]

    assert isinstance(product, dict)

    assert 'link' in product
    
    assert result_without_products is None


@pytest.mark.parametrize(
    ("adapter_classes_for_tests"),
    [
        (BooksToScrape),
        pytest.param(MercadoLibre, marks=pytest.mark.xfail(reason="MercadoLibre does not yet provide the required selector")),
        pytest.param(Amazon, marks=pytest.mark.xfail(reason="Amazon does not yet provide the required selector")),
    ],
)

def test_product_scraping_wait_selector_contract(url_for_testing, adapter_classes_for_tests):

    adapter_used = adapter_classes_for_tests()

    fake_page = create_autospec(Page)
    fake_logger = create_autospec(Logger)

    process_single_url(
        fake_page, 
        url_for_testing, 
        fake_logger, 
        adapter_used.wait_selector, 
    )

    assert hasattr(adapter_used, "wait_selector")

@pytest.mark.parametrize(
    ("adapter_classes_for_tests"),
    [
        (BooksToScrape),
        (MercadoLibre),
        pytest.param(Amazon, marks=pytest.mark.xfail(reason="Amazon does not yet provide the required selector")),
    ],
)

def test_individual_product_data_extraction_adapter_contract(adapter_classes_for_tests):

    adapter_used = adapter_classes_for_tests()

    assert hasattr(adapter_used, 'individual_product_data_extraction')


books_to_scrape_individual_product_html = """
""" 

ml_individual_product_html = """
"""


@pytest.mark.parametrize(
    ("adapter_class", "test_html"),
    [
        (BooksToScrape, books_to_scrape_individual_product_html),
        (MercadoLibre, ml_individual_product_html),
        pytest.param(
            Amazon,
            'placeholder_html_value',
            marks=pytest.mark.xfail(
                reason="Amazon does not presently support individual product extraction"
            ),
        ),
    ],
)

def test_individual_product_contract_for_adapters_that_support_individual_product_data_extraction(adapter_class, test_html):

    soup = BeautifulSoup(test_html, 'html.parser')

    adapter_used = adapter_class()

    result = adapter_used.individual_product_data_extraction(soup)

    assert isinstance(result, dict)
    assert "slug" in result
    assert "currency" in result
    assert "price" in result
    assert "product_code" in result
    assert "reviews" in result
    assert "images" in result
    assert len(result["images"]) > 0