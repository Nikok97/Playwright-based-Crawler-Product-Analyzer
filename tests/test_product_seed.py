import logging
import pytest
import sqlite3

from crawler.crawler_seed import db_insert_paginated_urls
from utilities.database import Database
from utilities.utils import now_with_hours

tmp_logger = logging.getLogger("test_logger")
error_logger = logging.getLogger("test_error_logger")


@pytest.fixture
def tmp_db(tmp_path):

    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = Database(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db.close()


def test_db_insert_paginated_urls_inserts_two_urls_and_marks_them_as_pending(tmp_db):

    list_of_urls = [
        "www.eldie.com",
        "www.mandadosdelanona.com"
    ]

    db_insert_paginated_urls(
        tmp_db,
        list_of_urls,
        tmp_logger,
        error_logger
    )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("""
            SELECT url_name, status
            FROM Urls
            ORDER BY url_name
        """)

        urls = cur.fetchall()

        assert urls == [
            ("www.eldie.com", "pending"),
            ("www.mandadosdelanona.com", "pending"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_db_already_contains_url_marked_as_pending(tmp_db):

    test_url = "www.eldie.com"
    date = "14.7.2026"

    tmp_db.insert_url(test_url, date)
    tmp_db.update_url_status(test_url, status="pending")

    list_of_urls = [
        "www.eldie.com",
        "www.mandadosdelanona.com"
    ]

    db_insert_paginated_urls(
        tmp_db,
        list_of_urls,
        tmp_logger,
        error_logger
    )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("""
            SELECT url_name, status
            FROM Urls
            ORDER BY url_name
        """)

        urls = cur.fetchall()

        assert urls == [
            ("www.eldie.com", "pending"),
            ("www.mandadosdelanona.com", "pending"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_db_already_contains_url_marked_as_fetched(tmp_db):

    test_url = "www.eldie.com"
    date = "14.7.2026"

    tmp_db.insert_url(test_url, date)
    tmp_db.update_url_status(test_url, status="fetched")

    list_of_urls = [
        "www.eldie.com",
        "www.mandadosdelanona.com"
    ]

    db_insert_paginated_urls(
        tmp_db,
        list_of_urls,
        tmp_logger,
        error_logger
    )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("""
            SELECT url_name, status
            FROM Urls
            ORDER BY url_name
        """)

        urls = cur.fetchall()

        assert urls == [
            ("www.eldie.com", "fetched"),
            ("www.mandadosdelanona.com", "pending"),
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_db_already_contains_url_marked_as_failed(tmp_db):

    """
    Given a failed URL already in the DB,
    when db_insert_paginated_urls() sees it again,
    then its status should become pending.
    """

    url = "www.eldie.com"
    list_of_urls = ["www.eldie.com"]

    tmp_db.insert_url(url, date="5/7/27")
    tmp_db.update_url_status(url, status="failed")

    db_insert_paginated_urls(
        tmp_db,
        list_of_urls,
        tmp_logger,
        error_logger
    )

    conn, cur = None, None

    try:
        conn = sqlite3.connect(tmp_db.path)
        cur = conn.cursor()

        cur.execute("""
            SELECT url_name, status
            FROM Urls
            ORDER BY url_name
        """)

        result = cur.fetchall()

        assert result == [
            ("www.eldie.com", "pending")
        ]

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()