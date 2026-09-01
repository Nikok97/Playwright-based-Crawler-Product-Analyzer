import pytest

from utilities.database import db_initialization, insert_url, already_pending_or_fetched_url, update_url_status, db_cur_and_conn_closer
from utilities.utils import now_with_hours

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)

def test_db_init(tmp_db):

    # Selects all required table names from the master table
    tmp_db["cur"].execute('''
        SELECT name from sqlite_master where type = 'table'
    ''')

    # Fetches those names from the cursor
    names_of_tables = tmp_db["cur"].fetchall()

    # Creates a list of table names
    list_of_tables = []
    for name in names_of_tables:
        # Since the values the cursor returned are tuples with just one value, only the first value is needed
        name_of_table = name[0]
        list_of_tables.append(name_of_table)

    assert 'Urls' in list_of_tables
    assert 'ProductPages' in list_of_tables
    assert 'sqlite_sequence' in list_of_tables

def test_insert_url_in_db(tmp_db):

    test_date = '8.7.2026'
    test_url = 'www.test.com'

    insert_url(test_url, tmp_db, test_date)

    tmp_db["cur"].execute('''
    SELECT url_name, date from Urls LIMIT 1
    ''')

    row = tmp_db["cur"].fetchone()

    assert row == (test_url, test_date)

def test_unique_db_insertion_of_url(tmp_db):

    test_date = '8.7.2026'
    test_url = 'www.test.com'

    insert_url(test_url, tmp_db, test_date)
    insert_url(test_url, tmp_db, test_date)

    tmp_db["cur"].execute('SELECT Count(*) FROM Urls where url_name = ?', (test_url,))

    row = tmp_db['cur'].fetchone()
    count = row[0]

    assert count == 1

def test_already_pending_or_fetched_url_no_url_in_db(tmp_db):

    test_url = 'www.test.com'

    result = already_pending_or_fetched_url(test_url, tmp_db)

    assert result is False

def test_already_pending_or_fetched_url_returns_true_after_pending_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    insert_url(test_url, tmp_db, test_date)

    update_url_status(test_url, tmp_db, status='pending')

    result = already_pending_or_fetched_url(test_url, tmp_db)

    assert result is True

def test_already_pending_or_fetched_url_returns_false_after_failed_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    insert_url(test_url, tmp_db, test_date)

    update_url_status(test_url, tmp_db, status='failed')

    result = already_pending_or_fetched_url(test_url, tmp_db)

    assert result is False

def test_already_pending_or_fetched_url_returns_false_after_fetched_status(tmp_db):
    
    test_url = 'www.test.com'
    test_date = '8/7/2026'

    insert_url(test_url, tmp_db, test_date)

    update_url_status(test_url, tmp_db, status='fetched')

    result = already_pending_or_fetched_url(test_url, tmp_db)

    assert result is True









                                                                                                                    





















    
