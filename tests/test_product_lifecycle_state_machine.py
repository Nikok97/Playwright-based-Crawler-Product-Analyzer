import tempfile
from pathlib import Path

from hypothesis.stateful import (
    RuleBasedStateMachine,
    rule,
    precondition,
    invariant,
)

from utilities.database import (
    db_initialization,
    db_cur_and_conn_closer,
    insert_product_url,
)

from crawler.crawler_product_scraper import (
    get_pending_product_url,
    reset_stuck_jobs,
    update_fetch_status_in_product_pages,
)

def read_product_status_from_db(db : dict, product_url: str):

    db['cur'].execute('SELECT fetch_status, parse_status FROM ProductPages WHERE product_url = ?', (product_url,))

    fetch_status, parse_status = db['cur'].fetchone()

    return fetch_status, parse_status

def read_product_status_from_db_failed_cases(db : dict):

    db['cur'].execute('SELECT fetch_status, parse_status FROM ProductPages WHERE product_url is NULL')

    fetch_status, parse_status = db['cur'].fetchone()

    return fetch_status, parse_status


class ProductLifecycleMachine(RuleBasedStateMachine):

    def __init__(self):

        super().__init__()

        self.temp_dir = tempfile.TemporaryDirectory()

        db_path = Path(self.temp_dir.name) / "test.sqlite"

        self.db = db_initialization(db_path) # type: ignore

        self.row_id = None

        self.product = {
            "link": "product_1.com",
        }

        self.expected_state = ("pending", None)

        insert_product_url(self.db, self.product)

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

        row_id, product_url = get_pending_product_url(self.db)

        self.row_id = row_id

        assert row_id is not None
        assert product_url == self.product["link"]

        self.expected_state = ("fetching", None)

    @precondition(
        lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def recover_fetching(self):
        reset_stuck_jobs(self.db)

        self.expected_state = ("pending", None)
        

    @precondition(
        lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def fail_fetching(self):

        update_fetch_status_in_product_pages(
            self.row_id , # type: ignore
            self.db,
            filename='product_1.html',
            status="failed"
        ) 
        self.expected_state = ('failed', None)

    @precondition(
    lambda self: self.expected_state == ("failed", None)
    )

    @rule()
    def failed_is_not_claimable(self):

        row_id, product_url = get_pending_product_url(self.db)

        assert row_id is None
        assert product_url is None

    def teardown(self):
        db_cur_and_conn_closer(self.db)
        self.temp_dir.cleanup()

class ProductLifecycleMachineFailedCases(RuleBasedStateMachine):

    def __init__(self):

        super().__init__()

        self.temp_dir = tempfile.TemporaryDirectory()

        db_path = Path(self.temp_dir.name) / "test.sqlite"

        self.db = db_initialization(db_path) # type: ignore

        self.row_id = None

        self.product = {"link": None}

        self.expected_state = ("pending", None)

        insert_product_url(self.db, self.product)

    @invariant()
    def database_matches_model(self):

        actual_database_state = read_product_status_from_db_failed_cases(
            self.db)
        assert actual_database_state == self.expected_state

    @precondition(lambda self: self.expected_state == ("pending", None)
    )

    @rule()
    def claim_for_fetching(self):

        row_id, product_url = get_pending_product_url(self.db)

        self.row_id = row_id

        assert row_id is not None
        assert product_url == self.product["link"]

        self.expected_state = ("fetching", None)

    @precondition(
    lambda self: self.expected_state == ("fetching", None)
    )

    @rule()
    def update_as_failed_unfetchable(self):

        update_fetch_status_in_product_pages(1, 
        self.db, 
        filename=None, 
        status='failed_unfetchable'
        )

        self.expected_state = ("failed_unfetchable", None)

    @precondition(
    lambda self: self.expected_state == ("failed_unfetchable", None)
    )

    @rule()
    def failed_unfetchable_is_not_claimable(self):

        row_id, product_url = get_pending_product_url(self.db)

        assert row_id is None
        assert product_url is None
    

    def teardown(self):
        db_cur_and_conn_closer(self.db)
        self.temp_dir.cleanup()

#TestProductLifecycleMachine = ProductLifecycleMachine.TestCase

TestProductLifecycleMachineFailedCases = ProductLifecycleMachineFailedCases.TestCase