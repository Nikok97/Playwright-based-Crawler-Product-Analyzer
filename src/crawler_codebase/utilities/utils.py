import time
import random
import re
import sys
import logging
import unicodedata

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Page
from pathlib import Path
from utilities.stealth import human_scroll

#Def Now
def now_with_hours() -> str:
    """
    Returns the actual date and hour in string format.
    """
    from datetime import datetime   
    return datetime.now().strftime("%Y-%m-%d, %H:%M hs.")

def setup_loggers() -> tuple[logging.Logger, logging.Logger]:
    """
    Sets up a general logger and an error logger, with corresponding handlers and levels.
    """
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

#Logging setup
logger, error_logger = setup_loggers()

def setup_directories_pathlib() -> dict:
    """
    Sets up directories using Pathlib.
    """
    try:
        SCRIPT_PATH = Path(__file__).resolve()
        CURRENT_DIR = SCRIPT_PATH.parent.parent.parent
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

def countdown_sleep_timer(waiting_time: float):
    remaining = int(waiting_time)

    while remaining > 0:
        print(f"Waiting… {remaining} seconds remaining".ljust(40), end="\r", flush=True)
        time.sleep(1)
        remaining -= 1
    print() # move to clean line
    print("Waiting… done.            ")

def load_page(page: Page, url: str, wait_selector: str, max_attempts: int=2) -> bool:
    """
    Tries to load the URL and waits for the required selector.
    Returns True if the page is ready for processing.
    """
    #Navigation block
    success = False
    for attempt in range(1, max_attempts + 3):
        try:
            #1st try
            if attempt == 1:
                page.goto(url, timeout=30000)
            #2nd (or n) retries
            else:
                time.sleep(random.uniform(15, 25))
                page.reload(timeout=30000)
            #Page loaded, wait for selector
            page.wait_for_selector(wait_selector, timeout=8000)
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
    
def perform_scroll(page: Page, url: str) -> bool:
    """
    Scrolls the page to trigger JS loading.
    Returns False if scrolling fails or times out.
    """
    try:
        print(f"Scrolling for {url}")
        human_scroll(page, min_increment=200, max_increment=450,  timeout=15.0)
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
    
def extract_html(page: Page, url: str) -> str | None:
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

def process_single_url(page: Page, url: str, logger: logging.Logger, wait_selector: str) -> str | bool:
    #Navigation phase
    if not load_page(page, url, wait_selector, max_attempts=2):
        return False
    logger.info(f"Target JavaScript selector detected in URL: {url}")

    #Scrolling phase
    if not perform_scroll(page, url):
        return False

    #Extra delay to let JS finish loading
    time.sleep(random.uniform(3, 5))

    #HTML extraction phase
    html = extract_html(page, url)
    if html is None:
        return False

    return html

def write_html(output_directory: Path, filename: str, html: str) -> bool:
    """
    Writes HTML to disk.
    """

    output_path = output_directory / filename
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)
        tmp_path.replace(output_path)
        return True
    except Exception:
        error_logger.error(
            f"HTML writing error for {filename}",
            exc_info=True
        )
        return False
    
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

def slugify(text: str) -> str:
    # Normalize accents: á → a, ñ → n, etc.
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Replace anything not alphanumeric with underscore
    text = re.sub(r"[^a-z0-9]+", "_", text)

    # Remove leading/trailing underscores
    return text.strip("_")

def interactive_decision_helper(STAGES: dict):

    # Ask user for decision
    decision = input("Input 1 to run the whole program, 2 to select individual parts, or 0 to exit: ")

    if decision != '1' and decision != '2' and decision != '0':
        print('Value not valid. Exiting program')
        raise ValueError
    
    elif decision == '0':
        print('Exiting program')
        sys.exit()

    elif decision == '2':
        run_crawler_seed_decision = input('Input 0 to skip Crawler_seed for this run, else press enter: ')
        if run_crawler_seed_decision == '0':
            STAGES['seed'] = False

        run_crawler_search_scraper_decision = input('Input 0 to skip crawler_search_scraper for this run, else press enter: ')
        if run_crawler_search_scraper_decision == '0':
            STAGES["search_scraper"] = False

        run_crawler_search_html_parser_decision = input('Input 0 to skip crawler_search_html_parser for this run, else press enter: ')
        if run_crawler_search_html_parser_decision == '0':
            STAGES["search_parser"] = False

        run_crawler_product_scraper_decision = input('Input 0 to skip crawler_product_scraper for this run, else press enter: ')
        if run_crawler_product_scraper_decision == '0':
            STAGES["product_scraper"] = False

        run_crawler_product_html_parser_decision = input('Input 0 to skip crawler_product_html_parser for this run, else press enter: ')
        if run_crawler_product_html_parser_decision == '0':
            STAGES["product_parser"] = False

        