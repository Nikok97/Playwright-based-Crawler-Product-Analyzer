# Playwright-based Crawler & Product Analyzer

A **synchronous web crawler** built with Playwright, designed to fetch e-commerce search result pages, store them locally as HTML, and extract structured product information into a SQLite database.

**Note:** in this version of the program, the code is designed to fetch Amazon's search results webpages.

---

## Features

- **Playwright-based** dynamic crawler (desktop Chrome UA, stealth context and JavaScript capabilities).
- **Config-driven:** loads settings from configurable config.json.
- **Local HTML saving:** stores each page as page.html for easier data extraction.
- **Persistent SQLite integration:** tracks URLs, timestamps, and filenames.
- **Stealth browser context:** spoofed languages, headers, viewport, user agent.
- **Product insertion module:** parses saved HTML, extracts product names/prices/currency and stores data in persistent database.
- **Export program included** to export SQLite database to JSON or CSV.

---

## Result examples

## URLs table

![DB URLs Screenshot](images/URLs.jpg)

*Shows the contents of the Urls table, where each discovered page is stored along with timestamps and filenames of its html file*.

## Example: Products table

![DB products Screenshot](images/Products.jpg)

*Displays the Products table built from exracting product-info (title, currency, and price) from scraped htmls*.

## Examples: JSON export file

![JSON export Screenshot](images/JSON.jpg)

*Shows an example of the JSON export. The file contains structured records for products correlated to their corresponding URLs*.

## Examples: CSV export file

![CSV export Screenshot](images/CSV.jpg)

*Shows the CSV export file generated from the SQLite database. Each row represents a crawled product with its scraped data.*

---

## Requirements

- Python 3.9+
- Playwright
- BeautifulSoup4

---

## Configuration

- Example:

```json
{
    "seed_url": "https://www.amazon.com/s?k=laptop",
    "database_path": "mini.sqlite",
    "start_position": 1,
    "end_position": 11
}
```

- seed_url: Amazon search URL

- crawling_range: Number of pages to scrape

- database_path: SQLite file name (placed inside /data)

---

## Usage

- Crawler usage example:

```python crawler.py```


**Note**: The crawler stores results in mini.sqlite by default. To export to JSON or CSV, run export_utils.py.

---    

## Database schema

- Urls: id, crawled URLs, timestamps, filename of stored html.

- Products: scraped product data (title, currency, price)

---

## Export

- sqlite (default): Results stored in `mini.sqlite`
- JSON / CSV: Run `export_utils.py` to export products from `mini.sqlite` to JSON or CSV.


---

## Logs

- crawler.log: general activity
- crawler_errors.log: errors during crawling

---

## Quick Start

1. Install dependencies: `pip install beautifulsoup4 playwright`
2. To complete Playwright installation, run in terminal: `playwright install`
2. Configure `config.json`.
3. Run the crawler (results stored in mini.sqlite by default): `python crawler.py`
4. (Optional). Export results to JSON (or CSV):
   run `python export_utils.py`

---

## License

This project is licensed under the MIT License – see the LICENSE file for details.

---

## Disclaimer 

This tool is for educational purposes only. Users are responsible for complying with the Terms of Service of any website they crawl, including Amazon.

---

## Contributions & Issues

Feel free to open issues or pull requests!
For major changes, please open an issue first to discuss.

---

## Acknowledgements

- Uses BeautifulSoup and Playwright.

