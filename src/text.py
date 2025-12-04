from bs4 import BeautifulSoup
import os
import re
import json
from db import db_initialization, insert_product, get_url_and_id_using_filename
from utils import setup_loggers, setup_directories

#Config directories
BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR = setup_directories()

#Load config
config_path = os.path.join(BASE_DIR, "config.json")
with open(config_path) as f:
    config = json.load(f)
    db_path = config.get("database_path", "mini.sqlite")

#DB setup
db_path = os.path.join(DATA_DIR, db_path)
db = db_initialization(db_path)

#Price pattern for fallback extraction
price_pattern_USD = r'\$\s*([\d.,]+)'

#Logging setup
logger, error_logger = setup_loggers()

#Main logic
for file in os.listdir(DATA_DIR):
    
    if file.endswith(".html"):

        filename = file
        file_path = os.path.join(DATA_DIR, file)
        print(file_path)

        products_of_page = []

        with open(file_path, "r", encoding="utf-8") as f:

            #1. Get URL id using filename
            url_id, url = get_url_and_id_using_filename(db, filename)

            #2. Extract product containers

            soup = BeautifulSoup(f, 'html.parser')

            containers = soup.find_all("div", attrs={"data-component-type": "s-search-result"})

            #3. Price and name extraction
            for container in containers:

                name = None
                price = None
                currency = None

                #Name extraction
                name_tag = container.find('h2', class_='a-size-medium a-spacing-none a-color-base a-text-normal')
                if name_tag:
                    name = name_tag.get_text(strip=True)

                #Price extraction
                price_tag = container.find('span', class_='a-price-whole')
                if price_tag:
                    price = price_tag.get_text(strip=True)
                    if price.endswith('.'):
                        price = price[:-1]

                #Currency extraction
                currency_tag = container.find('span', class_= "a-price-symbol")
                if currency_tag:
                    currency = currency_tag.get_text(strip=True)
                
                #Fallback price and currency extraction
                if price is None:

                    spans = container.find_all('span', class_='a-color-base')

                    for span in spans:
                        text = span.get_text(strip=True)
                        if re.search(price_pattern_USD, text):
                            match = re.search(price_pattern_USD, text)
                            if match:
                                currency_to_strip = match.group(0)[0]
                                currency = currency_to_strip[0]
                                price = match.group(1)
                                print(currency, price)
                                break

                individual_product = {
                    "name" : name,
                    "currency" : currency,
                    "price" : price,
                }

                products_of_page.append(individual_product)

            #DB Product insertion
            for individual_product in products_of_page:

                #Go over the list products of page and insert the product with the corresponding URL_ID in the DB
                insert_product(db, individual_product, url_id)
                print(f"Inserted product for URL {url_id}")

db["conn"].close()











