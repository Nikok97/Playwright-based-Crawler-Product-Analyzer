import time, random
import os
import re
import json

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from stealth import human_scroll
from pathlib import Path
from db import now, update_url_date, update_filename_for_url, update_url_status, mark_url_as_failed

#Def Now
def now():
    """Return the actual date, hour and timezone."""
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d")

#Def Now
def now_with_hours():
    """
    Returns the actual date and hour in string format.
    """
    from datetime import datetime   
    return datetime.now().strftime("%Y-%m-%d, %H:%M hs.")

def setup_loggers():
    """
    Sets up a general logger and an error logger, with corresponding handlers and levels.
    """
    import logging
    # Get the root logger (used by logging.info, logging.warning, etc.)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Add a file handler only if one does not already exist
    if not logger.handlers:
        handler = logging.FileHandler('crawler.log')

        # Define the log format
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        )
        handler.setFormatter(formatter)

        #Attach the handler to the root logger
        logger.addHandler(handler)

    # Create / get a named logger dedicated to errors
    error_logger = logging.getLogger('error_logger')
    error_logger.setLevel(logging.ERROR)

    # Prevent error logs from propagating to the root logger
    error_logger.propagate = False

    # Add an error file handler only once
    if not error_logger.handlers:
        error_handler = logging.FileHandler('crawler_errors.log')
        error_handler.setLevel(logging.ERROR)

        # Reuse the same formatting style for consistency
        error_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        )
        error_handler.setFormatter(error_formatter)

        # Attach the handler to the error logger
        error_logger.addHandler(error_handler)

    # Return both loggers for use
    return logger, error_logger

QUERY_EXPORT = '''
SELECT Urls.id, Urls.name, Urls.date, Products.name, Products.currency, Products.price
FROM Urls
LEFT JOIN Products ON Urls.id = Products.url_id
ORDER BY Urls.id;
'''

# Save to JSON
def export_to_json(db):

    """Export crawling results directly to a json file."""

    import json

    filename = input("Name of desired json file: ").strip()
    date = now()

    # If the user didn't type ".json" this adds it
    if not filename.lower().endswith(".json"):
        filename += "_" + date + ".json"

    rows = db["cur"].execute(QUERY_EXPORT)

    list_of_objects = list()

    for row in rows:

        url_id = row[0]
        url_title = row[1]
        
        if (row[3] == None):
            continue
        else:
            product_name = row[3]
            product_currency = row[4]
            product_price = row[5]

        temporary_dic_object = {
            "id": url_id,
            "url_title": url_title,
            "name" : product_name,
            "currency": product_currency,
            "price": product_price

        }

        list_of_objects.append(temporary_dic_object)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(list_of_objects, f, indent=4, ensure_ascii=False)

    print("Exported crawl results to exported_data")
            
#Def export CSV
def export_to_csv(db):

    """Export crawling results to a csv file."""

    import csv

    filename = input("Name of desired csv file: ").strip()
    date = now()
    
    rows = db["cur"].execute(QUERY_EXPORT)

    # If the user didn't type ".csv", add it
    if not filename.lower().endswith(".csv"):
        filename += "_" + date + ".csv"

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        #Headers
        writer.writerow([
            'id', 'url_title', 'date',
            'product_title', 'currency', 'product_price'
        ])

        # Write rows
        for row in rows:
            if row[4] is None:
                continue
            else:
                writer.writerow(row)

    print(f"Exported crawl results to {filename}")

def setup_directories_os():
    import os
    import sys

    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        PARENT_DIR = os.path.dirname(CURRENT_DIR)
        DATA_DIR = os.path.join(BASE_DIR, "data")
        OUTPUT_DIR = os.path.join(DATA_DIR, "output")
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        print(f"Could not create required directories: error {e}")
        sys.exit()

    return BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR, OUTPUT_DIR

def setup_directories_pathlib():
    from pathlib import Path
    try:
        SCRIPT_PATH = Path(__file__).resolve()
        CURRENT_DIR = SCRIPT_PATH.parent
        BASE_DIR = CURRENT_DIR.parent
        DATA_DIR = BASE_DIR / "data"
        OUTPUT_DIR = DATA_DIR / "output"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        paths_dict = {
            "script_path": SCRIPT_PATH,
            "current_dir": CURRENT_DIR,
            "base_dir": BASE_DIR,
            "data_dir": DATA_DIR,
            "output_dir": OUTPUT_DIR
        }
    except Exception as e:
        print(f"Could not create required directories: error {e}")
        raise RuntimeError

    return paths_dict

def countdown_sleep_timer(waiting_time):
    import time
    remaining = int(waiting_time)

    while remaining > 0:
        print(f"Waiting… {remaining} seconds remaining".ljust(40), end="\r", flush=True)
        time.sleep(1)
        remaining -= 1
    print() # move to clean line
    print("Waiting… done.            ")

#Logging setup
logger, error_logger = setup_loggers()

def load_page(page, url, specific_site_config, max_attempts=2) -> bool:
    """
    Tries to load the URL and waits for the required selector.
    Returns True if the page is ready for processing.
    """
    #Navigation block
    success = False
    for attempt in range(1, max_attempts + 1):
        try:
            #1st try
            if attempt == 1:
                page.goto(url, timeout=30000)
            #2nd (or n) retries
            else:
                time.sleep(random.uniform(15, 25))
                page.reload(timeout=30000)
            #Page loaded, wait for selector
            page.wait_for_selector(specific_site_config.selector_to_start_process, timeout=8000)
            success = True
            logger.info(f"URL: {url} succesfully loaded on attempt {attempt}")
            break
        except PlaywrightTimeoutError:
            error_logger.warning(f"Load timeout on {url} on attempt {attempt}")
            continue
        except Exception:
            error_logger.error(f"Navigation failure on {url} on attempt {attempt}", exc_info=True)
            continue
    #Final check
    if success:
        return True 
    else:
        return False
    
def perform_scroll(page, url) -> bool:
    """
    Scrolls the page to trigger JS loading.
    Returns False if scrolling fails or times out.
    """
    try:
        human_scroll(page, min_increment=200, max_increment=450,  timeout=15.0)
        print(f"Scrolling for {url}")
        return True
    except PlaywrightTimeoutError:
        error_logger.warning(f"Scroll timeout on {url}")
        return False
    except Exception:
        error_logger.error(
            f"Unexpected scroll error on {url}",
            exc_info=True
        )
        return False
    
def extract_html(page, url) -> str | None:
    """
    Returns page HTML or None if extraction fails.
    """
    #Fetch HTML
    logger.info(f"Fetching HTML for: {url}")
    try:
        html = page.content()
        logger.info(f"Fetched HTML content for {url}")
        return html
    except Exception:
        error_logger.error(
            f"HTML fetching error for {url}",
            exc_info=True)
        return None
     
def write_html(url_id, html, tmp_path) -> bool:
    """
    Writes HTML.
    """
    #HTML writing
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)
            return True
    except Exception:
        error_logger.error(
            f"HTML writing error for {url_id}",
            exc_info=True)
        return False

    
def persist_result_in_db(db, url, url_id, html, DATA_DIR):
    """
    Atomically saves HTML and updates DB metadata.
    Raises on failure.
    """
    #File path setup
    try:
        filename = f"page_{url_id}.html"
        output_path = os.path.join(DATA_DIR, filename)
        tmp_path = output_path + ".tmp"
    except Exception:
        error_logger.error(
            f"HTML pathing error for {url_id}",
            exc_info=True)
        raise
    #HTML writing
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        error_logger.error(
            f"HTML writing error for {url_id}",
            exc_info=True)
        raise
    #Insert link to DB
    try:
        date = str(now())
        update_url_date(url, db, date)
        update_filename_for_url(url, db, filename)
        update_url_status(url, db, status="fetched")
        os.replace(tmp_path, output_path)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        error_logger.error(f"DB or filesystem error while processing {url}", exc_info=True)
        raise

def process_single_url(db, url, url_id, page, specific_site_config, page_counter, DATA_DIR):
    """
    Docstring for process_single_url
    
    :param db: Description
    :param url: Description
    :param url_id: Description
    :param page: Description
    :param specific_site_config: Description
    :param page_counter: Description
    :param DATA_DIR: Description
    """
    #Navigation phase
    if not load_page(page, url, specific_site_config, max_attempts=2):
        mark_url_as_failed(db, url)
        return False
    print(f"{page_counter}. Target JavaScript selector detected in URL: {url}")

    #Scrolling phase
    if not perform_scroll(page, url):
        mark_url_as_failed(db, url)
        return False

    #Extra delay to let JS finish loading
    time.sleep(random.uniform(3, 5))

    #HTML extraction phase
    html = extract_html(page, url)
    if html is None:
        mark_url_as_failed(db, url)
        return False

    #DB persistence phase
    try:
        persist_result_in_db(db, url, url_id, html, DATA_DIR)
    except Exception:
        mark_url_as_failed(db, url)
        return False

    return True

def product_extraction(soup, specific_site_config):
        containers = soup.find_all(
            specific_site_config.product_container_selector[0],
            class_=specific_site_config.product_container_selector[1]
        )

        products = []

        for container in containers:
            name, price, currency = None, None, None

            name_tag = container.find(
                specific_site_config.product_name_selector[0],
                class_=specific_site_config.product_name_selector[1]
            )
            if name_tag:
                name = name_tag.get_text(strip=True)

            price_tag = container.find(
                specific_site_config.price_selector[0],
                class_=specific_site_config.price_selector[1]
            )
            if price_tag:
                price = price_tag.get_text(strip=True)

            currency_tag = container.find(
                specific_site_config.currency_selector[0],
                class_=specific_site_config.currency_selector[1]
            )
            if currency_tag:
                currency = currency_tag.get_text(strip=True)

            products.append({
                "name": name,
                "currency": currency,
                "price": price,
            })

        return products

def sort_pages(files):
    """
    Docstring for sort_pages
    
    :param files: list of unsorted html files 
    """
    if files is None:
        return None
    return sorted(
        files,
        key=lambda f: int(re.search(r"\d+", f).group()) # type: ignore
    )

def list_of_html_files_compiler(directory):
    #HTML detection
    page_pattern = re.compile(r"^page_(\d+)\.html$")
    list_of_html_files = []
    #List building
    for file in os.listdir(directory):
        match = page_pattern.match(file)
        if match:
            list_of_html_files.append(file)
    #List ordering
    if list_of_html_files is None:
        return None
    else:
        return sorted(
            list_of_html_files,
            key=lambda f: int(re.search(r"\d+", f).group()) # type: ignore
        )
    
def list_of_json_files_compiler(directory):
    #JSON detection
    page_pattern = re.compile(r"^page_(\d+)\.json$")
    list_of_files = []
    #List building
    for file in os.listdir(directory):
        match = page_pattern.match(file)
        if match:
            list_of_files.append(file)
    #List ordering
    if list_of_files is None:
        return None
    else:
        return sorted(
            list_of_files,
            key=lambda f: int(re.search(r"\d+", f).group()) # type: ignore
        )
    
def json_writer(output_dir, list_of_products):
    import json
    #JSON writing
    with open(output_dir, 'w', encoding='utf-8') as f:
        json.dump(list_of_products, f, indent=4, ensure_ascii=False)

def slugify(text: str) -> str:
    import unicodedata
    # Normalize accents: á → a, ñ → n, etc.
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Replace anything not alphanumeric with underscore
    text = re.sub(r"[^a-z0-9]+", "_", text)

    # Remove leading/trailing underscores
    return text.strip("_")

def write_json_manifest(path, product_counter, image_counter, site_name, date):
    """
    Docstring for write_manifest
    
    :param file: Description
    :param product_counter: Description
    :param image_counter: Description
    :param date: Description
    """
    import json
    #Write manifest
    site_name = site_name

    manifest_path = Path(path) / "manifest.json"

    product_manifest = {
        'site_name': site_name,
        'total_products': product_counter,
        'total_images': image_counter,
        'generated_at': date}

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(product_manifest, f, indent=4, ensure_ascii=False)

def download_image_to_product_path(temp_img_path, image_link, max_attempts=2):
    import requests

    # Retry loop to handle transient network or empty-response failures
    for attempt in range(1, max_attempts + 1):
        try:
            # Fetch image as a stream to avoid loading it fully into memory
            resp = requests.get(image_link, timeout=20, stream=True)
        except requests.RequestException:
            # Network error → retry
            continue

        # Only proceed on a successful HTTP response
        if resp.status_code != 200:
            resp.close()
            continue

        # Write response content to a temporary file
        with open(temp_img_path, "wb") as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)

        # Guard against zero-byte downloads
        if temp_img_path.stat().st_size == 0:
            temp_img_path.unlink()
            if attempt == max_attempts:
                # Final attempt failed → propagate failure
                resp.close()
                raise ValueError("Empty file")
            resp.close()
            continue

        # Final filename is derived from the temp file
        final_img_path = temp_img_path.with_suffix(".webp")

        # If image already exists, avoid duplication
        if final_img_path.exists():
            temp_img_path.unlink()
            resp.close()
            return False

        # Atomically promote temp file to final image
        temp_img_path.rename(final_img_path)
        resp.close()
        return True

def stable_image_name(url):
    import hashlib
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

   


        



