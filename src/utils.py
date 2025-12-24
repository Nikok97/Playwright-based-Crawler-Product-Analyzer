#Def Now
def now():
    """Return the actual date, hour and timezone."""
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d")

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

def setup_directories():
    import os
    import sys

    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        PARENT_DIR = os.path.dirname(CURRENT_DIR)
        DATA_DIR = os.path.join(BASE_DIR, "data")
        os.makedirs(DATA_DIR, exist_ok=True)
        sys.path.append(PARENT_DIR)
    except Exception as e:
        print(f"Could not create required directories: error {e}")
        sys.exit()

    return BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR

def countdown_sleep_timer(waiting_time):
    import time
    remaining = int(waiting_time)

    while remaining > 0:
        print(f"Waiting… {remaining} seconds remaining".ljust(40), end="\r", flush=True)
        time.sleep(1)
        remaining -= 1
    print() # move to clean line
    print("Waiting… done.            ")





