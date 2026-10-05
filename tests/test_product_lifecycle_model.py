import pytest
import sqlite3

from utilities.database import Database

def read_product_status_from_db(db : Database, url: str) -> tuple[str | None, str | None]:

    conn, cur = [None] * 2

    try:

        conn = sqlite3.connect(db.path)
        cur = conn.cursor()

        cur.execute("SELECT fetch_status, parse_status FROM ProductPages where product_url=?", (url,))
        row = cur.fetchone()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return row

@pytest.fixture
def tmp_db(tmp_path):
        
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()


@pytest.fixture
def product_for_testing():
    test_product = {
        'link': 'product_1.com',
        'slug': 'product_1_com',
        'currency': '$',
        "price": 5,
        "product_code": 'TEST_CODE',
        "reviews": "review",
        "images": ["image.com"]
    }
    return test_product

def test_crawler_product_lifecycle_model(tmp_db, product_for_testing):

    """
    Insert the product. The independent model begins as ("pending", None). Read the real row and compare it with the model.
    Insert the product. Compare again.
    Call update_fetch_status_in_product_pages(..., status="fetched"). Update the model to ("fetched", None). Compare again.
    Call get_fetched_product(). Update the model to ("fetched", "parsing"). Compare again.
    Simulate parsing failure with update_parse_status(..., "parsing_failed") and commit. Update the model to ("fetched", "parsing_failed"). Compare one final time.
    """

    # 1. Insert product
    tmp_db.insert_product_url(product_for_testing)

    expected_state = ('pending', None)

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    assert result == expected_state

    # 2.

    tmp_db.get_pending_product_url()

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetching', None)
    
    assert result == expected_state

    # 3.
    tmp_db.update_fetch_status_in_product_pages(1, None, 'fetched')

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', None)

    assert result == expected_state

    # 4.

    tmp_db.get_fetched_product()

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', 'parsing')

    assert result == expected_state


    # 5

    tmp_db.update_parse_status(1, 'parsing_failed')

    result = read_product_status_from_db(tmp_db, 'product_1.com')

    expected_state = ('fetched', 'parsing_failed')

    assert result == expected_state

