import pytest
import sqlite3

from utilities.database import Database

@pytest.fixture
def tmp_db(tmp_path):
        
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()

def test_db_init(tmp_db):

    conn, cur = None, None

    try:
        # Selects all required table names from the master table
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        # Fetches those names from the cursor
        cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        names_of_tables = cur.fetchall()

        # Creates a list of table names
        list_of_tables = []
        for name in names_of_tables:
            # Since the values the cursor returned are tuples with just one value, only the first value is needed
            name_of_table = name[0]
            list_of_tables.append(name_of_table)

        assert 'Urls' in list_of_tables
        assert 'ProductPages' in list_of_tables
        assert 'sqlite_sequence' in list_of_tables

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_insert_url_in_db(tmp_db):
    test_date = "8.7.2026"
    test_url = "www.test.com"

    tmp_db.insert_url(test_url, test_date)

    with sqlite3.connect(tmp_db.path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT url_name, date FROM Urls LIMIT 1")
        row = cur.fetchone()

    assert row == (test_url, test_date)

def test_unique_db_insertion_of_url(tmp_db):

    test_date = '8.7.2026'
    test_url = 'www.test.com'

    tmp_db.insert_url(test_url, test_date)
    tmp_db.insert_url(test_url, test_date)

    conn = sqlite3.connect(tmp_db.path)
    cur = conn.cursor()

    cur.execute('SELECT Count(*) FROM Urls where url_name = ?', (test_url,))

    row = cur.fetchone()
    count = row[0]

    assert count == 1

    cur.close()
    conn.close()

def test_already_pending_or_fetched_url_no_url_in_db(tmp_db):

    test_url = 'www.test.com'

    result = tmp_db.already_pending_or_fetched_url(test_url)

    assert result is False

def test_already_pending_or_fetched_url_returns_true_after_pending_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    tmp_db.insert_url(test_url, test_date)

    tmp_db.update_url_status(test_url, status='pending')

    result = tmp_db.already_pending_or_fetched_url(test_url)

    assert result is True

def test_already_pending_or_fetched_url_returns_false_after_failed_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    tmp_db.insert_url(test_url, test_date)

    tmp_db.update_url_status(test_url, status='failed')

    result = tmp_db.already_pending_or_fetched_url(test_url)

    assert result is False

def test_already_pending_or_fetched_url_returns_true_after_fetched_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    tmp_db.insert_url(test_url, test_date)

    tmp_db.update_url_status(test_url, status='fetched')

    result = tmp_db.already_pending_or_fetched_url(test_url)

    assert result is True









                                                                                                                    





















    
