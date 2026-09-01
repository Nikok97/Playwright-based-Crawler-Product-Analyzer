import logging
import pytest

from utilities.database import db_initialization, insert_url, already_pending_or_fetched_url, update_url_status, db_cur_and_conn_closer

from utilities.utils import now_with_hours

tmp_logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)


def db_insert_paginated_urls(
    db: dict, 
    list_of_urls: list[str], 
    logger: logging.Logger, 
    error_logger: logging.Logger):

    # URL DB inserting
    page_counter = 1
    
    # Main loop
    for i in range(len(list_of_urls)):
            
            # Check if URL has been already fetched
            if already_pending_or_fetched_url(list_of_urls[i], db):

                logger.info(f"Skipping already fetched URL: {list_of_urls[i]}")
                continue

            date = str(now_with_hours())

            try:

                insert_url(list_of_urls[i], db, date)

                logger.info(f"{page_counter}. Inserted URL: {list_of_urls[i]}")

                update_url_status(list_of_urls[i], db, status="pending")

                logger.info(f"{page_counter}. Marked pending status for URL: {list_of_urls[i]}")

                page_counter += 1

            except Exception:

                error_logger.error(f"Failed to insert URL: {list_of_urls[i]} in DB for reason",
                exc_info = True)

                page_counter += 1

def test_db_insert_paginated_urls_inserts_two_urls_and_marks_them_as_pending(tmp_db):

    list_of_urls = [
    'www.eldie.com', 
    'www.mandadosdelanona.com'
    ]
        
    db_insert_paginated_urls(tmp_db, list_of_urls, tmp_logger, error_logger)

    tmp_db["cur"].execute("""
    SELECT url_name, status FROM Urls ORDER BY url_name
    """)

    urls = tmp_db["cur"].fetchall()

    assert urls == [('www.eldie.com', 'pending'),
    ('www.mandadosdelanona.com', 'pending'),              
    ]

def test_db_already_contains_url_marked_as_pending(tmp_db):

    test_url = "www.eldie.com"
    date = "14.7.2026"
    
    insert_url(test_url, tmp_db, date)

    update_url_status(test_url, tmp_db, status='pending')

    list_of_urls = [
    "www.eldie.com", 
    "www.mandadosdelanona.com"
    ]

    db_insert_paginated_urls(tmp_db, list_of_urls, tmp_logger, error_logger)

    tmp_db["cur"].execute("""
    SELECT url_name, status FROM Urls ORDER BY url_name
    """)

    urls = tmp_db["cur"].fetchall()

    assert urls == [("www.eldie.com", "pending"),
    ("www.mandadosdelanona.com", "pending"),              
    ]
    
def test_db_already_contains_url_marked_as_fetched(tmp_db):

    test_url = "www.eldie.com"
    date = "14.7.2026"
    
    insert_url(test_url, tmp_db, date)

    update_url_status(test_url, tmp_db, status='fetched')

    list_of_urls = [
    "www.eldie.com", 
    "www.mandadosdelanona.com"
    ]

    db_insert_paginated_urls(tmp_db, list_of_urls, tmp_logger, error_logger)

    tmp_db["cur"].execute("""
    SELECT url_name, status FROM Urls ORDER BY url_name
    """)

    urls = tmp_db["cur"].fetchall()

    assert urls == [("www.eldie.com", "fetched"),
    ("www.mandadosdelanona.com", "pending"),              
    ]


def test_db_already_contains_url_marked_as_failed(tmp_db):

    """
    Given a failed URL already in the DB,
    when db_insert_paginated_urls() sees it again,
    then its status should become pending.     
    """

    url = 'www.eldie.com'
    list_of_urls = ['www.eldie.com']

    insert_url(url, tmp_db, date='5/7/27')

    update_url_status(url, tmp_db, status='failed')

    db_insert_paginated_urls(tmp_db, list_of_urls, tmp_logger, error_logger)

    tmp_db["cur"].execute("SELECT url_name, status FROM Urls ORDER BY url_name")

    result = tmp_db["cur"].fetchall()

    assert result == [('www.eldie.com', 'pending')]



    


    





