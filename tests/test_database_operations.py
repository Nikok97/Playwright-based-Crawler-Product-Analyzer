import pytest

from utilities.database import (
    db_initialization,
    db_cur_and_conn_closer,
)

@pytest.fixture
def tmp_db_path(tmp_path):
    return tmp_path / "temp_db.sqlite"

@pytest.fixture
def tmp_db(tmp_db_path):
    db = db_initialization(tmp_db_path)

    yield db

    db_cur_and_conn_closer(db)

@pytest.fixture
def tmp_db_2(tmp_db_path):
    db = db_initialization(tmp_db_path)

    yield db

    db_cur_and_conn_closer(db)

def test_two_workers_race_condition(tmp_db, tmp_db_2):

    product_url = "product_1.com"

    # Arrange: one pending product
    tmp_db["cur"].execute(
        """
        INSERT INTO ProductPages (product_url, fetch_status)
        VALUES (?, ?)
        """,
        (product_url, "pending"),
    )
    tmp_db["conn"].commit()

    # Worker A sees the pending product
    tmp_db["cur"].execute(
        """
        SELECT id, product_url
        FROM ProductPages
        WHERE fetch_status = 'pending'
        LIMIT 1
        """
    )
    row_a = tmp_db["cur"].fetchone()

    # Worker B sees the same pending product
    tmp_db_2["cur"].execute(
        """
        SELECT id, product_url
        FROM ProductPages
        WHERE fetch_status = 'pending'
        LIMIT 1
        """
    )
    row_b = tmp_db_2["cur"].fetchone()

    assert row_a == row_b

    tmp_db["cur"].execute("UPDATE ProductPages SET fetch_status = 'fetching' WHERE product_url = ? AND fetch_status = 'pending'", ("product_1.com",))

    tmp_db["conn"].commit()

    assert tmp_db["cur"].rowcount == 1

    tmp_db_2["cur"].execute("UPDATE ProductPages SET fetch_status = 'fetching' WHERE product_url = ? AND fetch_status = 'pending'", ("product_1.com",))
    
    assert tmp_db_2["cur"].rowcount == 0