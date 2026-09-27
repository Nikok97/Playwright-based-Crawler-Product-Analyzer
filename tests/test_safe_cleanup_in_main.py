import pytest

from utilities.database import (
    db_initialization,
    db_cur_and_conn_closer,
)
from unittest.mock import patch, Mock

from main import run_pipeline, main

@pytest.fixture
def tmp_db(tmp_path):
    # 1. setup
    temp_db_path = tmp_path / "temp_db.sqlite"
    db = db_initialization(temp_db_path)

    # 2. hand the db to the test
    yield db

    # 3. cleanup after the test finishes
    db_cur_and_conn_closer(db)

def test_main_cleans_up_when_run_pipeline_fails(tmp_db):

    #patch db init, replace run pipeline with raising version
    
    with patch("main.interactive_decision_helper"), patch("main.db_initialization") as mock_db, patch("main.run_pipeline") as mock_run_pipeline, patch("main.close_db") as mock_close_db:

        mock_db.return_value = tmp_db

        mock_run_pipeline.side_effect = Exception()
        main()


        mock_close_db.assert_called_once_with(mock_db.return_value)