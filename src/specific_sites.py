import re

class AmazonConfig:
    """
    Configuration class containing all Amazon-specific
    scraping parameters so the crawler code stays generic.
    """
    
    SITE_NAME = 'Amazon'

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

        print(products_of_page)

        return products_of_page

    
class MercadoLibreConfig:
    """
    Mercado Libre-specific configuration class.
    Provides selectors, pagination rules, and fallback extraction.
    """

    SITE_NAME = "Mercado Libre"

    def __init__(self):

        # Example seed URL — replace with your query
        self.seed_urls = [
            "https://listado.mercadolibre.com.ar/placa-grafica"
        ]

        # Selectors for checking JS has loaded
        self.selector_to_start_process = "li.ui-search-layout__item"

        # Product fields
        self.product_container_selector = ("li", "ui-search-layout__item")
        self.product_name_selector = ("h3", "poly-component__title-wrapper")
        self.price_selector = ("span", "andes-money-amount__fraction")
        self.currency_selector = ("span", "andes-money-amount__currency-symbol")

    # ---------------------------
    # URL Construction
    # ---------------------------
    def build_pagination_url(self, seed_url: str, page: int) -> str:
        """
        MercadoLibre pagination uses _Desde_ offset pagination.
        """
        if page == 1:
            return seed_url

        offset = (page - 1) * 48
        return f"{seed_url}_Desde_{offset}"

    # ---------------------------
    # Product parsing
    # ---------------------------
    def product_extraction(self, soup):
        containers = soup.find_all(
            self.product_container_selector[0],
            class_=self.product_container_selector[1]
        )

        products = []

        for container in containers:
            name, price, currency = None, None, None

            name_tag = container.find(
                self.product_name_selector[0],
                class_=self.product_name_selector[1]
            )
            if name_tag:
                name = name_tag.get_text(strip=True)

            price_tag = container.find(
                self.price_selector[0],
                class_=self.price_selector[1]
            )
            if price_tag:
                price = price_tag.get_text(strip=True)

            currency_tag = container.find(
                self.currency_selector[0],
                class_=self.currency_selector[1]
            )
            if currency_tag:
                currency = currency_tag.get_text(strip=True)

            # Fallback
            #if price is None:
                #currency, price = self.price_fallback_extraction(container)

            products.append({
                "name": name,
                "currency": currency,
                "price": price,
            })

        return products


