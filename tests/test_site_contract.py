"""
Offline tests of the site adapter contract.

Every test in this module uses the concrete adapters of the registry, but none of them reaches a live website: HTML is read from the fixtures in this folder or built inline, and the stages are exercised with fake pages / injected fetchers, exactly like the rest of the suite.
"""

import logging
import pytest
import sqlite3

from bs4 import BeautifulSoup
from pathlib import Path
from unittest.mock import patch

from crawler.crawler_product_html_parser import run_crawler_product_html_parser
from crawler.crawler_product_scraper import scrape_product_urls
from crawler.crawler_search_html_parser import crawler_search_html_parser
from crawler.crawler_search_scraper import scrape_urls
from crawler.crawler_seed import alrogithmic_paginator, resolve_pagination, run_crawler_seed

from main import (
    ProductParserStage,
    ProductScraperStage,
    SearchParserStage,
    SearchScraperStage,
    SeedStage,
    get_default_stages,
    get_stage_pipeline,
    validate_stage_selection
)

from utilities.database import Database
from utilities.site_contract import (
    ConfigurationError,
    PRODUCT_URL_KEY,
    SiteCapability,
    SiteCapabilityError,
    WebsiteToScrape
)
from utilities.specific_sites import (
    Amazon,
    BooksToScrape,
    MercadoLibre,
    site_registry,
    specific_site_setup
)

logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

TESTS_DIR = Path(__file__).parent


# ---------------------------
# Fakes and fixtures
# ---------------------------
class FakePage:
    def goto(self, url, timeout=0):
        pass
    def reload(self, timeout=0):
        pass
    def wait_for_selector(self, wait_selector, timeout=0):
        pass

fake_page = FakePage()

@pytest.fixture
def tmp_db(tmp_path):

    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()


@pytest.fixture
def tmp_paths_dict(tmp_path):
    data_dir = tmp_path / 'data_dir'
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir = data_dir / 'output_dir'
    output_dir.mkdir(parents=True, exist_ok=True)

    return {'data_dir': data_dir, 'output_dir': output_dir}

@pytest.fixture
def books_search_results_soup():
    with open(TESTS_DIR / 'test_page.html', encoding='utf-8') as f:
        return BeautifulSoup(f, 'html.parser')

@pytest.fixture
def books_product_page_soup():
    with open(TESTS_DIR / 'test_book.html', encoding='utf-8') as f:
        return BeautifulSoup(f, 'html.parser')

# Offline HTML built with the selectors MercadoLibre already declares, so its existing parsing can be exercised without reaching the live site.
MERCADOLIBRE_SEARCH_RESULTS_HTML = """
<ul>
    <li class="ui-search-layout__item">
        <img class="poly-component__image-overlay" data-src="https://http2.mlstatic.com/D_MLA123456-O.jpg">
        <h3 class="poly-component__title-wrapper">Guitarra criolla usada</h3>
        <a class="poly-component__title" href="https://articulo.mercadolibre.com.ar/MLA-123456-guitarra">link</a>
        <span class="andes-money-amount__fraction">150.000</span>
    </li>
    <li class="ui-search-layout__item">
        <img class="poly-component__image-overlay" data-src="https://http2.mlstatic.com/D_MLA654321-O.jpg">
        <h3 class="poly-component__title-wrapper">Guitarra electrica usada</h3>
        <a class="poly-component__title" href="https://articulo.mercadolibre.com.ar/MLA-654321-guitarra">link</a>
        <span class="andes-money-amount__fraction">320.500</span>
    </li>
</ul>
"""

MERCADOLIBRE_PRODUCT_PAGE_HTML = """
<div>
    <h1 class="ui-pdp-title">Guitarra criolla usada</h1>
    <img class="poly-component__image-overlay" data-src="https://http2.mlstatic.com/D_MLA123456-O.jpg">
    <span class="andes-money-amount__fraction">150.000</span>
    <a class="poly-component__title" href="https://articulo.mercadolibre.com.ar/MLA-123456-guitarra">link</a>
    <p class="andes-visually-hidden">10 opiniones</p>
</div>
"""

# ---------------------------
# The registered adapters honour the contract
# ---------------------------
def test_every_registered_adapter_implements_the_contract():

    registry = site_registry()

    for site_name in registry:

        # Construction validates the declared capabilities against the actual implementation, so this would raise for a lying adapter.
        specific_site_config, seed_url = specific_site_setup(registry, site_name)

        assert isinstance(specific_site_config, WebsiteToScrape)
        assert seed_url # assert the website has a seed url
        assert specific_site_config.capabilities() <= frozenset(SiteCapability)
        assert specific_site_config.pagination_capability() in specific_site_config.capabilities()


def test_bookstoscrape_declares_every_capability():

    assert BooksToScrape().capabilities() == frozenset({
        SiteCapability.ALGORITHMIC_PAGINATION,
        SiteCapability.SEARCH_PAGE_READINESS,
        SiteCapability.PRODUCT_URL_EXTRACTION,
        SiteCapability.PRODUCT_PAGE_READINESS,
        SiteCapability.PRODUCT_PAGE_PARSING,
    })


def test_mercadolibre_declares_dynamic_pagination_and_product_page_capabilities():

    mercadolibre = MercadoLibre()

    assert mercadolibre.pagination_mode == "dynamic"
    assert mercadolibre.pagination_capability() is SiteCapability.DYNAMIC_PAGINATION
    assert mercadolibre.supports(SiteCapability.DYNAMIC_PAGINATION)
    assert mercadolibre.supports(SiteCapability.ALGORITHMIC_PAGINATION)
    assert mercadolibre.supports(SiteCapability.PRODUCT_PAGE_READINESS)
    assert mercadolibre.supports(SiteCapability.PRODUCT_PAGE_PARSING)


def test_mercadolibre_exposes_its_product_page_readiness_through_the_contract():

    mercadolibre = MercadoLibre()

    # The already existing product page selector is what the pipeline reads
    assert mercadolibre.wait_selector == mercadolibre.selector_to_start_process_in_individual_product_pages
    assert mercadolibre.wait_selector == "a.poly-component__title"


def test_amazon_is_a_partial_adapter():

    amazon = Amazon()

    assert amazon.capabilities() == frozenset({
        SiteCapability.ALGORITHMIC_PAGINATION,
        SiteCapability.SEARCH_PAGE_READINESS,
    })

    assert not amazon.supports(SiteCapability.PRODUCT_URL_EXTRACTION)
    assert not amazon.supports(SiteCapability.PRODUCT_PAGE_READINESS)
    assert not amazon.supports(SiteCapability.PRODUCT_PAGE_PARSING)


def test_amazon_unsupported_functionality_raises_a_capability_error():

    amazon = Amazon()

    with pytest.raises(SiteCapabilityError):
        amazon.individual_product_data_extraction(BeautifulSoup("<html></html>", 'html.parser'))

    with pytest.raises(SiteCapabilityError):
        amazon.discover_first_paginated_url(amazon.seed_urls[0])


# ---------------------------
# Contract enforcement
# ---------------------------
def test_adapter_declaring_a_capability_it_does_not_implement_is_rejected():

    class LyingSite(WebsiteToScrape):
        SITE_NAME = "lying"
        pagination_mode = "algorithmic"
        CAPABILITIES = frozenset({
            SiteCapability.ALGORITHMIC_PAGINATION,
            SiteCapability.PRODUCT_PAGE_PARSING,
        })

        def __init__(self):
            self.seed_urls = ["https://example.com/"]

        def build_pagination_url(self, base_url, page_number):
            return base_url

        def product_extraction(self, soup):
            return []

    with pytest.raises(SiteCapabilityError):
        LyingSite()


def test_adapter_declaring_product_page_readiness_without_selector_is_rejected():

    class SelectorLessSite(WebsiteToScrape):
        SITE_NAME = "selectorless"
        pagination_mode = "algorithmic"
        CAPABILITIES = frozenset({
            SiteCapability.ALGORITHMIC_PAGINATION,
            SiteCapability.PRODUCT_PAGE_READINESS,
        })

        def __init__(self):
            self.seed_urls = ["https://example.com/"]

        def build_pagination_url(self, base_url, page_number):
            return base_url

        def product_extraction(self, soup):
            return []

    with pytest.raises(SiteCapabilityError):
        SelectorLessSite()


def test_adapter_with_an_unknown_pagination_mode_is_rejected():

    class UnknownModeSite(WebsiteToScrape):
        SITE_NAME = "unknownmode"
        pagination_mode = "telepathic"
        CAPABILITIES = frozenset({SiteCapability.ALGORITHMIC_PAGINATION})

        def __init__(self):
            self.seed_urls = ["https://example.com/"]

        def build_pagination_url(self, base_url, page_number):
            return base_url

        def product_extraction(self, soup):
            return []

    with pytest.raises(ConfigurationError):
        UnknownModeSite()


def test_adapter_declaring_dynamic_mode_without_the_capability_is_rejected():

    class HalfDynamicSite(WebsiteToScrape):
        SITE_NAME = "halfdynamic"
        pagination_mode = "dynamic"
        CAPABILITIES = frozenset({SiteCapability.ALGORITHMIC_PAGINATION})

        def __init__(self):
            self.seed_urls = ["https://example.com/"]

        def build_pagination_url(self, base_url, page_number):
            return base_url

        def product_extraction(self, soup):
            return []

    with pytest.raises(SiteCapabilityError):
        HalfDynamicSite()


# ---------------------------
# Stage selection validation
# ---------------------------
def test_full_pipeline_is_valid_for_bookstoscrape():

    validate_stage_selection(get_default_stages(), get_stage_pipeline(), BooksToScrape())


def test_full_pipeline_is_valid_for_mercadolibre():

    validate_stage_selection(get_default_stages(), get_stage_pipeline(), MercadoLibre())


def test_full_pipeline_is_rejected_for_amazon_before_running_any_stage():

    with pytest.raises(SiteCapabilityError) as error:
        validate_stage_selection(get_default_stages(), get_stage_pipeline(), Amazon())

    message = str(error.value)

    # The error names the site, the offending stages and what they need
    assert "Amazon" in message
    assert "Crawler search parser" in message
    assert "Crawler product scraper" in message
    assert "Crawler product parser" in message
    assert SiteCapability.PRODUCT_URL_EXTRACTION.value in message
    assert SiteCapability.PRODUCT_PAGE_READINESS.value in message
    assert SiteCapability.PRODUCT_PAGE_PARSING.value in message

    # A stage Amazon does support is not reported
    assert "Crawler search scraper" not in message


def test_amazon_is_accepted_for_the_stages_it_supports():

    stages = {
        "seed": True,
        "search_scraper": True,
        "search_parser": False,
        "product_scraper": False,
        "product_parser": False,
    }

    validate_stage_selection(stages, get_stage_pipeline(), Amazon())


def test_stage_selection_missing_a_stage_key_is_a_configuration_error():

    stages = get_default_stages()
    del stages["product_parser"]

    with pytest.raises(ConfigurationError):
        validate_stage_selection(stages, get_stage_pipeline(), BooksToScrape())


def test_stage_required_capabilities_match_the_pipeline_stages():

    books = BooksToScrape()
    mercadolibre = MercadoLibre()

    assert SeedStage().required_capabilities(books) == frozenset({
        SiteCapability.ALGORITHMIC_PAGINATION
    })

    # A dynamic site also needs to discover its canonical pagination base
    assert SeedStage().required_capabilities(mercadolibre) == frozenset({
        SiteCapability.ALGORITHMIC_PAGINATION,
        SiteCapability.DYNAMIC_PAGINATION
    })

    assert SearchScraperStage().required_capabilities(books) == frozenset({
        SiteCapability.SEARCH_PAGE_READINESS
    })
    assert SearchParserStage().required_capabilities(books) == frozenset({
        SiteCapability.PRODUCT_URL_EXTRACTION
    })
    assert ProductScraperStage().required_capabilities(books) == frozenset({
        SiteCapability.PRODUCT_PAGE_READINESS
    })
    assert ProductParserStage().required_capabilities(books) == frozenset({
        SiteCapability.PRODUCT_PAGE_PARSING
    })


# ---------------------------
# Pagination behaviour is preserved
# ---------------------------
def test_bookstoscrape_algorithmic_pagination_is_preserved(tmp_db):

    books = BooksToScrape()
    seed_url = books.seed_urls[0]

    canonical_url = resolve_pagination(books, seed_url, books.SITE_NAME, error_logger)

    assert canonical_url == seed_url

    assert alrogithmic_paginator(books, 3, canonical_url) == [
        "https://books.toscrape.com/catalogue/page-1.html",
        "https://books.toscrape.com/catalogue/page-2.html",
        "https://books.toscrape.com/catalogue/page-3.html",
    ]


def test_bookstoscrape_seed_stage_inserts_paginated_urls(tmp_db):

    books = BooksToScrape()

    run_crawler_seed(tmp_db, books, books.seed_urls[0], books.SITE_NAME, 2, logger, error_logger)

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("SELECT url_name, status FROM Urls ORDER BY url_name")

        assert cur.fetchall() == [
            ("https://books.toscrape.com/catalogue/page-1.html", "pending"),
            ("https://books.toscrape.com/catalogue/page-2.html", "pending"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_mercadolibre_dynamic_pagination_is_preserved():

    mercadolibre = MercadoLibre()
    canonical = "https://listado.mercadolibre.com.ar/guitarra-usada_Desde_51_NoIndex_True"

    # Discovery is the only step that needs the live site, so it is replaced
    with patch.object(MercadoLibre, 'discover_first_paginated_url', return_value=canonical) as discovery:

        canonical_url = resolve_pagination(
            mercadolibre,
            mercadolibre.seed_urls[0],
            mercadolibre.SITE_NAME,
            error_logger
        )

    discovery.assert_called_once_with(mercadolibre.seed_urls[0])
    assert canonical_url == canonical

    assert alrogithmic_paginator(mercadolibre, 3, canonical_url) == [
        "https://listado.mercadolibre.com.ar/guitarra-usada",
        "https://listado.mercadolibre.com.ar/guitarra-usada_Desde_49_NoIndex_True",
        "https://listado.mercadolibre.com.ar/guitarra-usada_Desde_98_NoIndex_True",
    ]


def test_amazon_algorithmic_pagination_is_preserved():

    amazon = Amazon()
    seed_url = amazon.seed_urls[0]

    canonical_url = resolve_pagination(amazon, seed_url, amazon.SITE_NAME, error_logger)

    assert alrogithmic_paginator(amazon, 2, canonical_url) == [
        "https://www.amazon.com/s?k=laptop&page=1",
        "https://www.amazon.com/s?k=laptop&page=2",
    ]


# ---------------------------
# Search page readiness is what the search scraper uses
# ---------------------------
@pytest.mark.parametrize("adapter_class", [BooksToScrape, MercadoLibre, Amazon])
def test_search_scraper_uses_the_search_readiness_selector_of_the_adapter(
    adapter_class, tmp_db, tmp_paths_dict):

    specific_site_config = adapter_class()
    used_selectors = list()

    def fake_fetch_html(page, url, logger, selector_to_start_process):
        used_selectors.append(selector_to_start_process)
        return "<html></html>"

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO Urls (url_name, status) VALUES (?, ?)", ("https://example.com/page-1", "pending")
        )
        conn.commit()

        with patch('crawler.crawler_search_scraper.countdown_sleep_timer'):
            scrape_urls(
                tmp_db,
                tmp_paths_dict,
                fake_page,
                specific_site_config,
                logger,
                error_logger,
                fetch_html=fake_fetch_html
            )

        assert used_selectors == [specific_site_config.selector_to_start_process]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ---------------------------
# Product URL boundary between search parsing and product fetching
# ---------------------------
def test_bookstoscrape_search_parsing_yields_product_urls(books_search_results_soup):

    books = BooksToScrape()

    products = books.product_extraction(books_search_results_soup)

    assert products
    for product in products:
        assert product[PRODUCT_URL_KEY]
        assert product[PRODUCT_URL_KEY].startswith("https://books.toscrape.com/catalogue/")


def test_mercadolibre_search_parsing_yields_product_urls():

    mercadolibre = MercadoLibre()
    soup = BeautifulSoup(MERCADOLIBRE_SEARCH_RESULTS_HTML, 'html.parser')

    products = mercadolibre.product_extraction(soup)

    assert [product[PRODUCT_URL_KEY] for product in products] == [
        "https://articulo.mercadolibre.com.ar/MLA-123456-guitarra",
        "https://articulo.mercadolibre.com.ar/MLA-654321-guitarra",
    ]
    assert [product["price"] for product in products] == [150000, 320500]


def test_amazon_search_parsing_does_not_yield_product_urls():

    amazon = Amazon()

    amazon_search_results_html = """
    <div data-component-type="s-search-result">
        <h2 class="a-size-medium a-spacing-none a-color-base a-text-normal">A laptop</h2>
        <span class="a-price-symbol">$</span>
        <span class="a-price-whole">1.999</span>
    </div>
    """

    products = amazon.product_extraction(BeautifulSoup(amazon_search_results_html, 'html.parser'))

    # This is exactly why Amazon does not declare PRODUCT_URL_EXTRACTION: the
    # search parser stage would have no URL to hand over to the product scraper
    assert products
    for product in products:
        assert PRODUCT_URL_KEY not in product


def test_search_parser_stage_stores_the_product_urls_of_bookstoscrape(
    tmp_db, tmp_paths_dict):

    books = BooksToScrape()

    page_html = (TESTS_DIR / 'test_page.html').read_text(encoding='utf-8')
    (tmp_paths_dict['data_dir'] / 'page_1.html').write_text(page_html, encoding='utf-8')

    crawler_search_html_parser(
        ['page_1.html'],
        tmp_paths_dict,
        books,
        tmp_db,
        logger,
        error_logger
    )

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("SELECT product_url, fetch_status FROM ProductPages")
        stored = cur.fetchall()

        assert stored
        for product_url, fetch_status in stored:
            assert product_url.startswith("https://books.toscrape.com/catalogue/")
            assert fetch_status == 'pending'

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ---------------------------
# Product page readiness is what the product scraper uses
# ---------------------------
@pytest.mark.parametrize("adapter_class", [BooksToScrape, MercadoLibre])
def test_product_scraper_uses_the_product_readiness_selector_of_the_adapter(
    adapter_class, tmp_db, tmp_paths_dict):

    specific_site_config = adapter_class()
    used_selectors = list()

    def fake_fetch_html(page, url, logger, wait_selector):
        used_selectors.append(wait_selector)
        return "<html></html>"

    tmp_db.insert_product_url({PRODUCT_URL_KEY: 'https://example.com/product-1'})

    with patch('crawler.crawler_product_scraper.countdown_sleep_timer'):
        scrape_product_urls(
            tmp_db,
            tmp_paths_dict,
            fake_page,
            specific_site_config,
            logger,
            error_logger,
            fetch_html=fake_fetch_html
        )

    assert used_selectors == [specific_site_config.wait_selector]


# ---------------------------
# Individual product parsing
# ---------------------------
def test_bookstoscrape_individual_product_parsing(books_product_page_soup):

    books = BooksToScrape()

    product = books.individual_product_data_extraction(books_product_page_soup)

    assert product["name"] == "A Light in the Attic"
    assert product["slug"] == "a_light_in_the_attic"
    assert product["price"] == "51.77"
    assert product["currency"] == "£"
    assert product["product_code"]

    # The keys the product parser stage writes to the DB
    for key in ("slug", "currency", "price", "product_code", "reviews", "images"):
        assert key in product

def test_mercadolibre_individual_product_parsing():

    mercadolibre = MercadoLibre()
    soup = BeautifulSoup(MERCADOLIBRE_PRODUCT_PAGE_HTML, 'html.parser')

    product = mercadolibre.individual_product_data_extraction(soup)

    assert product["name"] == "Guitarra criolla usada"
    assert product["price"] == 150000
    assert product["currency"] == "ARS"
    assert product["product_code"] == "MLA123456"
    assert product["reviews"] == "10 opiniones"

    for key in ("slug", "currency", "price", "product_code", "reviews", "images"):
        assert key in product

@pytest.mark.parametrize(
    "adapter_class, product_html, expected_name",
    [
        (BooksToScrape, (TESTS_DIR / 'test_book.html').read_text(encoding='utf-8'), 'a_light_in_the_attic'),
        (MercadoLibre, MERCADOLIBRE_PRODUCT_PAGE_HTML, 'guitarra_criolla_usada'),
    ]
)
def test_product_parser_stage_stores_parsed_products(
    adapter_class, product_html, expected_name, tmp_db, tmp_paths_dict):

    specific_site_config = adapter_class()

    (tmp_paths_dict['output_dir'] / 'product_1.html').write_text(product_html, encoding='utf-8')

    tmp_db.insert_product_url({PRODUCT_URL_KEY: 'https://example.com/product-1'})

    conn, cur = None, None

    try:

        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE ProductPages SET fetch_status = ?, filename = ? WHERE id = ?",
            ('fetched', 'product_1.html', 1)
        )
        conn.commit()

        run_crawler_product_html_parser(
            tmp_db,
            specific_site_config,
            tmp_paths_dict,
            logger,
            error_logger
        )

        cur.execute("SELECT product_name, parse_status FROM ProductPages WHERE id = 1")

        assert cur.fetchone() == (expected_name, 'parsed_succeeded')

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()