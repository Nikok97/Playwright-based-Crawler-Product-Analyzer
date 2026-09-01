# Playwright-based Crawler & Product Analyzer

A synchronous, stage-based web crawler built with **Python, Playwright, BeautifulSoup, and SQLite**.

The project separates web fetching from HTML parsing and persists crawl state in SQLite, allowing interrupted work to be recovered and later stages to be run independently.

The current end-to-end reference implementation targets **BooksToScrape**. The codebase also contains partial/experimental adapters for **Amazon** and **MercadoLibre**.

---

## Overview

The crawler follows a five-stage pipeline:

```text
Seed
  ↓
Search Scraper
  ↓
Search HTML Parser
  ↓
Product Scraper
  ↓
Product HTML Parser
```

At a high level, it:

1. generates search-result URLs;
2. downloads and stores search-result HTML;
3. parses that HTML to discover individual product URLs;
4. downloads and stores individual product pages;
5. parses product HTML and persists structured product data.

The stages share a `CrawlerContext` containing the database connection, directory paths, active site adapter, configuration values, and loggers.

---

## Features

- Five-stage crawling pipeline coordinated by `main.py`
- Selective stage execution from an interactive CLI
- Playwright-based browser automation
- BeautifulSoup-based offline HTML parsing
- SQLite persistence for URLs, product data, and processing state
- Recovery of jobs interrupted while fetching or parsing
- Local persistence of downloaded HTML
- Atomic HTML writes using temporary files
- Product HTML archiving after successful parsing
- Site-specific adapters separated from the generic pipeline
- Normal and error logging
- Automated pytest coverage for pipeline, scraper, parser, database, and recovery behavior

---

## Current site support

### BooksToScrape

`bookstoscrape` is the current end-to-end reference adapter and the default configuration.

It supports:

- algorithmic search-page pagination;
- search-result page scraping;
- product URL extraction;
- product page scraping;
- individual product parsing.

### Amazon

The repository contains Amazon-specific search-result selectors, pagination logic, and price extraction helpers.

The Amazon adapter is currently **partial** and is not wired for the complete five-stage product pipeline.

### MercadoLibre

The repository contains MercadoLibre search-page pagination and parsing logic, together with individual-product extraction code.

The MercadoLibre adapter is currently **experimental/partial** and is not the reference implementation for the full pipeline.

---

## Project structure

```text
.
├── config.json
├── LICENSE.md
├── pytest.ini
├── requirements.txt
├── README.md
├── src/
│   └── crawler_codebase/
│       ├── __init__.py
│       ├── main.py
│       ├── crawler/
│       │   ├── __init__.py
│       │   ├── crawler_context.py
│       │   ├── crawler_seed.py
│       │   ├── crawler_search_scraper.py
│       │   ├── crawler_search_html_parser.py
│       │   ├── crawler_product_scraper.py
│       │   └── crawler_product_html_parser.py
│       └── utilities/
│           ├── __init__.py
│           ├── database.py
│           ├── specific_sites.py
│           ├── stealth.py
│           └── utils.py
├── tests/
│   └── test_pipeline.py
└── dynamic_crawler_tests/
    ├── test_product_html_parser.py
    ├── test_product_scraper.py
    ├── test_product_seed.py
    ├── test_search_scraper.py
    └── beginner_tests/
```

Runtime directories such as `data/` and `data/output/` are created automatically.

---

## Pipeline stages

### 1. Seed

Implemented in:

```text
src/crawler_codebase/crawler/crawler_seed.py
```

The seed stage:

- reads the active site's pagination mode;
- generates the configured number of search-result URLs;
- supports both algorithmic and dynamic pagination strategies;
- inserts search URLs into SQLite;
- marks URLs that should be processed as `pending`.

The current pagination modes are:

```text
algorithmic
dynamic
```

---

### 2. Search Scraper

Implemented in:

```text
src/crawler_codebase/crawler/crawler_search_scraper.py
```

The search scraper:

- retrieves a `pending` search URL;
- marks it as `in_progress`;
- loads the page with Playwright;
- waits for a site-specific selector;
- scrolls the page;
- extracts the rendered HTML;
- saves the HTML locally;
- records the filename in SQLite;
- marks the URL as `fetched` or `failed`.

Search-page HTML is stored using names such as:

```text
data/page_<url_id>.html
```

Before processing begins, search jobs left in `in_progress` by an interrupted execution are returned to a retryable state.

---

### 3. Search HTML Parser

Implemented in:

```text
src/crawler_codebase/crawler/crawler_search_html_parser.py
```

This stage works from the HTML already stored on disk.

It:

- finds files matching `page_<id>.html`;
- parses them with BeautifulSoup;
- calls the active site's `product_extraction()` method;
- extracts product URLs;
- inserts discovered products into the `ProductPages` table.

New product URLs are inserted with:

```text
fetch_status = pending
```

`ProductPages.product_url` is unique, and insertion currently uses SQLite `INSERT OR IGNORE`.

---

### 4. Product Scraper

Implemented in:

```text
src/crawler_codebase/crawler/crawler_product_scraper.py
```

The product scraper:

- selects one product whose `fetch_status` is `pending`;
- immediately marks it `fetching`;
- opens the product URL with Playwright;
- waits for the site's product-page selector;
- retrieves the page HTML;
- writes it to `data/output/`;
- stores the generated filename;
- marks successful jobs as `fetched`.

Typical product-fetch states include:

```text
pending
fetching
fetched
failed
failed_unfetchable
```

Rows left in `fetching` after an interrupted execution are reset to `pending` before processing resumes.

A keyboard interruption also returns the currently selected product to `pending`.

---

### 5. Product HTML Parser

Implemented in:

```text
src/crawler_codebase/crawler/crawler_product_html_parser.py
```

This stage selects products where:

```text
fetch_status = fetched
parse_status IS NULL
```

Before parsing, the row is locked with:

```text
parse_status = parsing
```

The parser then:

- opens the locally saved product HTML;
- parses it with BeautifulSoup;
- delegates extraction to the site's `individual_product_data_extraction()` method;
- updates the structured product fields in SQLite;
- marks successful rows as `parsed_succeeded`.

Parsing failures are marked:

```text
parsing_failed
```

Rows left in `parsing` by interrupted executions are reset before the stage starts.

After successful parsing, the product HTML is archived under a date-based directory:

```text
data/output/parse_YYYY-MM-DD/
```

An archive error is logged independently from the database update.

---

## Database

The project uses SQLite for both crawl state and product data.

The database is initialized in:

```text
src/crawler_codebase/utilities/database.py
```

### `Urls`

Stores search-result URLs and their current processing state.

```text
id
url_name
date
filename
status
```

Important constraints:

```text
url_name  UNIQUE
filename  UNIQUE
```

Typical states include:

```text
pending
in_progress
fetched
failed
```

### `ProductPages`

Stores individual product URLs, processing state, and parsed product information.

```text
id
product_url
product_code
product_name
price
currency
description
fetch_status
parse_status
condition
seller
reviews
images
fetched_at
filename
```

Important constraint:

```text
product_url UNIQUE
```

The same table therefore acts as both a product-processing queue and the final storage location for parsed product data.

---

## Recovery and resumability

The pipeline stores its state in SQLite instead of relying only on in-memory progress.

Recovery logic includes transitions such as:

```text
search URL:
in_progress → pending

product fetch:
fetching → pending

product parse:
parsing → NULL
```

This allows work interrupted during temporary processing states to be selected again on a later run.

Fetching and parsing remain separate stages, so downloaded HTML can also be processed independently of browser access.

---

## Site adapters

Site-specific behavior is defined in:

```text
src/crawler_codebase/utilities/specific_sites.py
```

The registry currently exposes:

```text
bookstoscrape
amazon
mercadolibre
```

Adapters can define behavior including:

- seed URLs;
- pagination mode;
- pagination URL construction;
- dynamic pagination discovery;
- selectors used by Playwright;
- search-result product extraction;
- individual-product data extraction.

The intent is to keep site-specific HTML knowledge outside the generic crawler stages.

---

## Browser behavior

The crawler uses Playwright's synchronous API and currently launches Chromium in visible mode:

```python
headless=False
```

Browser-context setup includes randomized desktop-oriented values such as:

- user agent;
- viewport dimensions;
- device scale factor;
- language and headers.

The project also applies basic webdriver masking and scrolling behavior before HTML extraction.

---

## Configuration

The current `config.json` is:

```json
{
  "site": "bookstoscrape",
  "database_path": "db.sqlite",
  "pages_to_crawl": 1
}
```

### `site`

Selects an adapter registered in `site_registry()`.

For the complete current pipeline, use:

```text
bookstoscrape
```

### `database_path`

Sets the SQLite filename.

The database is created inside the runtime `data/` directory.

### `pages_to_crawl`

Controls how many paginated search-result URLs the seed stage generates.

---

## Installation

Python **3.10+** is recommended because the codebase uses modern type-union syntax such as:

```python
str | None
```

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd Playwright-based-Crawler-Product-Analyzer
```

Create and activate a virtual environment if desired, then install runtime dependencies:

```bash
pip install -r requirements.txt
```

Install the Playwright Chromium browser:

```bash
playwright install chromium
```

For development and tests, install pytest:

```bash
pip install pytest
```

---

## Usage

From the repository root:

```bash
python src/crawler_codebase/main.py
```

The program starts with an interactive decision:

```text
Input 1 to run the whole program,
2 to select individual parts,
or 0 to exit
```

### Run the complete pipeline

Enter:

```text
1
```

The five stages run in order.

### Run selected stages

Enter:

```text
2
```

You can then skip individual stages for that execution.

This is useful when, for example:

- search HTML is already present;
- product pages have already been downloaded;
- only parsing needs to be repeated;
- persistent SQLite state should be reused.

---

## Generated runtime files

### Search-result HTML

```text
data/page_<url_id>.html
```

### Product HTML

```text
data/output/product_<n>.html
```

### Parsed product HTML archive

```text
data/output/parse_YYYY-MM-DD/
```

### SQLite database

```text
data/<database_path>
```

### Logs

```text
crawler.log
crawler_errors.log
```

Runtime data, local databases, logs, cache files, and generated HTML should normally remain outside version control.

---

## Testing

The project uses pytest.

Run the full suite from the repository root:

```bash
pytest
```

The current test suite covers areas including:

- pipeline ordering;
- selective stage execution;
- shared crawler context;
- seed and pagination behavior;
- search scraping;
- search-job recovery;
- product scraping;
- product-fetch states;
- product HTML parsing;
- parse-job recovery;
- SQLite updates and transactions;
- rollback behavior;
- file handling and archiving;
- parsing helpers and utilities.

The codebase is intentionally structured so that much of the crawler behavior can be tested with local HTML, temporary SQLite databases, and mocked browser interactions rather than requiring live network requests.

---

## Design rationale

The crawler deliberately separates fetching from parsing.

Instead of extracting all product data while the browser is open, pages are first persisted as HTML and later parsed in dedicated stages.

This provides several advantages:

- parsing logic can be tested without network access;
- fetched pages remain available for inspection;
- scraper and parser failures can be tracked independently;
- browser work and parsing work can be resumed separately;
- persistent queue state survives process interruptions;
- site-specific extraction logic stays isolated from the orchestration layer.

The codebase is primarily an educational project and continues to evolve.

---

## License

This project is licensed under the MIT License. See `LICENSE.md`.

---

## Disclaimer

This project is intended for educational and experimental purposes.

Users are responsible for complying with the terms of service, robots policies, rate limits, and applicable rules of any website they access with the crawler.

---

## Contributions

Issues and pull requests are welcome.

For substantial changes, opening an issue first is recommended.
