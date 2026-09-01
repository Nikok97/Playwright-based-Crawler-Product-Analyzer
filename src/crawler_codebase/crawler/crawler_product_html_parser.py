import logging

from bs4 import BeautifulSoup
from pathlib import Path
from utilities.utils import now_with_hours

def create_folder_with_date_of_parse_in_output_dir(paths_dict) -> Path:
    #Create folder with the date of the parse in data/output dir
    date_for_archiving = now_with_hours()[0:10]
    html_archiving_folder : Path = paths_dict['output_dir'] / f'parse_{date_for_archiving}'
    html_archiving_folder.mkdir(parents=True, exist_ok=True)

    return html_archiving_folder

def update_parse_status(row_id: int, db: dict, status: str):
    """
    Updates parse status of a product page in the DB with parameter status.
    """
    db["cur"].execute(
        'UPDATE ProductPages SET parse_status = ? WHERE id = ?',
        (status, row_id)
    )

def get_fetched_product(db: dict) -> tuple[int, str, str, str] | tuple[None, None, None, None]:
    """
    Gets 1 product webpage (id, product_url) from ProductPages table that has been fetched, but not parsed.
    """
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
    #print(row)
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
    return True


def reset_stuck_parsing_jobs(db: dict):
    db["cur"].execute(
        '''
        UPDATE ProductPages
        SET parse_status = NULL
        WHERE parse_status = "parsing"
        '''
    )
    db["conn"].commit()

    
###################################################

def run_crawler_product_html_parser(
        db: dict,
        specific_site_config,
        paths_dict: dict, 
        logger: logging.Logger, 
        error_logger: logging.Logger,
        counter_of_products=1
    ):

    # Reset stuck parsing jobs
    reset_stuck_parsing_jobs(db)

    # Main logic
    while True:
        
        row_id = None
        filename = None

        #Create folder with the date of the parse in data/output dir
        html_archiving_folder = create_folder_with_date_of_parse_in_output_dir(paths_dict)

        # Get fetched search result product page
        row_id, _, product_name, filename = get_fetched_product(db)

        if row_id is None:

            print("No more products to parse")
            break

        # Initialize file_path with the path of the scraped html page
        file_path = paths_dict['output_dir'] / filename

        if not file_path.exists():

            error_logger.error(f"Missing HTML for id {row_id}")
            update_parse_status(row_id, db, status='parsing_failed')

            db["conn"].commit()
            
            continue

        # Extract Soup
        with open(file_path, "r", encoding="utf-8") as f:

            soup = BeautifulSoup(f, 'html.parser')

        # Individual product data extraction
        product = specific_site_config.individual_product_data_extraction(soup)

        if not product:

            update_parse_status(row_id, db, status='parsing_failed')

            db["conn"].commit()

            continue

        # Else, if product, go on to DB insertion

        try:

            date = now_with_hours()

            update_product_data(db, row_id, product, date)

            update_parse_status(row_id, db, status='parsed_succeeded')

            db["conn"].commit()

            logger.info(f"Product {counter_of_products} parsed: {product_name}")

            counter_of_products += 1

            try:
            #Move html to a folder with the date of the parse for better organization. This renames the reference of the OS to the html to the new archiving_folder path.
                file_path.rename(html_archiving_folder / file_path.name)
            
            except Exception as error:
                error_logger.error(f"Error in archiving HTML file: {error}")


        except Exception:

            db['conn'].rollback()

            error_logger.error(f"DB update failed for id {row_id}", exc_info=True)

            update_parse_status(row_id, db, status='parsing_failed')

            db["conn"].commit()












