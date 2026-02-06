import re
import time
import random

from playwright.sync_api import sync_playwright
from utilities.stealth import stealth_context, human_scroll
from utilities.utils import setup_loggers, slugify

#Logging setup
logger, error_logger = setup_loggers()

def site_registry():
    """
    Dictionary object containing the specific configuration classes for each site.
    """
    SITE_REGISTRY = {
        "amazon": AmazonConfig,
        "mercadolibre": MercadoLibreConfig,
    }
    return SITE_REGISTRY

def specific_site_setup(SITE_REGISTRY: dict, site_name: str) -> tuple:
    """
    Loads the site name, seed_url and specific config of a site from the registry by reference of its name.
    """
    if site_name not in SITE_REGISTRY:
        raise ValueError(f"Unsupported site: {site_name}")
    specific_site_config = SITE_REGISTRY[site_name]()
    seed_url = specific_site_config.seed_urls[0]
    return specific_site_config, seed_url

class AmazonConfig:
    """
    Amazon-specific configuration class.
    Provides selectors, pagination rules, and fallback extraction.
    """
    
    SITE_NAME = "Amazon"
    pagination_mode = "algorithmic"

    def __init__(self):
        
        # Base URLs or seed URLs
        self.seed_urls = [
            "https://www.amazon.com/s?k=laptop"
        ]

        # Required selectors
        self.selector_to_start_process = "span.a-price-whole"
        self.product_name_selector = ("h2", "a-size-medium a-spacing-none a-color-base a-text-normal")
        self.price_selector = ("span", "a-price-whole")
        self.currency_selector = ("span", "a-price-symbol")

    # ---------------------------
    # URL Construction
    # ---------------------------
    def build_pagination_url(self, seed_url: str, i: int) -> str:
        """
        Returns a properly formatted Amazon pagination URL.
        """
        paginated_url = f"{seed_url}&page={i}"

        return paginated_url
    
    # ---------------------------
    # Price extraction fallback functions
    # ---------------------------

    #ARS Function
    def price_fallback_extraction_for_amz_ARS(self, container):

        price_pattern_ARS = r'ARS\s*([\d.,]+)'

        spans = container.find_all('span', class_='a-color-base')

        price, currency = None, None

        for span in spans:
            text = span.get_text(strip=True)
            if re.search(price_pattern_ARS, text):
                match = re.search(price_pattern_ARS, text)
                if match:
                    price = match.group(1)
                    currency = match.group(0).split()[0].strip()
                    break
        return currency, price

    #USD Function
    def price_fallback_extraction_for_amz_USD(self, container):

        price_pattern_USD = r'\$\s*([\d.,]+)'

        spans = container.find_all('span', class_='a-color-base')

        price, currency = None, None

        for span in spans:
            text = span.get_text(strip=True)
            if re.search(price_pattern_USD, text):
                match = re.search(price_pattern_USD, text)
                if match:
                    currency_to_strip = match.group(0)[0]
                    currency = currency_to_strip[0]
                    price = match.group(1)
                    #print(currency, price)
                    break
        return currency, price
    
    # ---------------------------
    # Product parsing function for text.py
    # ---------------------------
    def product_extraction(self, soup):

        containers = soup.find_all("div", attrs={"data-component-type": "s-search-result"})

        products_of_page = list()

        #3. Price and name extraction
        for container in containers:

            name = None
            price = None
            currency = None

            #Name extraction
            name_tag = container.find(self.product_name_selector[0], class_=self.product_name_selector[1])
            if name_tag:
                name = name_tag.get_text(strip=True)

            #Price extraction
            price_tag = container.find(self.price_selector[0], class_=self.price_selector[1])
            if price_tag:
                price = price_tag.get_text(strip=True)
                if price.endswith('.'):
                    price = price[:-1]

            #Currency extraction
            currency_tag = container.find(self.currency_selector[0], class_=self.currency_selector[1])
            if currency_tag:
                currency = currency_tag.get_text(strip=True)

            #Fallback extraction
            if price is None:

                currency, price = self.price_fallback_extraction_for_amz_USD(container)

            individual_product = {
                "name" : name,
                "currency" : currency,
                "price" : price,
            }

            products_of_page.append(individual_product)

        #print(products_of_page)

        return products_of_page

####################################################

class MercadoLibreConfig:
    """
    Mercado Libre-specific configuration class.
    Provides selectors, pagination rules, and extraction parameters.
    """

    SITE_NAME = "MercadoLibre"
    pagination_mode = "dynamic"

    def __init__(self):

        # Set seed_url here
        self.seed_urls = [
            "https://listado.mercadolibre.com.ar/boya-natacion-aguas-abiertas"
        ]

        # Selectors for checking JS has loaded in search results pages
        self.selector_to_start_process = "li.ui-search-layout__item"
        self.selector_siguiente_for_pagination = "li.ui-search-filter-container"

        # Search Result fields
        self.product_container_selector = ("li", "ui-search-layout__item")
        self.product_name_selector = ("h3", "poly-component__title-wrapper")
        self.price_selector = ("span", "andes-money-amount__fraction")
        #self.currency_selector = ("span", "andes-money-amount__currency-symbol")
        self.search_results_page_product_image_selector_1 = ("img", "poly-component__image-overlay")
        self.search_results_page_product_image_selector_2 = ("img", "poly-component__picture lazy-loadable")
        self.product_link_selector = ("h3", "poly-component__title-wrapper")

        # Individual product pages
        self.selector_to_start_process_in_individual_product_pages = "a.poly-component__title"
        self.individual_product_name_selector = ("h1", "ui-pdp-title")

    # ---------------------------
    # URL Construction
    # ---------------------------
    def discover_first_paginated_url(self, seed_url: str):
        """
        Fetch the first MercadoLibre canonical URL.
        """

        with sync_playwright() as p:

            loaded = False
            seed_url = self.seed_urls[0]
            browser = p.chromium.launch(
            headless=False
            )
            try:
                context = stealth_context(browser)
                page = context.new_page()

                #Fetch page 1 of ML
                try:
                    page.goto(seed_url, timeout=30000)
                    loaded = True
                except Exception:
                    error_logger.warning(f"First failure on {seed_url}", exc_info=True)
                    time.sleep(random.uniform(15, 25))

                #Second try
                if not loaded:
                    try:
                        time.sleep(random.uniform(11, 14))
                        page.reload(timeout=30000)
                        loaded = True
                        logger.info(f"URL: {seed_url} succesfully loaded")
                    except Exception:
                        error_logger.warning(f"Second failure on {seed_url}", exc_info=True) 
                        return None  
                
                #If page loaded, proceed and scroll
                if loaded:
                    try:
                        print(f"Scrolling for {seed_url}")
                        human_scroll(page, min_increment=200, max_increment=450,  timeout=15.0)
                    except Exception:
                        error_logger.error(f"Scrolling error on {seed_url}", exc_info=True)

                # Go to the end
                page.locator("body").press("End")

                # Click "Siguiente"
                page.click("li.andes-pagination__button--next a")

                # This is the first canonical paginated URL
                time.sleep(random.uniform(4, 6))
                canonical_url = page.url
                if not canonical_url:
                    print("Could not fetch canonical url")
                    return None
                return canonical_url
            finally:
                browser.close()

    def build_pagination_url(self, canonical_url: str, page_number: int):
        "Algorithmic Mercado libre URL generator."
        try:
            clean_canonical_url = canonical_url.split("_Desde_")[0]
        except Exception as e:
            print(f"Unable to clean provided seed URL for reason: {e}")
            clean_canonical_url = canonical_url
        if page_number == 1:
            return clean_canonical_url
        ITEMS_PER_PAGE = 49
        offset = (page_number - 1) * ITEMS_PER_PAGE
        return (f"{clean_canonical_url}_Desde_{offset}_NoIndex_True")
        
    # ---------------------------
    # Product parsing
    # ---------------------------
    def product_extraction(self, soup):
        #Find all product containers on the page
        containers = soup.find_all(
            self.product_container_selector[0],
            class_=self.product_container_selector[1]
        )

        products = []
        seen_images = set()

        for container in containers:
            name, price, product_id, img, slug, link = [None] * 6
            currency = 'ARS'

            #Name
            name_tag = container.find(
                self.product_name_selector[0],
                class_=self.product_name_selector[1]
            )
            if name_tag:
                name = name_tag.get_text(strip=True)

            #Price
            price_tag = container.find(
                self.price_selector[0],
                class_=self.price_selector[1]
            )
            if price_tag:
                price = price_tag.get_text(strip=True)
                raw_price = int(price.replace('.', '')) 

            #Currency
            #currency_tag = container.find(self.currency_selector[0], class_=self.currency_selector[1])
            #if currency_tag:
                #currency = currency_tag.get_text(strip=True)

            #Image
            candidate = None
            img_tag = container.find(self.search_results_page_product_image_selector_1[0])
            if img_tag:
                candidate = img_tag.get("data-src")
                if not candidate:
                    src = img_tag.get("src")
                    if src and not src.startswith("data:image"):
                        candidate = src
            if candidate and candidate not in seen_images:
                seen_images.add(candidate)
                img = candidate

            #Product_id
            # Extract item_id from image_link
            if img is not None:
                m = re.search(r'MLA(\d+)', img)
            if m:
                product_id = f"MLA{m.group(1)}"

            #Slug
            if name:
                try:
                    slug = slugify(name)
                except:
                    pass

            #Link of product
            link_tag = container.find("a", class_="poly-component__title")
            href = link_tag.get("href")
            if href:
                link = href
            if href.startswith("https://click"):
                link = None


            #Build products
            products.append({
                "name": name,
                "slug": slug,
                "product_id": product_id,
                "currency": currency,
                "price": raw_price,
                "link" : link,
                "images": [
                img
                ]

            })

        return products
    

    def individual_product_data_extraction(self, soup):
        
        seen_images = set()

        name, price, product_code, img, slug, link = [None] * 6

        #Currency
        currency = 'ARS'

        #Name
        name_tag = soup.find(
            self.individual_product_name_selector[0],
            class_=self.individual_product_name_selector[1]
        )
        if name_tag:
            name = name_tag.get_text(strip=True)
        else:
            print('no name found')

        #Price
        price_tag = soup.find(
            self.price_selector[0],
            class_=self.price_selector[1]
        )
        if price_tag:
            price = price_tag.get_text(strip=True)
            raw_price = int(price.replace('.', '')) 

        #Image
        candidate = None
        img_tag = soup.find(self.search_results_page_product_image_selector_1[0])
        if img_tag:
            candidate = img_tag.get("data-src")
            if not candidate:
                src = img_tag.get("src")
                if src and not src.startswith("data:image"):
                    candidate = src
        if candidate and candidate not in seen_images:
            seen_images.add(candidate)
            img = candidate

        #Product_id
        # Extract item_id from image_link
        if img is not None:
            m = re.search(r'MLA(\d+)', img)
        if m:
            product_code = f"MLA{m.group(1)}"

        #Slug
        if name:
            try:
                slug = slugify(name)
            except:
                pass

        #Link of product
        link_tag = soup.find("a", class_="poly-component__title")
        href = link_tag.get("href")
        if href:
            link = href
        if href.startswith("https://click"):
            link = None

        #Reviews
        reviews = None
        reviews_tag = soup.find("p", class_="andes-visually-hidden")
        if reviews_tag:
            reviews = reviews_tag.get_text(strip=True)

        #Build products
        product = ({
            "name": name,
            "slug": slug,
            "product_code": product_code,
            "currency": currency,
            "price": raw_price,
            "product_url" : link,
            "reviews" : reviews,
            "images": [
            img
            ]

        })

        return product