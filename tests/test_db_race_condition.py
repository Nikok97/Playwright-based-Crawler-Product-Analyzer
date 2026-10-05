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

@pytest.fixture
def tmp_db_2(tmp_db_path):

    db = Database(tmp_db_path)

    yield db

    db.close()

def test_two_workers_race_condition(tmp_db):

    product_url = "product_1.com"

    conn1, cur1, conn2, cur2 = [None] * 4

    try:

        conn1 = sqlite3.connect(tmp_db.path)
        cur1 = conn1.cursor()

        conn2 = sqlite3.connect(tmp_db.path)
        cur2 = conn2.cursor()

        # Arrange: one pending product
        cur1.execute(
            """
            INSERT INTO ProductPages (product_url, fetch_status)
            VALUES (?, ?)
            """,
            (product_url, "pending"),
        )
        conn1.commit()

        # Worker A sees the pending product
        cur1.execute(
            """
            SELECT id, product_url
            FROM ProductPages
            WHERE fetch_status = 'pending'
            LIMIT 1
            """
        )
        row_a = cur1.fetchone()

        # Worker B sees the same pending product
        cur2.execute(
            """
            SELECT id, product_url
            FROM ProductPages
            WHERE fetch_status = 'pending'
            LIMIT 1
            """
        )
        row_b = cur2.fetchone()

        assert row_a == row_b

        cur1.execute("UPDATE ProductPages SET fetch_status = 'fetching' WHERE product_url = ? AND fetch_status = 'pending'", ("product_1.com",))

        conn1.commit()

        assert cur1.rowcount == 1

        cur2.execute("UPDATE ProductPages SET fetch_status = 'fetching' WHERE product_url = ? AND fetch_status = 'pending'", ("product_1.com",))
        
        assert cur2.rowcount == 0

    finally:

        pass