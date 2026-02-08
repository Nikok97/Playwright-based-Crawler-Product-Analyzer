import logging

from bs4 import BeautifulSoup
from utilities.utils import now_with_hours

def update_parse_status(row_id: int, db: dict, status: str):
    db["cur"].execute(
        'UPDATE ProductPages SET parse_status = ? WHERE id = ?',
        (status, row_id)
    )
    db["conn"].commit()

def get_fetched_product(db: dict) -> tuple[int, str, str, str] | tuple[None, None, None, None]:

    db["cur"].execute(
        '''
        SELECT id, product_url, product_name, filename
        FROM ProductPages
        WHERE fetch_status = ?
        AND parse_status IS NULL
        ORDER BY id
        LIMIT 1
        ''',
        ('fetched',)
    )
    row = db["cur"].fetchone()
    if row is None:
        return None, None, None, None

    row_id, product_url, product_name, filename = row

    # Lock immediately
    db["cur"].execute(
        'UPDATE ProductPages SET parse_status = ? WHERE id = ?',
        ('parsing', row_id)
    )

    db["conn"].commit()

    return row_id, product_url, product_name, filename

def update_product_data(db: dict, row_id: int, product: dict, date: str) -> bool:
    db["cur"].execute(
        '''
        UPDATE ProductPages
        SET
            product_name = ?,
            currency = ?,
            price = ?,
            product_code = ?,
            reviews = ?,
            images = ?,
            fetched_at = ?
        WHERE id = ?
        ''',
        (
            product["slug"],
            product["currency"],
            product["price"],
            product["product_code"],
            product['reviews'],
            product['images'][0],
            date,
            row_id
        )
    )
    db["conn"].commit()
    return True

    
###################################################

def run_crawler_product_html_parser(
        db: dict, 
        paths_dict: dict, 
        specific_site_config, 
        logger: logging.Logger, 
        error_logger: logging.Logger,
        counter_of_products=1
    ):

    def reset_stuck_parsing_jobs(db: dict):
        db["cur"].execute(
            '''
            UPDATE ProductPages
            SET parse_status = NULL
            WHERE parse_status = "parsing"
            '''
        )
        db["conn"].commit()
    
    # Reset stuck parsing jobs
    reset_stuck_parsing_jobs(db)

    # Main logic
    while True:
        
        row_id = None
        filename = None

        try:
            # Get fetched search result product page
            row_id, _, product_name, filename = get_fetched_product(db)
            if row_id is None:
                break

            # Filepath creation
            file_path = paths_dict['output_dir'] / filename
            if not file_path.exists():
                error_logger.error(f"Missing HTML for id {row_id}")
                update_parse_status(row_id, db, status='parsing_failed')
                continue

            # Soup extraction
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, 'html.parser')
            product = specific_site_config.individual_product_data_extraction(soup)
            if not product:
                update_parse_status(row_id, db, status='parsing_failed')
                continue

            # DB insertion
            try:
                date = now_with_hours()
                update_product_data(db, row_id, product, date)
                update_parse_status(row_id, db, status='parsed_succeeded')
                logger.info(f"Product {counter_of_products} parsed: {product_name}")
                counter_of_products += 1
            except Exception:
                error_logger.error(f"DB update failed for id {row_id}", exc_info=True)
                update_parse_status(row_id, db, status='parsing_failed')

        except Exception:
            error_logger.error(f"Unspecified error for {row_id} ({filename})", exc_info=True)
            if row_id is not None:
                update_parse_status(row_id, db, status='parsing_failed')












