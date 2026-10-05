import tempfile
import sqlite3
from pathlib import Path

from hypothesis.stateful import (
    RuleBasedStateMachine,
    rule,
    precondition,
    invariant,
)

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


def read_product_status_from_db_failed_cases(db : Database):

    conn, cur = [None] * 2

    try:

        conn = sqlite3.connect(db.path)
        cur = conn.cursor()

        cur.execute('SELECT fetch_status, parse_status FROM ProductPages WHERE product_url is NULL')

        fetch_status, parse_status = cur.fetchone()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return fetch_status, parse_status


class ProductLifecycleMachine(RuleBasedStateMachine):

    def __init__(self):

        super().__init__()

        self.temp_dir = tempfile.TemporaryDirectory()

        db_path = Path(self.temp_dir.name) / "test.sqlite"

        self.db = Database(db_path)

        self.row_id = None

        self.product = {
            "link": "product_1.com",
        }

        self.expected_state = ("pending", None)

        self.db.insert_product_url(self.product)

    @invariant()
    def database_matches_model(self):

        actual_database_state = read_product_status_from_db(
            self.db,
            self.product["link"],
        )

        assert actual_database_state == self.expected_state

    @precondition(
        lambda self: self.expected_state == ("pending", None)
    )

    @rule()
    def claim_for_fetching(self):

        row_id, product_url = self.db.get_pending_product_url()

        self.row_id = row_id

        assert row_id is not None
        assert product_url == self.product["link"]

        self.expected_state = ("fetching", None)

    @precondition(
        lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def recover_fetching(self):
        self.db.reset_stuck_jobs()

        self.expected_state = ("pending", None)
        

    @precondition(
        lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def fail_fetching(self):

        self.db.update_fetch_status_in_product_pages(
            self.row_id , #type: ignore 
            filename='product_1.html',
            status="failed"
        ) 
        self.expected_state = ('failed', None)

    @precondition(
    lambda self: self.expected_state == ("failed", None)
    )

    @rule()
    def failed_is_not_claimable(self):

        row_id, product_url = self.db.get_pending_product_url()

        assert row_id is None
        assert product_url is None

    def teardown(self):
        self.db.close()
        self.temp_dir.cleanup()

class ProductLifecycleMachineFailedCases(RuleBasedStateMachine):

    def __init__(self):

        super().__init__()

        self.temp_dir = tempfile.TemporaryDirectory()

        db_path = Path(self.temp_dir.name) / "test.sqlite"

        self.db = Database(db_path) # type: ignore

        self.row_id = None

        self.product = {"link": None}

        self.expected_state = ("pending", None)

        self.db.insert_product_url(self.product)

    @invariant()
    def database_matches_model(self):

        actual_database_state = read_product_status_from_db_failed_cases(
            self.db)
        assert actual_database_state == self.expected_state

    @precondition(lambda self: self.expected_state == ("pending", None)
    )

    @rule()
    def claim_for_fetching(self):

        row_id, product_url = self.db.get_pending_product_url()

        self.row_id = row_id

        assert row_id is not None
        assert product_url == self.product["link"]

        self.expected_state = ("fetching", None)

    @precondition(
    lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def update_as_failed_unfetchable(self):

        self.db.update_fetch_status_in_product_pages(
        1, 
        filename=None, 
        status='failed_unfetchable'
        )

        self.expected_state = ("failed_unfetchable", None)

    @precondition(
    lambda self: self.expected_state == ("failed_unfetchable", None)
    )

    @rule()
    def failed_unfetchable_is_not_claimable(self):

        row_id, product_url = self.db.get_pending_product_url()

        assert row_id is None
        assert product_url is None
    

    def teardown(self):
        self.db.close()
        self.temp_dir.cleanup()

#TestProductLifecycleMachine = ProductLifecycleMachine.TestCase

TestProductLifecycleMachineFailedCases = ProductLifecycleMachineFailedCases.TestCase