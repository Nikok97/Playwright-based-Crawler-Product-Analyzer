from main import run_pipeline, CrawlerContext
from unittest.mock import patch, Mock
import pytest

shared_state = list()
received_contexts = list()

fake_context = Mock()

class SeedStage:
    key = "seed"
    display_name = "Crawler seed"
    run_flag = False
    def run(self, context):
        
        self.run_flag = True
        shared_state.append(self.key)
        received_contexts.append(context)

class SearchScraperStage:
    key = "search_scraper"
    display_name = "search_scraper"
    run_flag = False
    def run(self, context):
        self.run_flag = True
        shared_state.append(self.key)
        received_contexts.append(context)
        
class SearchParserStage:
    key = "search_parser"
    display_name = "search_parser"
    run_flag = False
    def run(self, context):
        
        self.run_flag = True
        shared_state.append(self.key)
        received_contexts.append(context)

class ProductScraperStage:
    key = "product_scraper"
    display_name = "product_scraper"
    run_flag = False
    def run(self, context):
        
        self.run_flag = True
        shared_state.append(self.key)
        received_contexts.append(context)

class ProductParserStage:
    key = "product_parser"
    display_name = "product_parser"
    run_flag = False
    def run(self, context):
        
        self.run_flag = True
        shared_state.append(self.key)
        received_contexts.append(context)

def fake_get_stage_pipeline() -> list:
    # Returns the stage pipeline composed of the stage objects
    return [
        SeedStage(),
        SearchScraperStage(),
        SearchParserStage(),
        ProductScraperStage(),
        ProductParserStage(),
    ]

def get_default_stages():
    # Returns the stages with the default value True to run the whole program as default setting
    
    stages = {
        "seed": True,
        "search_scraper": True,
        "search_parser": True,
        "product_scraper": True,
        "product_parser": True,
    }
    return stages


def test_run_pipeline_all_enabled():

    shared_state.clear()

    with patch('main.CrawlerContext') as mock_context: run_pipeline(
        get_default_stages(), fake_get_stage_pipeline(), mock_context )

    # Assert that run pipeline has run the stage in a certain order
    assert shared_state == ['seed',
    'search_scraper',
    'search_parser',
    'product_scraper',
    'product_parser']

def test_run_pipeline_only_product_parser_enabled():
    shared_state.clear()

    stages = {
        "seed": False,
        "search_scraper": False,
        "search_parser": False,
        "product_scraper": False,
        "product_parser": True,
    }

    run_pipeline(
    stages, fake_get_stage_pipeline(), fake_context )

    assert shared_state == ['product_parser']

def test_run_pipeline_same_context_object_is_passed():

    shared_state.clear()
    received_contexts.clear()

    run_pipeline(
    get_default_stages(), fake_get_stage_pipeline(), fake_context )

    # Assert that run pipeline has run the stage in a certain order
    assert shared_state == ['seed',
    'search_scraper',
    'search_parser',
    'product_scraper',
    'product_parser']

    # Assert they all have received the same context object
    def check_contexts(fake_context) -> bool:

        if len(received_contexts) != 5:
                
                return False

        for context in received_contexts:

            if context is not fake_context:
                return False
            
        return True

    result = check_contexts(fake_context)

    assert result is True


def test_run_pipeline_a_stage_fails_exception_stops_execution():

    shared_state.clear()

    received_contexts.clear()

    fake_search_scraper = Mock()
    fake_search_scraper.key = 'search_scraper'
    fake_search_scraper.display_name = "search_scraper"

    fake_search_scraper.run.side_effect = RuntimeError()

    def fake_get_stage_pipeline() -> list:
        # Returns the stage pipeline composed of the stage objects
        return [
            SeedStage(),
            fake_search_scraper,
            SearchParserStage(),
            ProductScraperStage(),
            ProductParserStage(),
        ]


    with pytest.raises(RuntimeError):

        run_pipeline(
        get_default_stages(), fake_get_stage_pipeline(), fake_context )

    # Assert that run pipeline has run the stage in a certain order
    assert shared_state == ['seed']

    fake_search_scraper.run.assert_called_once_with(fake_context)
















