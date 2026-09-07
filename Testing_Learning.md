PYTHON TESTING REVIEW
Based on the dynamic_crawler test suite
Technical consolidation notes

**============================================================**
1. PURPOSE OF THESE NOTES
**============================================================**

These notes summarize the testing concepts practiced in the crawler project and
connect each concept to concrete tests in the current tests folder.

The goal is to develop a method for deciding:

- what a function is responsible for;
- what result or state the rest of the program depends on;
- which dependencies make the function difficult to test directly;
- what evidence would prove that the function fulfilled its contract.

A useful framework is:

    - Responsibility:
    - Contract:
    - Dependencies:
    - Evidence that the contract was fulfilled:

This can be applied before writing any test.

**============================================================**
2. THE BASIC MENTAL MODEL OF A TEST
**============================================================**

A test constructs a controlled situation, runs one piece of behavior, and
checks evidence.

A practical structure is:

    Arrange:
        Build the input, fake objects, database, files, or mock behavior.

    Act:
        Call the function being tested.

    Assert:
        Check the result, changed state, generated file, database row, or
        interaction with a dependency.

Example from extract_html():

    Arrange:
        fake_page.content.return_value = "<html>test</html>"

    Act:
        result = extract_html(fake_page, url)

    Assert:
        fake_page.content.assert_called_once()
        assert result == "<html>test</html>"

There are two broad kinds of evidence in the current suite:

1. Outcome or state evidence

   Examples:
   - a function returns True, False, None, a string, a dictionary, or a list;
   - a file exists and contains the expected text;
   - a database row has the expected filename or status.

2. Interaction evidence

   Examples:
   - goto() was called once;
   - reload() was not called;
   - wait_for_selector() was called twice;
   - human_scroll() was called once.

Outcome evidence asks:

    What result did the program produce?

Interaction evidence asks:

    Did the function use its collaborators correctly?


**============================================================**
3. TESTING CONTRACTS RATHER THAN INTERNAL STEPS
**============================================================**

A contract is the observable promise a function makes to the rest of the
program.

The most useful formulation developed during the learning process is:

    Test the results the program needs in order to function.

This is more operational than trying to test every internal line.

Example: process_single_url()

Its relevant contract is approximately:

- if page loading fails, return None;
- if scrolling fails, return None;
- if HTML extraction fails, return None;
- if every stage succeeds, return the extracted HTML.

The tests do not need real Playwright navigation to prove that orchestration
contract. They replace the stages with controlled fake functions.

This produces four clear paths:

    loading succeeds, scrolling succeeds, extraction succeeds -> HTML
    loading fails                                             -> None
    scrolling fails                                           -> None
    extraction fails                                          -> None

The tests concentrate on what the caller receives, not on browser details that
belong to lower-level functions.


**============================================================**
4. PURE INPUT/OUTPUT TESTS
**============================================================**

Files:
- tests/test_3.py
- tests/test_product_parser.py

Pure or mostly pure tests give a function concrete input and compare its output
with an expected value.

Examples in test_3.py include:

- extracting a title from a small HTML string;
- returning None when a link is absent;
- extracting an href;
- returning a dictionary containing title and href;
- extracting several products;
- skipping products without href values;
- preserving a missing title as None;
- joining relative URLs to a base URL;
- preserving already absolute URLs.

These tests teach several useful ideas:

1. Small representative input

   A test does not need an entire website page when a short HTML fragment is
   enough to demonstrate the behavior.

2. Happy paths and edge cases

   The suite checks both valid product cards and incomplete HTML structures.

3. Exact expected structures

   Tests compare dictionaries and lists directly. This verifies both values
   and structure.

4. Boundary behavior

   Examples:
   - no article elements -> empty list;
   - no matching link -> None;
   - missing href -> product skipped;
   - missing title -> title stored as None.

The product parser tests use saved HTML fixture files:

- test_book.html
- test_page.html

They then run production parsing behavior from BooksToScrape and compare the
result with a complete expected dictionary or list.

This is useful when the parser needs realistic HTML but does not need a real
network request.


**============================================================**
5. PYTEST FIXTURES
**============================================================**

Files:
- tests/test_fixture.py
- tests/test_db.py
- tests/test_search_html_parser.py
- tests/test_search_scraper.py
- tests/test_product_parser.py
- tests/test_product_seed.py

A fixture supplies reusable test setup.

Example:

    @pytest.fixture
    def url_for_testing():
        return "www.mdp.com"

A test requests the fixture by naming it as a parameter:

    def test_something(url_for_testing):
        ...

Pytest finds the fixture and injects its returned value.

Fixtures in this project provide:

- small HTML strings;
- base URLs;
- test dates and URLs;
- temporary directories;
- temporary SQLite databases;
- realistic HTML loaded from files.

Why fixtures exist:

- avoid repeating setup;
- give multiple tests consistent input;
- isolate test data from production data;
- make cleanup reliable.

A fixture should usually represent meaningful reusable setup, not merely hide
one arbitrary line.


**============================================================**
6. YIELD FIXTURES: SETUP, HANDOFF, CLEANUP
**============================================================**

The temporary database fixtures use yield:

    @pytest.fixture
    def tmp_db(tmp_path):
        temp_db_path = tmp_path / "temp_db.sqlite"
        db = db_initialization(temp_db_path)

        yield db

        db_cur_and_conn_closer(db)

The phases are:

1. Before yield:
   create the temporary database and initialize its tables.

2. At yield:
   hand the database object to the test.

3. After the test:
   close the cursor and connection.

The conceptual purpose of yield is not special test magic. It divides fixture
execution into:

    setup -> provide resource -> cleanup

Cleanup still belongs to the fixture because the fixture created the resource.


**============================================================**
7. TMP_PATH AND TEMPORARY FILE TESTING
**============================================================**

Files:
- tests/test_fixture.py
- tests/test_search_html_parser.py
- tests/test_search_scraper.py

tmp_path is a pytest fixture that provides a unique temporary pathlib.Path for
a test.

It is used to test file operations without writing into the crawler's real data
directory.

The file-writing tests verify:

- the target file is created;
- the written content is correct;
- a newer write replaces older content;
- UTF-8 text such as "Pedro Páramo" survives correctly;
- missing parent directories are created.

This teaches an important testing principle:

    Use the real filesystem behavior when the filesystem itself is part of the
    contract, but isolate it in a temporary directory.

There is no need to mock open() merely because a file is involved. If the
purpose is to verify that a real file is correctly written, tmp_path gives a
safe and deterministic test environment.


**============================================================**
8. DATABASE INTEGRATION TESTS
**============================================================**

Files:
- tests/test_db.py
- tests/test_product_seed.py
- parts of tests/test_search_scraper.py
- tests/test_search_html_parser.py

The database tests use a real temporary SQLite database rather than a fake
cursor.

They verify:

- initialization creates the expected tables;
- inserting a URL stores the expected URL and date;
- the unique rule prevents duplicate URL rows;
- status checks behave differently for missing, pending, fetched, and failed
  URLs;
- update operations change statuses and filenames;
- stuck in_progress jobs return to pending;
- seed logic skips or reprocesses URLs according to status.

These are integration tests because several real pieces work together:

    production database function
    + sqlite connection
    + schema
    + SQL behavior
    + transaction commit

The test checks the database directly with SELECT statements. This is valid
evidence because the database state is the contract being tested.

SQLite returns rows as tuples. Therefore:

    fetchone() -> one tuple or None
    fetchall() -> a list of tuples

Examples:

    ("www.test.com", "pending")

or:

    [("book1.html", "pending"), ("book2.html", "pending")]

The database tests also teach state-transition testing:

    pending -> in_progress
    in_progress -> pending
    pending -> fetched
    pending -> failed
    failed -> pending when reseeded

The important question is not only whether a function returned something. It
is whether the persistent state now matches what the next crawler stage needs.


**============================================================**
9. INTEGRATION ACROSS FILES, PARSING, CONFIGURATION, AND DATABASE
**============================================================**

File:
- tests/test_search_html_parser.py

These tests combine:

- a real temporary HTML file;
- BeautifulSoup parsing;
- a FakeSiteConfig;
- a real temporary database;
- product URL insertion.

FakeSiteConfig replaces site-specific extraction behavior:

    class FakeSiteConfig:
        def __init__(self, products):
            self.products = products

        def product_extraction(self, soup):
            return self.products

The test does not care whether BooksToScrape selectors are correct. It cares
whether the search HTML parser takes extracted product dictionaries and stores
their links as pending product pages.

This is a useful test-boundary decision:

    Real:
    - file reading;
    - parser orchestration;
    - database insertion.

    Fake:
    - website-specific extraction rules.

The final evidence is a database query containing:

    ("book1.html", "pending")

or two corresponding rows.

This is broader than a unit test but still controlled and local.


**============================================================**
10. DEPENDENCIES AND DEPENDENCY INJECTION
**============================================================**

A dependency is something a function calls or uses to do its job.

For process_single_url(), the dependencies are:

- page_loading;
- perform_scrolling;
- html_extracting;
- time.sleep.

The function accepts three dependencies as parameters with production defaults:

    page_loading=load_page
    perform_scrolling=perform_scroll
    html_extracting=extract_html

The tests inject fake functions:

    def fake_load_page(...):
        return True

    def fake_perform_scroll(...):
        return False

    def fake_extract_html(...):
        return "dummy_content"

This is dependency injection:

    The function does not have to use only its real dependencies. A test can
    supply controlled replacements.

Why this is useful:

- no browser is opened;
- each path can be forced deliberately;
- the test stays fast;
- the test can focus on orchestration logic;
- failures are easier to locate.

A fake function is a small working replacement with behavior written directly
for the test.


**============================================================**
11. FAKES
**============================================================**

A fake is a simplified implementation that behaves enough like the real
dependency for the test.

The suite uses two forms.

1. Fake functions

   Used in process_single_url() and scrape_urls():

       def fake_fetch_html(...):
           return "<html>...</html>"

2. Fake objects

   Used in load_page():

       class FakePage:
           def goto(...):
               pass

           def reload(...):
               pass

           def wait_for_selector(...):
               pass

The fake page represents successful Playwright operations by not raising.

This is important:

    Some APIs communicate success through the absence of an exception rather
    than through return True.

The test therefore does not need fake goto() to return True. It only needs it
to complete normally.


**============================================================**
12. STATEFUL FAKES
**============================================================**

Sometimes a dependency must behave differently on successive calls.

Example:

    first wait_for_selector() call -> raises
    second wait_for_selector() call -> succeeds

A stateful fake stores a counter:

    self.wait_for_selector_count = 0

Each call changes the state:

    self.wait_for_selector_count += 1

The method then branches according to the count.

This models retry behavior explicitly and teaches that object state persists
after a method call, even when a later line raises an exception.

Example sequence:

    call count becomes 1
    exception is raised
    load_page catches it
    retry occurs
    call count becomes 2
    method succeeds

The state change made before raise remains.


**============================================================**
13. EXCEPTIONS AND CONTROL FLOW
**============================================================**

When a line raises an exception:

- normal execution of the current try block stops;
- later lines in that try block are skipped;
- control jumps to the matching except block.

This distinction was essential in the load_page tests.

Path A:

    goto() raises
    -> wait_for_selector() is not called on the first attempt
    -> retry reloads
    -> wait_for_selector() is called once total if retry succeeds

Path B:

    goto() succeeds
    -> wait_for_selector() raises
    -> retry reloads
    -> wait_for_selector() is called a second time

Therefore:

    goto failure followed by retry success:
        wait_for_selector call count == 1

    selector failure followed by retry success:
        wait_for_selector call count == 2

This demonstrates why vague names such as "retry happy path" are insufficient.
A test must identify exactly where the first attempt fails.


**============================================================**
14. RAISE EXCEPTION VS BARE RAISE
**============================================================**

To intentionally create an exception:

    raise Exception
    raise Exception()

Both raise a new generic Exception.

A bare raise:

    raise

means:

    re-raise the exception currently being handled.

It normally belongs inside an except block. If there is no active exception,
bare raise produces:

    RuntimeError: No active exception to reraise

For fake methods that intentionally simulate navigation failure, use:

    raise Exception

or:

    raise Exception()


**============================================================**
15. MANUAL CALL TRACKING
**============================================================**

Before using Mock interaction helpers, the suite manually reproduces their
mechanism:

    self.goto_calls = 0
    self.reload_calls = 0

and:

    self.goto_calls += 1

Assertions then check:

    assert fake_page.goto_calls == 1
    assert fake_page.reload_calls == 1

This teaches what a mock records internally.

The increment must happen before raise:

    self.goto_calls += 1
    raise Exception

If the increment were after raise, it would never execute.

Manual counters make the concept visible:

    the fake does not only behave like the dependency;
    it also records how it was used.


**============================================================**
16. MOCK OBJECTS
**============================================================**

Import:

    from unittest.mock import Mock

Create:

    fake_page = Mock()

Attributes accessed on a Mock, such as:

    fake_page.goto
    fake_page.reload
    fake_page.wait_for_selector

become mock objects that can be called, configured, and inspected.

By default, a mock method:

- does not raise;
- returns another Mock;
- records calls and arguments.

A Mock is useful when the test needs evidence that a dependency was used
correctly.

This is the problem mocks solve:

    A fake supplies replacement behavior.
    A mock additionally records interactions.


**============================================================**
17. MOCK VS MAGICMOCK
**============================================================**

Mock supports ordinary method and attribute behavior.

MagicMock adds prepared support for Python special methods such as:

    __len__
    __iter__
    __getitem__
    __enter__
    __exit__

For the fake Playwright page, ordinary methods such as goto(), reload(), and
wait_for_selector() do not require MagicMock. Mock is sufficient.

MagicMock is broader, not automatically better.


**============================================================**
18. MOCK ASSERTION METHODS
**============================================================**

Mock provides assertion helpers such as:

    assert_called()
    assert_called_once()
    assert_not_called()
    assert_called_with(...)
    assert_called_once_with(...)
    assert_any_call(...)
    assert_has_calls(...)

These are methods of the mock library.

Example:

    fake_page.goto.assert_called_once()

Do not write:

    assert fake_page.goto.assert_called_once()

Reason:

- assert_called_once() performs the assertion internally;
- when successful, it returns None;
- wrapping it in assert would become assert None, which fails.

A mock assertion method either:

- completes normally when the expectation is satisfied; or
- raises AssertionError when it is not.

The suite uses interaction checks such as:

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_not_called()
    mock_human_scroll.assert_called_once()


**============================================================**
19. CALL_COUNT
**============================================================**

call_count is an attribute of a Mock object.

Example:

    fake_page.wait_for_selector.call_count

It stores how many times that specific mock was called.

The mock library updates it automatically.

This:

    assert fake_page.wait_for_selector.call_count == 2

is equivalent in purpose to a manually maintained counter, but without writing
the counter logic yourself.

Each mocked method has its own call history:

    fake_page.goto.call_count
    fake_page.reload.call_count
    fake_page.wait_for_selector.call_count


**============================================================**
20. RETURN_VALUE
**============================================================**

return_value defines the value a mock returns when called normally.

Example:

    fake_page.content.return_value = "<html>test</html>"

Then:

    fake_page.content()

returns the same HTML string.

Use return_value when the normal successful behavior is:

    call completes -> gives back a value

The extract_html happy-path test applies this directly:

    page.content() returns HTML
    -> extract_html() returns that HTML


**============================================================**
21. SIDE_EFFECT
**============================================================**

side_effect configures behavior that occurs when a mock is called.

It can be:

1. An exception

       fake_page.goto.side_effect = Exception()

   Calling goto() raises.

2. A function

       mock.side_effect = custom_function

   Calling the mock delegates behavior to that function.

3. An iterable or sequence

       mock.side_effect = [Exception(), None]

   Successive calls consume successive items:
   - first call raises Exception;
   - second call returns None.

The name "side_effect" can be confusing because the configured exception may
be the main intended behavior in the test. In the mock API, the term means
behavior triggered by calling the mock that is not merely one stable normal
return.

Difference:

    return_value:
        one normal result returned by the call.

    side_effect:
        an exception, custom behavior, or changing sequence of results.

A string assigned to side_effect is treated as an iterable:

    mock.side_effect = "test"

would produce successive values:

    "t", "e", "s", "t"

and then StopIteration.

Therefore, use return_value when the desired stable result is the full string.

A useful syntax distinction is:

    side_effect is an attribute that is assigned:

        fake_html_fetching.side_effect = [Exception(), "html_content"]

    It is not called like a function:

        fake_html_fetching.side_effect(...)

Another important distinction is that return_value does not distribute a
list across calls. For example:

    mock_write_html.return_value = [False, True]

means every call returns the entire list [False, True]. Because a non-empty list
is truthy, code such as:

    if write_html(...):

would treat that result as successful. Changing behavior across calls belongs to
side_effect, while one stable result belongs to return_value.


**============================================================**
22. SIDE_EFFECT SEQUENCES AND RETRIES
**============================================================**

The selector retry test uses a sequence:

    fake_page.wait_for_selector.side_effect = [
        Exception(),
        True,
    ]

Conceptually:

    first selector call -> raises
    second selector call -> returns True

Because load_page() does not use the selector method's return value, None would
also represent a successful second call:

    [Exception(), None]

The key idea is not the returned True or None. The key idea is:

    first call interrupts the attempt;
    second call completes without raising.

The test then verifies:

    goto called once;
    reload called once;
    selector called twice;
    result is True.

The same mechanism can model different outcomes for different product rows:

    fake_html_fetching.side_effect = [Exception(), "html_content"]

Conceptually:

    first call  -> raises Exception
    second call -> returns normal HTML

A side_effect sequence may be any iterable. A list or tuple can therefore
represent successive behaviors. The important idea is the order of consumed
items, not the specific container type.


**============================================================**
23. PATCH
**============================================================**

Import:

    from unittest.mock import patch

patch temporarily replaces a name with a mock or another replacement.

Example:

    with patch("utilities.utils.time.sleep"):
        result = process_single_url(...)

Conceptual behavior:

    save original object
    replace name with a mock
    run code inside with block
    restore original object when block ends

The replacement is restored even if an exception occurs inside the block.

A default mock accepts calls and records them but does not run the original
function. Therefore, patching time.sleep prevents the real delay.


**============================================================**
24. PATCH WITH "AS"
**============================================================**

This form:

    with patch("utilities.utils.human_scroll") as mock_human_scroll:
        ...

does two things:

1. replaces utilities.utils.human_scroll with a mock;
2. gives the test a local reference named mock_human_scroll.

The test can then configure or inspect it:

    mock_human_scroll.side_effect = Exception()
    mock_human_scroll.assert_called_once()

Without "as", patch still replaces the object, but the test does not retain a
convenient handle to configure or inspect the generated mock.


**============================================================**
25. PATCH WHERE THE NAME IS LOOKED UP
**============================================================**

The source contains an import equivalent to:

    from utilities.stealth import human_scroll

This means:

- the original function is defined in utilities.stealth;
- utilities.utils receives its own name referring to that function;
- perform_scroll() looks up human_scroll inside utilities.utils.

Therefore the correct target for testing perform_scroll() is:

    patch("utilities.utils.human_scroll")

not:

    patch("utilities.stealth.human_scroll")

General rule:

    Patch the name where the tested code looks it up.

A patch can target the original definition yet fail to replace the already
imported local reference used by the tested module.

Interaction assertions help expose a wrong patch target. If the patched mock
was never called, assert_called_once() fails.

GOLDEN MEMORY RULE 

from X import Y  → call Y(...)
import X         → call X.Y(...)


**============================================================**
26. PATCH ONLY WHAT THE TEST NEEDS TO CONTROL
**============================================================**

Not every test needs every patch.

Example:

In the immediate-success load_page path:

    goto succeeds
    selector succeeds
    break exits the loop

The retry branch is never reached, so time.sleep is never called.

Therefore, that test does not need to patch sleep.

In retry tests:

    first attempt fails
    second attempt executes sleep + reload

Those tests patch time.sleep to avoid a real 15-25 second delay.

This teaches a useful discipline:

    Patch an external behavior because it interferes with the test, not merely
    because patch is available.


**============================================================**
27. TESTING IMPORTED HELPERS
**============================================================**

perform_scroll() wraps human_scroll():

    human_scroll(...)
    return True

If human_scroll raises:

    timeout -> False
    generic exception -> False

The tests patch the imported helper and verify three paths:

1. Default mock does not raise:
   perform_scroll returns True.

2. Mock raises generic Exception:
   perform_scroll catches it and returns False.

3. Mock raises PlaywrightTimeoutError:
   the specific timeout branch catches it and returns False.

These tests show how to isolate a wrapper from a lower-level helper while still
checking that the wrapper called that helper.


**============================================================**
28. HIGHER-LEVEL SCRAPER ORCHESTRATION TESTS
**============================================================**

File:
- tests/test_search_scraper.py

The scrape_urls tests use a real temporary database and filesystem but inject a
fake fetch_html function.

Success path evidence:

    HTML returned
    -> page file written
    -> filename stored in database
    -> status becomes fetched

Failure path evidence:

    fetch_html returns None
    -> file not written
    -> filename remains None
    -> status becomes failed

Multiple-item tests verify:

- two successful URLs produce two files and fetched statuses;
- one failed URL does not stop the crawler from processing the next URL;
- filenames correspond to database IDs;
- each item's final state is independently correct.

These are orchestration/integration tests. They verify a workflow across:

    database queue
    + injected HTML fetching
    + file writing
    + filename persistence
    + status transitions
    + loop continuation

The injected fake controls the browser-facing boundary. The real internal
workflow remains active.


**============================================================**
29. TESTING CONTINUATION AFTER FAILURE
**============================================================**

The one-failure/one-success scraper test checks more than two isolated results.

Its contract includes:

    A failed URL must not terminate processing of later pending URLs.

The evidence is:

- the failed URL has no file and status failed;
- the successful URL still gets a file, filename, and fetched status.

This is an important loop behavior. A test of only one failed URL would not
prove continuation.


**============================================================**
30. REFACTORING ORCHESTRATION FOR TESTABILITY
**============================================================**

The product scraper originally combined several responsibilities:

    reset stuck database jobs
    + create Playwright and the browser
    + create the page
    + process the database queue
    + fetch HTML
    + write files
    + update statuses

This made the main loop difficult to test because testing it also required
controlling the complete Playwright context-manager chain.

The function was divided into three levels:

    run_crawler_product_scraper()
        resets stuck jobs and starts the workflow

    scrape_product_urls_with_playwright()
        creates Playwright, browser, context, and page

    scrape_product_urls()
        performs the product-processing loop

The important design lesson is:

    Separate environment setup from workflow logic.

After this refactoring, scrape_product_urls() can receive a fake page and an
injected fetch_html function. Its tests no longer need to launch or reproduce a
real browser session.

This is not refactoring merely to satisfy tests. The separation also clarifies
what each function is responsible for.


**============================================================**
31. PRODUCT-SCRAPER RESPONSIBILITY AND BRANCH CONTRACTS
**============================================================**

The responsibility identified for scrape_product_urls() is:

    retrieve one pending product
    -> fetch its HTML
    -> write the HTML to disk
    -> update the database according to the outcome
    -> continue until no pending rows remain

The following contracts were established and tested.

1. Successful product

       pending row exists
       fetch_html returns HTML
       write_html succeeds
       -> product_1.html exists
       -> file content is correct
       -> database status becomes fetched

2. HTML fetching fails

       fetch_html returns None
       -> no file is created
       -> database status becomes failed

3. HTML writing fails

       fetch_html returns HTML
       write_html returns False
       -> write_html is called
       -> no real file is created
       -> database status becomes failed

4. Product row has no URL

       row_id exists
       product_url is None
       -> fetch_html is not called
       -> write_html is not called
       -> database status becomes failed_unfetchable

5. No pending product remains

       get_pending_product_url returns (None, None)
       -> the loop stops
       -> later processing stages are not reached

6. Keyboard interruption after row selection

       row has already changed from pending to fetching
       fetch_html raises KeyboardInterrupt
       -> current row returns to pending
       -> KeyboardInterrupt is raised outward again

7. Ordinary exception after row selection

       row has already changed from pending to fetching
       fetch_html raises Exception
       -> current row becomes failed
       -> write_html is skipped for that row
       -> error_logger.error(...) is called
       -> the exception is swallowed
       -> the loop can continue to the next pending product

8. Special wait at the interval boundary

       page_counter is a non-zero multiple of 5
       -> random.uniform(5, 7) is used to obtain the special wait
       -> countdown_sleep_timer receives that value

   The test patches random.uniform to make the branch deterministic and patches
   countdown_sleep_timer to avoid a real delay.

9. No special wait outside the interval boundary

       page_counter is not a multiple of 5
       -> the special wait branch must not execute

   Because countdown_sleep_timer is also used later for the normal post-success
   delay, the test deliberately makes fetch_html return None. That causes the
   loop to continue before the normal delay and isolates the branch being tested.

10. Failed fetch does not advance page_counter

       first product -> fetch_html returns None
       second product -> fetch_html returns HTML
       -> first product becomes failed
       -> second product becomes fetched
       -> the successful file is still product_1.html

   This proves that page_counter advances only after a successful write. A failed
   fetch does not consume an output filename number.

These tests combine outcome evidence and interaction evidence:

    Outcome evidence:
        file existence, file content, database status

    Interaction evidence:
        fetch_html called or skipped, write_html called or skipped


**============================================================**
32. TESTING DATABASE STATE TRANSITIONS DIRECTLY
**============================================================**

The get_pending_product_url() tests verify more than its returned tuple.

Successful retrieval:

    inserted row begins as pending
    get_pending_product_url() returns (row_id, product_url)
    selected row becomes fetching

Empty queue:

    no pending row exists
    -> returns (None, None)

This reinforced the principle that a database function can have two observable
parts of its contract:

    returned value
    + persistent state change

For queue-processing code, testing only the returned row would miss the lock or
status transition that prevents the same pending item from being selected
again.


**============================================================**
33. PATCH TARGETS AND IMPORT STYLE
**============================================================**

A practical debugging case clarified the rule:

    Patch the name used by the module under test.

The production module contains:

    from utilities.utils import write_html

This creates a local name inside:

    crawler.crawler_product_scraper.write_html

The function scrape_product_urls() later calls:

    write_html(...)

Therefore the working patch target is:

    patch("crawler.crawler_product_scraper.write_html")

Patching:

    patch("utilities.utils.write_html")

replaced the name in utilities.utils, but it did not replace the already
imported local reference used by crawler.crawler_product_scraper. The symptom
was especially instructive:

    the mock reported zero calls
    but the real HTML file existed

That meant the real function was still running.

The import-style memory rule is:

    from X import Y
        code calls Y(...)
        patch the Y name inside the module that imported it

    import X
        code calls X.Y(...)
        patch X.Y where that expression is looked up

Example:

    from utilities.utils import write_html
    -> patch crawler.crawler_product_scraper.write_html

    import utilities.utils
    utilities.utils.write_html(...)
    -> patch utilities.utils.write_html

The exact dotted module path must also be importable. In this project the module
is not a top-level crawler_product_scraper module; its import path is:

    crawler.crawler_product_scraper


**============================================================**
34. EXPECTED EXCEPTIONS WITH PYTEST.RAISES
**============================================================**

side_effect and pytest.raises perform different jobs.

To make a dependency raise an interruption:

    fake_html_fetching = Mock()
    fake_html_fetching.side_effect = KeyboardInterrupt()

This arranges the failure.

To verify that the function under test lets that interruption escape:

    with pytest.raises(KeyboardInterrupt):
        scrape_product_urls(...)

This asserts the outward behavior.

The term swallowed exception was clarified as:

    the exception occurs and enters an except block,
    but the function does not raise it outward again

The product scraper must not swallow KeyboardInterrupt. It first restores the
selected row to pending and then re-raises the interruption.

Assertions that must run after the exception should be placed after the
pytest.raises block:

    with pytest.raises(KeyboardInterrupt):
        scrape_product_urls(...)

    fake_html_fetching.assert_called_once()
    mock_write_html.assert_not_called()
    assert database_status == "pending"

Lines placed after the raising call but still inside pytest.raises do not run,
because execution leaves the block as soon as the expected exception occurs.


**============================================================**
35. GENERIC EXCEPTIONS, LOGGING, AND LOOP CONTINUATION
**============================================================**

The product scraper distinguishes an ordinary Exception from KeyboardInterrupt.

For an ordinary Exception after a row has already been selected:

    row is fetching
    -> fetch_html raises Exception
    -> except Exception runs
    -> row becomes failed
    -> error is logged
    -> exception is not raised outward again
    -> loop continues

This is what it means for the ordinary exception to be swallowed: the function
handles it internally instead of propagating it to the caller.

A narrow test can prove this branch with one product row. If execution reaches
the assertions after scrape_product_urls() returns, that itself is evidence
that the ordinary exception did not escape. pytest.raises(Exception) would be
wrong for this contract because the function is expected to catch the exception.

The logger assertion must target the method that production code actually calls.
If production code executes:

    error_logger.error(
        "Unhandled error in product scraper",
        exc_info=True
    )

then the corresponding interaction assertion is on:

    mock_error_logger.error

not on the logger object itself. This follows the same interaction-testing rule
used elsewhere: assert against the collaborator method that received the call.

A stronger continuation test uses two product rows and changing fetch behavior:

    first product  -> fetch_html raises Exception
    second product -> fetch_html returns "html_content"

The evidence for continuation is cumulative:

    fake_html_fetching.call_count == 2
        proves the scraper attempted both rows;

    first row status == failed
        proves the exception branch completed its recovery state;

    second row status == fetched
        proves processing did not merely continue to another call but completed
        the next product successfully.

When the real write_html() is left active in that continuation test, additional
integration evidence can be checked:

    product_1.html exists
    its content is "html_content"

The filename is product_1.html because page_counter increments only after a
successful write. The first product failed before writing, so it did not consume
a file number.

This also clarified the difference between mocking and using a real dependency:

    mocked write_html:
        proves scrape_product_urls() follows the expected control flow when
        writing reports success or failure;

    real write_html:
        proves that flow plus the actual filesystem integration in that flow.


**============================================================**
36. TESTING THE SAME DEPENDENCY FROM MULTIPLE BRANCHES
**============================================================**

The special-wait test introduced an important interaction-testing problem:
the same dependency can be called for more than one reason.

In scrape_product_urls(), countdown_sleep_timer is used in two places:

    special wait:
        when page_counter is a non-zero multiple of 5

    normal wait:
        after a successful product write

This affects how interaction evidence should be chosen.

If random.uniform is patched to return 6 for every call and a successful product
is processed with page_counter=5, countdown_sleep_timer may receive 6 more than
once. Therefore:

    mock_countdown_sleep_timer.assert_called_once_with(6)

would be too strong for that test.

A more suitable assertion is:

    mock_countdown_sleep_timer.assert_any_call(6)

Meaning:

    among all calls recorded by this mock,
    at least one call had argument 6

This differs from:

    assert_called_with(6)

which checks the most recent call.

The inverse-branch test introduced another useful principle:

    When the same dependency can be called by several branches,
    remove unrelated reasons for that dependency to be called.

For page_counter=4, fetch_html is made to return None. This causes the function
to continue before reaching the normal post-success wait. The resulting:

    mock_countdown_sleep_timer.assert_not_called()

can therefore be interpreted specifically as evidence that the special-wait
branch did not run.

This is branch isolation: control the surrounding flow so the observed call or
absence of a call has only one relevant explanation.

Later refinement from automated mutation testing:

    assert_any_call(expected_value)

is still weak evidence if another branch can independently produce the same
expected call.

This happened when random.uniform was patched with one stable return value for
the whole scraper test. The intended special wait used:

    random.uniform(5, 7)
    -> countdown_sleep_timer(6)

but the later normal wait also used random.uniform. Because the same patched
random.uniform returned 6 there as well, the normal wait could produce:

    random.uniform(1, 5)
    -> mocked result 6
    -> countdown_sleep_timer(6)

Therefore:

    mock_countdown_sleep_timer.assert_any_call(6)

could pass even when the special-wait branch never executed.

Refined rule:

    The observed evidence must not only be compatible with the intended branch.
    It should be difficult or impossible for an unrelated branch to produce the
    same evidence.

When several branches share the same dependency and can produce indistinguishable
calls, useful options are:

- isolate the other branch;
- inspect a more specific interaction;
- extract the behavior behind a helper boundary and test the helper directly.

This became a concrete example of a test being technically correct while its
evidence remained semantically ambiguous.


**============================================================**
37. PAGE COUNTERS AND FAILURE-THEN-SUCCESS FLOWS
**============================================================**

The page-counter test combines changing mock behavior with a real filesystem
write:

    fake_html_fetching.side_effect = [None, "html_content"]

Conceptually:

    first product:
        fetch fails
        -> no write
        -> status failed
        -> page_counter unchanged

    second product:
        fetch succeeds
        -> real write_html runs
        -> status fetched
        -> product_1.html is created

This is another example of choosing the test boundary deliberately.

Mocking write_html would allow direct control over write success and failure,
but it would prevent the real HTML file from being created. By instead
controlling fetch_html, the test controls the workflow while leaving the real
writer active.

The resulting evidence proves both:

    orchestration:
        a failed fetch does not consume a filename number

    integration:
        the later successful product is really written as product_1.html

A useful design question is therefore:

    Which dependency should I control so that the behavior I actually want
    evidence for can remain real?


**============================================================**
38. TEST NAMES AS TECHNICAL DOCUMENTATION
**============================================================**

A good test name describes behavior, not only a general mood such as
"happy path" or "unhappy path."

Examples of more precise forms:

    test_load_page_returns_false_when_selector_always_fails
    test_perform_scroll_returns_false_on_playwright_timeout
    test_extract_html_returns_none_when_content_raises

Precision matters especially for retry tests.

These are different:

    goto fails, then reload succeeds
    selector fails, then selector succeeds after reload
    every navigation attempt fails
    selector fails on every attempt

All may involve "retry," but their call counts differ.

A useful test name can often be read as:

    test_[unit]_[expected behavior]_when_[condition]


**============================================================**
39. CURRENT SUITE: LEARNING EXERCISES VS PRODUCTION TESTS
**============================================================**

Not every test in the folder currently targets imported production code.

Some early learning files define the function inside the test module:

- test_3.py defines its own extraction functions;
- test_fixture.py defines its own extraction and save_html functions;
- test_search_html_parser.py defines local parser/insertion functions;
- test_search_scraper.py defines a local update_filename_for_url function.

These tests are still useful learning exercises. They teach test construction,
fixtures, edge cases, files, and databases.

However, they do not protect the corresponding production implementation from
regressions when they test a local copy rather than importing the production
function.

This distinction is important:

    Learning test:
        proves that the example implementation in the test module behaves as
        expected.

    Regression test:
        imports and exercises the actual production function, so it fails if
        production behavior changes incorrectly.

A future consolidation step is to migrate useful learning cases toward actual
production imports when appropriate.


**============================================================**
40. CURRENT SUITE: TECHNICAL OBSERVATIONS
**============================================================**

The uploaded suite passes, but several details are worth remembering.

1. A test can pass without testing what its name claims.

   test_load_page_calls_reload_in_retry_happy_path currently uses an
   unconfigured Mock. The first attempt succeeds, and its assertions say reload
   was not called. The behavior tested is another immediate-success path, not a
   retry path.

2. A test can be collected but effectively do nothing.

   test_scrape_urls_with_playwright contains an early return before its setup
   and assertions. Pytest reports it as passed because no assertion fails, but
   the intended behavior is not exercised.

3. A name can contradict its assertion.

   test_already_pending_or_fetched_url_returns_false_after_fetched_status
   asserts True. The production behavior and assertion agree that fetched
   should return True; the test name is the mismatched part.

4. Local copies can drift from production.

   A test of a locally defined helper may remain green even if the actual
   production helper changes or breaks.

5. A passing test is evidence only for the exact path and assertions it
   contains.

These are not reasons to discard the tests. They are examples of why test
review matters in addition to seeing a green test run.


**============================================================**
41. DETERMINISM
**============================================================**

A deterministic test produces the same result repeatedly under the same code.

The suite improves determinism by:

- patching real sleeps;
- avoiding network requests;
- using fixed HTML strings;
- using temporary local databases;
- using temporary directories;
- injecting fake fetch functions;
- forcing exceptions explicitly with side_effect.

Random delays, browser state, external sites, and persistent production data
would make tests slower or less reliable.

The principle is:

    Keep the behavior under test real.
    Control unrelated uncertainty at the test boundary.


**============================================================**
42. UNIT TESTS AND INTEGRATION TESTS IN THIS PROJECT
**============================================================**

Examples closer to unit tests:

- extract_html with a Mock page;
- perform_scroll with patched human_scroll;
- load_page with a fake or mock page;
- process_single_url with injected fake stage functions;
- small HTML extraction functions.

Examples closer to integration tests:

- database functions using real SQLite;
- saving and reading real files under tmp_path;
- search HTML parser inserting into a real temporary DB;
- scrape_urls updating DB state and writing files;
- BooksToScrape parsing realistic saved HTML.

The difference is not that one category is good and the other bad.

Unit tests provide narrow diagnosis and precise control.

Integration tests provide confidence that several real components cooperate.

A healthy suite often uses both.

The product-scraper tests give a concrete example of choosing that boundary.
If write_html is mocked, the test can prove orchestration and database state
transitions without proving that a real file is written. If write_html remains
real under tmp_path, the test additionally proves filesystem integration.
Neither boundary is automatically better; they answer different questions.


**============================================================**
43. A PRACTICAL TEST-DESIGN CHECKLIST
**============================================================**

Before writing a test, answer:

1. Responsibility

   What job does this function perform?

2. Contract

   What observable result does the next part of the program depend on?

3. Dependencies

   What does the function call or use?

4. Test boundary

   Which dependencies should remain real, and which should be controlled?

5. Exact path

   Where does success or failure occur?
   Which later lines are skipped because of it?

6. Evidence

   Should the test check:
   - return value;
   - file content;
   - database state;
   - exception;
   - call count;
   - call arguments;
   - absence of a call?

7. Determinism

   Do network access, sleep, randomness, real browser state, or persistent data
   need to be replaced or isolated?

8. Cleanup

   Does the test create files, connections, cursors, or another resource that
   should be removed or closed?

9. Test name

   Does the name describe the exact condition and expected behavior?

10. Strength check

   Could the test still pass if the production behavior it claims to test were
   removed or broken?


**============================================================**
44. QUICK REFERENCE
**============================================================**

Plain fake function:

    def fake_dependency(...):
        return controlled_value

Fake method that succeeds:

    def goto(...):
        pass

Fake method that fails:

    def goto(...):
        raise Exception()

Stateful fake:

    self.calls = 0

    def method(...):
        self.calls += 1
        if self.calls == 1:
            raise Exception()

Create mock:

    fake_page = Mock()

Stable returned value:

    fake_page.content.return_value = "<html>test</html>"

Raised failure:

    fake_page.content.side_effect = Exception()

Different behavior across calls:

    fake_page.method.side_effect = [Exception(), None]

Exception first, normal value second:

    fake_html_fetching.side_effect = [Exception(), "html_content"]

Remember:

    side_effect = [...]      -> successive call behavior
    return_value = [...]     -> every call returns that whole list

Interaction assertions:

    fake_page.goto.assert_called_once()
    fake_page.reload.assert_not_called()
    assert fake_page.wait_for_selector.call_count == 2

Autospecced mock from a real collaborator:

    fake_html_fetching: Mock = create_autospec(process_single_url)

The `: Mock` annotation helps editor/Pylance discovery of Mock methods.
The signature enforcement comes from create_autospec() at runtime.

Recorded call history:

    mock.call_count
    mock.call_args
    mock.call_args_list

Expected call descriptor:

    call(fake_page, "product_1.com", logger, wait_selector="x")

Exact complete call history:

    assert mock.call_args_list == expected_calls

Required calls with possible extra calls before or after:

    mock.assert_has_calls(expected_calls)

Inspect only one part of one call:

    first_call = mock.call_args_list[0]
    assert first_call.args[1] == "product_1.com"
    assert first_call.kwargs["wait_selector"] == "x"

Ignore one value while still comparing the rest of a call:

    call(fake_page, "product_1.com", ANY, wait_selector="x")

Exactly one call with expected arguments:

    mock.assert_called_once_with(...)

Clear recorded interactions while keeping normal configuration:

    mock.reset_mock()

Patch without inspecting replacement:

    with patch("utilities.utils.time.sleep"):
        ...

Patch and inspect/configure replacement:

    with patch("utilities.utils.human_scroll") as mock_human_scroll:
        mock_human_scroll.side_effect = Exception()
        ...

None assertion:

    assert result is None

Boolean assertion:

    assert result is True
    assert result is False

Temporary path:

    def test_file_behavior(tmp_path):
        path = tmp_path / "file.html"

Yield fixture:

    create resource
    yield resource
    close resource


**============================================================**
45. WHAT HAS BEEN CONSOLIDATED SO FAR
**============================================================**

The current test suite shows practical experience with:

- pytest test discovery and assertions;
- simple input/output tests;
- happy paths and edge cases;
- fixtures;
- yield-based cleanup;
- tmp_path;
- temporary SQLite databases;
- file and database integration tests;
- dependency injection;
- fake functions;
- fake objects;
- stateful fakes;
- exception-driven control flow;
- manual interaction counters;
- Mock;
- Mock assertion methods;
- call_count;
- return_value;
- side_effect;
- side_effect sequences;
- patch as a context manager;
- capturing a patched mock with "as";
- patching where a name is looked up;
- testing return outcomes;
- testing collaborator interactions;
- testing loop continuation after one item fails;
- distinguishing unit and integration test boundaries;
- refactoring browser setup away from orchestration logic;
- defining branch-specific contracts for a database/file workflow;
- verifying database state transitions such as pending -> fetching;
- patching multiple dependencies in one context manager;
- diagnosing an incorrect patch target from mock calls and real side effects;
- distinguishing `from X import Y` from `import X` when choosing patch paths;
- using pytest.raises to verify that an expected exception escapes;
- distinguishing the mock side_effect that creates an exception from the
  pytest assertion that expects it;
- testing KeyboardInterrupt recovery without swallowing the interruption;
- distinguishing ordinary exceptions that are intentionally swallowed from
  interruptions that must be re-raised;
- asserting calls on a mocked collaborator method such as error_logger.error;
- using side_effect sequences to produce an exception on one call and a normal
  value on the next;
- distinguishing side_effect assignment from calling side_effect as if it
  were a function;
- understanding that a list assigned to return_value is returned as one list,
  not distributed across calls;
- proving loop continuation through call counts plus final state of later rows;
- choosing deliberately between mocked file-writing orchestration tests and
  real filesystem integration tests;
- understanding that page_counter advances only after a successful write, so
  failed products do not consume output filenames;
- creating interface-aware mocks with create_autospec();
- using the real production collaborator as the autospec source so the test
  double follows the actual production signature;
- understanding that a plain Mock can accept invalid call signatures that the
  real collaborator would reject;
- distinguishing function parameters from call arguments;
- distinguishing default parameters from keyword arguments;
- understanding recorded mock calls as positional `args` plus keyword `kwargs`;
- using `call(...)` to describe an expected invocation;
- inspecting `call_args`, `call_args_list`, `.args`, and `.kwargs`;
- comparing `call_args_list` with an expected list when the complete call
  history, arguments, and order matter;
- using `assert_has_calls()` when required calls matter but extra surrounding
  calls are acceptable;
- using `ANY` when part of a call matters but one specific argument value does
  not;
- using `assert_called_once_with()` for one exact expected invocation;
- understanding `reset_mock()` as an interaction-history reset rather than, by
  default, a reset of configured return behavior.

This is already more than learning isolated pytest commands. It is the
beginning of a method for decomposing software behavior into controllable
contracts and observable evidence.


**============================================================**
46. CURRENT LEARNING POSITION
**============================================================**

The scrape_product_urls() branch-testing cycle is sufficiently complete.

The goal is not to keep adding branches or Mock API methods merely because they
exist. A new test or tool is worth adding when it introduces a distinct testing
idea, clarifies an important contract, or protects behavior that materially
matters.

A useful stopping rule is:

    Write another test when it teaches or proves something meaningfully new.
    Do not add tests only because another branch, argument, or Mock method exists.

The product-scraper work has already consolidated:

- branch-specific contracts;
- dependency injection;
- real database state checks;
- real filesystem integration;
- patching imported dependencies;
- deterministic control of randomness;
- exceptions that escape versus exceptions that are swallowed;
- loop continuation after failure;
- changing behavior across mock calls with side_effect;
- call-history inspection;
- autospecced collaborators;
- exact versus partial interaction verification.

At this point, learning additional Mock convenience methods would mostly expand
library vocabulary. The stronger next step is to reason about when interaction
verification should be used at all, and when state/outcome verification is the
better evidence.


**============================================================**
47. AUTOSPEC AND INTERFACE DRIFT
**============================================================**

A plain Mock is permissive. It may accept arguments that the real collaborator
would reject.

Example idea:

    fake_html_fetching = Mock()

If production code accidentally changes from a valid call to an invalid one,
a plain Mock may still accept it. The test can therefore remain green even though
the real collaborator's interface has been violated.

create_autospec() creates a mock from a real callable or object:

    fake_html_fetching: Mock = create_autospec(process_single_url)

The important effect is:

    the mock follows the real collaborator's call signature

If the tested code calls it with an invalid combination of positional or keyword
arguments, the autospecced mock raises TypeError.

This protects against interface drift between:

    the caller
    and
    the collaborator it is supposed to call

The autospec source should normally be the actual production collaborator:

    create_autospec(process_single_url)

rather than a locally written fake that merely imitates its signature.

A locally written fake can be thought of as a manually maintained interface
replacement. It can work, but the developer must keep its signature synchronized
with production. Autospec derives that interface automatically from the real
object.

Editor note:

    fake_html_fetching: Mock = create_autospec(process_single_url)

The `: Mock` annotation can help Pylance expose Mock members such as
call_args_list and assert_called_once_with. It does not create the autospec or
enforce the signature. create_autospec() does that at runtime.


**============================================================**
48. PARAMETERS, ARGS, KWARGS, AND RECORDED CALLS
**============================================================**

A distinction that became important while inspecting mock calls is:

    function definition -> parameters
    function call       -> arguments

Example definition:

    def func(a, b=10):
        ...

Here:

    a       is a parameter
    b       is a parameter
    b=10    means b has a default value

The default value belongs to the function definition.

Now consider a call:

    func(5, b=20)

The values were supplied in two different ways:

    5       -> positional argument
    b=20    -> keyword argument

Conceptually, a recorded mock call separates them as:

    args = (5,)
    kwargs = {"b": 20}

This is why default parameters and keyword arguments must not be treated as the
same concept.

A default parameter can be passed positionally:

    func(5, 20)

Then:

    args = (5, 20)
    kwargs = {}

A parameter with no default can still be passed by keyword:

    def func(a):
        ...

    func(a=5)

Then:

    args = ()
    kwargs = {"a": 5}

And if a default parameter is not supplied at all:

    func(5)

then the caller did not pass b, so the recorded call is still:

    args = (5,)
    kwargs = {}

Python applies the default value internally after argument binding.

For unittest.mock, a recorded call can be represented conceptually as:

    (args, kwargs)

or, for named/method calls:

    (name, args, kwargs)

These structures describe what was actually passed during the call. They are not
a description of which parameters in the original function have defaults.

In the product scraper, the injected collaborator is called approximately as:

    fetch_html(
        page,
        product_url,
        logger,
        wait_selector=specific_site_config.wait_selector
    )

Therefore:

    args[0] -> page
    args[1] -> product_url
    args[2] -> logger

and:

    kwargs["wait_selector"] -> selector value


**============================================================**
49. CALL, CALL_ARGS, AND CALL_ARGS_LIST
**============================================================**

Mocks record their interactions.

The small core worth remembering is:

    call_count      -> how many times the mock was called
    call_args       -> arguments of the most recent call
    call_args_list  -> arguments of every call, in order

The helper `call` is used to construct a description of an expected invocation:

    expected_calls = [
        call(
            fake_page,
            "product_1.com",
            logger,
            wait_selector="dummy_wait_selector"
        ),
        call(
            fake_page,
            "product_2.com",
            logger,
            wait_selector="dummy_wait_selector"
        ),
    ]

Each `call(...)` represents one expected invocation.

If the entire interaction history matters:

    assert fake_html_fetching.call_args_list == expected_calls

This proves, together:

- the number of calls is exact;
- the arguments of each call are exact;
- the order is exact;
- there are no extra calls.

A separate:

    assert fake_html_fetching.call_count == 2

would be redundant if exact equality with a two-element expected_calls list has
already been established.


**============================================================**
50. EXACT, PARTIAL, AND SELECTIVE INTERACTION ASSERTIONS
**============================================================**

Different assertions express different strengths of requirement.

1. Exact complete history

       assert mock.call_args_list == expected_calls

   Use this when the complete sequence itself is part of the expected behavior.

2. Required sequence inside a larger history

       mock.assert_has_calls(expected_calls)

   With the normal ordered behavior, the expected calls must occur sequentially
   and in order, but additional calls may exist before or after them.

   This fits a requirement such as:

       these two calls must happen,
       but other calls are allowed

3. Inspect one particular recorded call

       first_call = mock.call_args_list[0]

       first_call.args
       first_call.kwargs

   Example:

       assert first_call.args[1] == "product_1.com"

   This is useful when the test cares about one argument but should not be
   coupled to every detail of the invocation.

4. Ignore one value while comparing the rest

       call(
           fake_page,
           "product_1.com",
           ANY,
           wait_selector="dummy_wait_selector"
       )

   ANY means:

       a value must be present here,
       but its exact identity/value is irrelevant to this test

   This is especially useful when several parts of a call matter but one
   collaborator argument, such as the exact logger object, does not.

5. Exactly one call with exact arguments

       mock.assert_called_once_with(...)

   This combines:

       called exactly once
       +
       called with these arguments

6. Resetting interaction history

       mock.reset_mock()

   By default this clears recorded interaction state such as:

       call_count
       call_args
       call_args_list
       called

   It does not, by default, mean:

       forget the mock's configured behavior

   Configured return_value or side_effect can remain unless explicitly reset.

These methods are useful, but they are secondary to the testing question:

    What evidence actually matters for this contract?


**============================================================**
51. STATE VS INTERACTION VERIFICATION
**============================================================**

The next step is not another Mock method.

The more important design distinction is:

    State/outcome verification
        Did the program produce the correct observable result?

    Interaction verification
        Did the program use a collaborator in a particular way?

Examples already present in the product-scraper tests:

State/outcome evidence:

    assert html_path.exists()
    assert html_path.read_text() == "html_content"
    assert database_status == "fetched"

Interaction evidence:

    assert fake_html_fetching.call_args_list == expected_calls
    mock_write_html.assert_not_called()

The next learning question is:

    If the internals of a function are refactored but its externally required
    behavior remains correct, which assertions should continue to pass?

This leads into an important testing-design issue:

    interaction assertions can be valuable when the interaction itself is part
    of the contract, but excessive interaction checking can couple a test to the
    current implementation.


**============================================================**
52. TEST DESIGN AND SOFTWARE RELIABILITY
**============================================================**

The learning focus has moved beyond pytest syntax and Mock API mechanics.
The stronger questions are now:

    Where should failure boundaries be?
    What state is valid after partial failure?
    Which interactions actually belong to the contract?
    What behavior deserves permanent regression protection?

The emphasis is increasingly on test design, failure semantics, and software
reliability rather than on learning additional convenience methods.


**============================================================**
53. MEANINGFUL INTERACTIONS VS IMPLEMENTATION DETAILS
**============================================================**

State/outcome verification should usually be preferred when it directly proves
the externally meaningful contract.

Interaction verification is justified when the interaction itself matters.

Example:

    fetch_html returns None
    -> write_html must not be called

That absence is meaningful behavior because attempting to write nonexistent or
invalid HTML would itself be a bug.

By contrast:

    fetch_html was called exactly twice

may be too implementation-specific if the real requirement is only that two
products reach the correct final state.

Useful decision question:

    If this interaction changed while the externally required behavior remained
    correct, would I consider that a bug?

If no, the interaction is probably an implementation detail.
If yes, interaction verification may belong in the contract.


**============================================================**
54. FAILURE INJECTION AND PARTIAL FAILURE
**============================================================**

Failure injection means deliberately forcing an operation to fail at a precise
point in a workflow.

Example from the product HTML parser:

    parse HTML                -> succeeds
    update product data       -> succeeds
    mark parsed_succeeded     -> succeeds
    archive HTML              -> forced to fail

The purpose is not merely to enter an except block. The important question is:

    If failure happens here, after earlier side effects already succeeded, what
    state is left behind?

This creates a partial failure: later work fails after earlier work has already
changed external state.


**============================================================**
55. CONSISTENCY INVARIANTS ACROSS DATABASE AND FILESYSTEM
**============================================================**

The product parser modifies more than one external resource:

    database state
    +
    filesystem state

A consistency invariant describes which combinations of those states the
application considers valid.

The archive-failure discussion established that this can be a valid partial
success state:

    product data remains in the database
    parse_status remains parsed_succeeded
    original HTML remains in its original location because archiving failed

Consistency does not necessarily mean that every operation succeeded. It means
that the resulting state accurately represents what actually succeeded and what
failed.


**============================================================**
56. ATOMICITY SHOULD MATCH THE REAL DOMAIN
**============================================================**

A workflow should not automatically be treated as one indivisible operation
merely because its steps appear in one function.

In the parser:

    read/parse HTML
    persist product data
    archive source HTML

were initially handled too atomically. If parsing and database persistence
succeeded, failure to archive the source file was not sufficient reason to
invalidate the stored product information.

The chosen model is:

    parse + persist
    -> define successful product processing

    archive
    -> secondary operation whose failure should not invalidate successful
       parsing/persistence

Testing can therefore expose when code structure is more atomic than the real
domain requires.


**============================================================**
57. EXCEPTION BOUNDARIES SHOULD FOLLOW SEMANTIC RESPONSIBILITIES
**============================================================**

The parser originally placed persistence and archiving under the same
try/except. This allowed an archive failure to overwrite a successful parse
status with parsing_failed.

That was misleading because parsing itself had succeeded.

General principle:

    If two operations have different meanings of failure, they may need
    different exception boundaries.

For this crawler:

    parsing/persistence failure
        -> parse_status may become parsing_failed

    archive failure
        -> parse_status remains parsed_succeeded
        -> archive error is logged
        -> later products should still be processed


**============================================================**
58. REGRESSION TESTS
**============================================================**

A regression test protects correct behavior after a bug or design flaw has been
identified.

Typical sequence:

    discover problematic behavior
    -> define desired behavior
    -> write a test for that behavior
    -> fix production code
    -> test passes
    -> keep the test permanently

The archive-failure regression test protects:

    archive move raises
    -> parsed product data remains in the database
    -> parse_status remains parsed_succeeded
    -> original HTML remains in its original location

The bug does not need to have been discovered through the test. It can first be
found by reasoning about the code and then captured as a regression test.


**============================================================**
59. FAILURE CONTINUATION AS A SEPARATE CONTRACT
**============================================================**

Two related behaviors should be tested separately:

    Test A:
        archive failure does not invalidate successful parsing

    Test B:
        archive failure does not stop processing later products

The decisive evidence for Test B is that a second product reaches its successful
final state after the first product's archive failure.

This reinforces:

    One test should prove one primary behavioral contract.

A later test does not need to re-prove every fact already protected by an
earlier regression test.


**============================================================**
60. MINIMUM SUFFICIENT EVIDENCE
**============================================================**

A test should assert enough to prove its contract, but not automatically assert
every observable detail.

For example, to prove:

    archive failure on product 1 does not stop the loop

the strongest simple evidence is:

    product 2 reaches parsed_succeeded

It is unnecessary to repeat every assertion about product 1 if those facts are
already protected by another test.

Useful question:

    What is the minimum observable evidence that would be impossible if this
    contract were broken?


**============================================================**
61. PATCH ONLY NONDETERMINISM RELEVANT TO THE CONTRACT
**============================================================**

The parser creates an archive folder using the current date. That initially
suggested patching the time source.

For the archive-failure regression test, however, the date does not affect the
assertions. Therefore time does not need to be patched.

Refined rule:

    nondeterminism exists
    != automatically patch it

Patch nondeterminism only when its value can affect the behavior or evidence
relevant to the specific test.


**============================================================**
62. PATCH.OBJECT AND TEST SEAMS
**============================================================**

A new patching form was used to inject archive failure:

    patch.object(Path, "rename", ...)

Difference:

    patch("module.name")
        -> locate a target through a dotted string path

    patch.object(actual_object, "attribute")
        -> already have the object and temporarily replace one of its attributes

In:

    patch.object(Path, "rename")

Path is the class object and "rename" is the method/attribute being replaced.

With:

    side_effect=OSError("archive failed")

the patched rename method raises that exception when called. The exception
itself is not patched.

This is also an example of a test seam: a point where a dependency can be
replaced or controlled so a specific scenario can be created deterministically.


**============================================================**
63. CURRENT LEARNING POSITION: SOFTWARE RELIABILITY
**============================================================**

The current focus is now:

- selecting meaningful contracts;
- preferring state/outcome evidence when possible;
- using interaction evidence only when the interaction itself matters;
- injecting failures at precise points;
- reasoning about partial side effects;
- identifying consistency invariants;
- deciding what should and should not be atomic;
- aligning exception boundaries with semantic responsibilities;
- protecting corrected behavior with regression tests;
- proving loop continuation independently from local failure handling;
- choosing minimum sufficient evidence;
- avoiding unnecessary mocks and patches.

This is a transition from:

    testing tools

toward:

    test design
    failure semantics
    reliability reasoning
    maintainable regression protection

Database transactions and rollback — NOW PRACTICED.
This is the most natural next step from the partial-failure work we just did. In run_crawler_product_html_parser(), update_product_data() commits, and then update_parse_status() performs another commit. Imagine:

product DB update       ✓ committed
parsed_succeeded update ✗

You now have another partial state, but this time entirely inside the database. This would teach actual transactional testing, rollback, and when several DB operations should be atomic. This is genuinely new.

State-machine testing — NOW PRACTICED.
Your crawler already has implicit lifecycles:

Urls:
pending → in_progress → fetched / failed


ProductPages:
pending → fetching → fetched
                    ↓
                 parsing → parsed_succeeded / parsing_failed

Until now you have tested many transitions separately. We can move to asking:

Which transitions are legal? Which states should never occur? What happens after a crash and restart?

That introduces state-machine/model-based reasoning, not another pytest trick.

Application-level pipeline testing — IN PROGRESS.
main.py now has a real:

run_pipeline(stages, stage_pipeline, context)

with stage objects. This is excellent for learning orchestration testing at a higher level:

correct stage order
skipped stages genuinely skipped
context passed through
what happens when stage 3 fails?
should stage 4 run?

Here, execution order is actually a meaningful interaction contract, so it also deepens the state-vs-interaction distinction you just learned.

Contract tests across implementations.
Your site_registry() contains several site implementations, while the crawler stages expect those implementations to offer particular operations. This is not merely theoretical: ProductParserStage ultimately expects:

individual_product_data_extraction(...)

but the current Amazon class does not define that method, whereas BooksToScrape and MercadoLibre do.

That makes the project a good place to learn contract testing:

Every object registered as a supported site must satisfy the interface required by the crawler pipeline.

This is a strong software-testing concept.

Property-based testing.
Your pure functions are good candidates:

slugify(...)
build_pagination_url(...)
list_of_html_files_compiler(...)

Instead of manually giving 5 examples, you start asserting general properties over many generated inputs. For example:

slugify output contains only expected characters
slugify(slugify(x)) == slugify(x)
HTML page filenames are always numerically ordered

This would introduce Hypothesis/property-based testing, which is definitely new territory.

A controlled end-to-end “slice” test.
Not Selenium/Playwright against a live website. Rather:

real temporary SQLite
+ real temporary files
+ real crawler stages
+ saved/fake HTML
+ fake browser/network boundary

Then follow one product through several stages and verify its final DB/file state. This teaches how unit and integration tests combine into a system-level confidence test without making the suite dependent on the internet.

Later: concurrency/race-condition testing.
This is more advanced, but your queue logic eventually provides a real reason to learn it. Functions such as get_pending_product_url() perform a selection and then change the row's status. With multiple workers, you can ask whether two workers could claim the same job. That leads into concurrent DB testing, locking, and atomic job acquisition.


**============================================================**
64. TRANSACTION BOUNDARIES AND TRANSACTION OWNERSHIP
**============================================================**

A major new distinction is:

    function separation
    != transaction separation

It is reasonable to keep:

    update_product_data(...)
    update_parse_status(...)

as separate functions because they represent different database operations.

The problem appears when each helper commits independently.

If:

    update_product_data()
    -> UPDATE
    -> COMMIT

and then:

    update_parse_status("parsed_succeeded")
    -> fails

the first database change is already permanent. A later exception cannot undo a
previous commit.

The better design for operations that must succeed together is:

    helper functions
        -> execute their SQL
        -> do not decide the transaction boundary

    higher-level orchestrator
        -> decides which operations belong to one transaction
        -> commits or rolls them back together

General principle:

    The code that knows which operations form one logical unit should usually
    own the commit/rollback decision.


**============================================================**
65. DATABASE ATOMICITY
**============================================================**

The product parser established a concrete atomicity requirement.

These two operations belong to one logical database transaction:

    update product fields
    +
    set parse_status = "parsed_succeeded"

Desired contract:

    both succeed
    -> COMMIT both

    either fails
    -> ROLLBACK both

This is atomicity inside one resource: the SQLite database.

It differs from the earlier archive discussion.

For archive failure, the chosen design allowed:

    database persistence succeeds
    archive fails
    -> keep the database result

For the two database updates above, the chosen design is stricter:

    product-data update succeeds
    status update fails
    -> product-data update must not survive

Atomicity should therefore be decided according to the semantic relationship
between operations, not merely because operations happen to appear near each
other in the same function.


**============================================================**
66. COMMITTED JOB CLAIM VS ATOMIC COMPLETION TRANSACTION
**============================================================**

The parser contains an earlier transition:

    parse_status = "parsing"
    -> COMMIT

This serves a different purpose: it claims the job before parsing begins.

Therefore the workflow contains two meaningful transaction boundaries.

Transaction A: job claim

    NULL
    -> parsing
    -> COMMIT

Transaction B: successful completion

    update product fields
    update parse_status -> parsed_succeeded
    -> COMMIT together

If Transaction B fails:

    ROLLBACK

returns the row to the state that existed at the beginning of Transaction B:

    product fields unchanged
    parse_status still parsing

Important point:

    rollback does not mean "undo everything the function has ever done"

It means:

    undo the uncommitted changes in the current transaction.


**============================================================**
67. ROLLBACK AND RECOVERY AS TWO SEPARATE TRANSACTIONS
**============================================================**

After the successful-completion transaction fails, the crawler still needs to
record a recovery state:

    parse_status = "parsing_failed"

That recovery update is a new database change.

Therefore the failure path is:

    transaction being attempted:
        update product data
        update parsed_succeeded
        -> failure
        -> ROLLBACK

    recovery transaction:
        update parse_status -> parsing_failed
        -> COMMIT

Conceptually:

    try:
        update_product_data(...)
        update_parse_status(..., "parsed_succeeded")
        connection.commit()

    except Exception:
        connection.rollback()

        update_parse_status(..., "parsing_failed")
        connection.commit()

A commit immediately after rollback, before any new SQL operation, is not useful.
The recovery state must first be written and then committed.

Also:

    commit()
    rollback()

belong to the database connection because the connection owns the transaction.

The cursor executes SQL statements.


**============================================================**
68. TRANSACTIONAL FAILURE INJECTION
**============================================================**

To test rollback, the failure must happen after one database update has already
executed but before the transaction is committed.

The chosen scenario is:

    update_product_data(...)                -> succeeds
    update_parse_status("parsed_succeeded") -> forced failure
    connection.rollback()

Then recovery occurs:

    update_parse_status("parsing_failed")
    connection.commit()

The final expected database state is:

    product fields -> unchanged from before the failed transaction
    parse_status   -> parsing_failed

This proves that an earlier database mutation did not survive a later failure
inside the same transaction.


**============================================================**
69. FUNCTION-BASED SIDE_EFFECT: BEHAVIOR BASED ON ARGUMENTS
**============================================================**

Earlier tests used side_effect sequences:

    mock.side_effect = [Exception(), None]

That changes behavior according to call order:

    first call  -> raise
    second call -> succeed

The transaction test required different control.

The same dependency is called with two semantically different values:

    "parsed_succeeded"
    "parsing_failed"

The desired behavior is:

    if status == "parsed_succeeded":
        raise an artificial exception

    otherwise:
        allow normal behavior

A function can therefore be used as side_effect:

    def controlled_update_status(row_id, db, status):
        if status == "parsed_succeeded":
            raise Exception()

        return real_update_parse_status(row_id, db, status)

    mock.side_effect = controlled_update_status

Mock passes the actual call arguments into the side-effect function.

Useful distinction:

    side_effect sequence
        -> behavior depends on call number

    function-based side_effect
        -> behavior can depend on call arguments or arbitrary logic


**============================================================**
70. DELEGATING FROM A FAKE TO REAL PRODUCTION BEHAVIOR
**============================================================**

The transaction test needs only one behavior to be fake:

    setting parsed_succeeded must fail artificially

The recovery behavior should remain real:

    setting parsing_failed should execute the production SQL

This produces a useful pattern:

    fake the smallest behavior necessary to create the scenario
    and delegate everything else to real production behavior

Example:

    real_update_parse_status = update_parse_status

    def controlled_update_status(row_id, db, status):
        if status == "parsed_succeeded":
            raise Exception()

        return real_update_parse_status(row_id, db, status)

This avoids copying the production SQL into the test.

Duplicating SQL in a fake creates a maintenance risk:

    production implementation changes
    fake implementation does not
    -> test and production behavior can drift apart


**============================================================**
71. FUNCTION OBJECT VS FUNCTION CALL
**============================================================**

A debugging step clarified a basic Python distinction that matters inside test
doubles.

This:

    return update_parse_status

returns the function object itself.

It does not execute any SQL.

This:

    return update_parse_status(row_id, db, status)

calls the function and returns the result of that call.

In the rollback test, returning only the function object caused the recovery
update never to execute.

The database therefore remained at:

    parse_status = "parsing"

Calling the function correctly allowed the recovery SQL to run and the later
commit to persist:

    parse_status = "parsing_failed"

General distinction:

    function_name
        -> reference to the function object

    function_name(...)
        -> execute the function now


**============================================================**
72. PYTEST OUTPUT CAPTURE
**============================================================**

A temporary print was used to inspect the status received by the side-effect
function.

Example:

    print(f"STATUS RECEIVED IS {status}")

Pytest captures standard output by default. Therefore print() output from a
passing test may not appear directly in the terminal.

To see output live:

    pytest -s

or:

    pytest --capture=no

This is useful for temporary debugging.

Captured print output should not normally become part of the permanent test
contract; it is diagnostic evidence used while understanding execution.


**============================================================**
73. CURRENT LEARNING POSITION AFTER TRANSACTION TESTING
**============================================================**

The project has now been used to practice two different forms of partial
failure:

1. Cross-resource partial failure

       database succeeds
       filesystem archive fails

   Result:
       preserve valid database state because archive failure is secondary.

2. Intra-database partial failure

       first DB update succeeds
       second DB update fails before commit

   Result:
       rollback both because the two updates form one atomic database operation.

The testing questions are now increasingly:

    What is one logical transaction?
    Which state transitions deserve their own commit?
    Which changes must roll back together?
    Which recovery state should be committed afterward?
    Where should a failure be injected to prove those guarantees?

State-machine testing is now practiced. Remaining high-value crawler topics include:

    application-level pipeline testing
    contract tests across site implementations
    property-based testing
    controlled end-to-end slice testing
    later, concurrency/race-condition testing


**============================================================**
74. STATE-MACHINE TESTING: COMPOSITE PRODUCTPAGES STATE
**============================================================**

The ProductPages workflow introduced explicit state-machine reasoning.

A row's relevant state is not represented by parse_status alone. It is the
combination:

    (fetch_status, parse_status)

Examples of meaningful combined states include:

    ("pending", NULL)
    ("fetching", NULL)
    ("fetched", NULL)
    ("fetched", "parsing")
    ("fetched", "parsed_succeeded")
    ("fetched", "parsing_failed")
    ("failed", NULL)
    ("failed_unfetchable", NULL)

This changes the testing question from:

    Did one status column receive the expected string?

to:

    Is the complete row in a valid lifecycle state?

This is especially important because parse_status has meaning only in relation
to the result of the fetch stage.

State-machine testing therefore treats the database row as a model of the
workflow rather than as a collection of unrelated fields.


**============================================================**
75. TRANSIENT, INTERMEDIATE, AND TERMINAL STATES
**============================================================**

A state can be terminal for one stage while still being intermediate for the
whole application.

For example:

    ("fetched", NULL)

is terminal success for the fetching sub-process, because fetching is complete.
But it is still intermediate for the full ProductPages lifecycle, because the
HTML has not yet been parsed.

This produces nested state machines.

Simplified fetch lifecycle:

    pending
    -> fetching
    -> fetched

or:

    pending
    -> fetching
    -> failed / failed_unfetchable

Simplified parsing lifecycle after a successful fetch:

    NULL
    -> parsing
    -> parsed_succeeded / parsing_failed

The full ProductPages lifecycle combines those two dimensions.

A useful distinction is:

    transient state
        -> normal processing is expected to move the row somewhere else

    terminal state
        -> no further transition is expected during the normal workflow

For the parser:

    "parsing"

is transient. It should eventually resolve to:

    "parsed_succeeded"
    "parsing_failed"

or, after interruption recovery, back to:

    NULL

so that the job can be retried.


**============================================================**
76. STATE INVARIANTS AND INVALID COMBINATIONS
**============================================================**

A state invariant is a rule that should be true for every valid reachable state,
not merely after one particular function call.

Two useful ProductPages invariants were derived.

Invariant 1:

    if parse_status is not NULL
    -> fetch_status must be "fetched"

This rejects combinations such as:

    ("fetching", "parsing")
    ("pending", "parsing_failed")
    ("failed", "parsed_succeeded")

Invariant 2:

    if fetch_status is "failed" or "failed_unfetchable"
    -> parse_status must be NULL

Therefore these are valid terminal states:

    ("failed", NULL)
    ("failed_unfetchable", NULL)

whereas this would be invalid:

    ("failed", "parsing_failed")

The broader testing lesson is:

    branch test
        -> proves behavior under one arranged path

    invariant test
        -> protects a rule that should hold across the valid state space

An invariant can therefore catch bugs that do not belong to only one obvious
branch.

When several input cases express the same invariant, parametrization is a good
fit because the cases belong to the same behavioral equivalence class.

Example idea:

    fetch_status = "failed"
    fetch_status = "failed_unfetchable"

Both imply the same assertion:

    parse_status is NULL


**============================================================**
77. TRANSITION RULES AND TRANSITION GUARDS
**============================================================**

An invariant describes which states are valid.

A transition rule describes which movement between states is legal.

A guard describes the precondition that allows a transition to occur.

For get_fetched_product(), the important eligibility condition is represented by
SQL equivalent to:

    WHERE fetch_status = 'fetched'
    AND parse_status IS NULL

This is a transition guard.

Only a row satisfying that condition is eligible to move from:

    ("fetched", NULL)

to:

    ("fetched", "parsing")

This distinction is useful:

    invariant
        -> which states are allowed at all?

    transition
        -> which state may follow another state?

    guard
        -> what must already be true before that transition is allowed?

Testing workflow code becomes more precise when these three questions are kept
separate.


**============================================================**
78. LEGAL TRANSITIONS
**============================================================**

A legal-transition test was written around get_fetched_product().

Initial state:

    ("fetched", NULL)

Action:

    get_fetched_product(db)

Expected result:

    the product is returned
    +
    the persistent state becomes ("fetched", "parsing")

The test therefore verifies two pieces of observable behavior:

    returned value
    + persistent state transition

This is similar to earlier queue tests such as pending -> fetching, but the
state-machine framing makes the contract explicit:

    this transition is not merely what the implementation currently does;
    it is an allowed movement in the lifecycle model.


**============================================================**
79. FORBIDDEN TRANSITIONS
**============================================================**

State-machine testing also asks which transitions must never happen.

A successfully parsed row is terminal for the parser:

    ("fetched", "parsed_succeeded")

It must not be selected again and moved back to:

    ("fetched", "parsing")

The test arranges a row as parsed_succeeded, calls get_fetched_product(), and
checks:

    the row is not returned as eligible work
    +
    its state remains ("fetched", "parsed_succeeded")

This is a forbidden-transition test:

    parsed_succeeded
    -X-> parsing

A useful general pattern is:

    arrange a terminal or otherwise ineligible state
    -> invoke the operation that could incorrectly claim it
    -> prove that the transition does not occur

This protects lifecycle rules that may be invisible if tests only cover normal
successful movement.


**============================================================**
80. EXACT DOMAIN VALUES AND FALSE-POSITIVE TESTS
**============================================================**

The forbidden-transition test exposed a subtle test-quality issue.

The state was initially misspelled as:

    "parsed_suceeded"

instead of:

    "parsed_succeeded"

The test could still pass because get_fetched_product() checks:

    parse_status IS NULL

Any non-NULL string would make the row ineligible, including an invalid value
such as:

    "parsed_suceeded"
    "banana"

Therefore a green test would not necessarily prove that the real terminal domain
state behaves correctly.

The correction was to use the exact production state:

    "parsed_succeeded"

General lesson:

    A test can pass for the wrong reason if its arranged data does not represent
    the real domain state it claims to test.

This extends the earlier strength check:

    Could this test still pass if the behavior it claims to protect were not
    actually being exercised?

Test data itself must be semantically valid, not merely convenient for reaching
an assertion.


**============================================================**
81. RECOVERY TRANSITIONS AFTER INTERRUPTION
**============================================================**

A transient state can remain persisted if the process crashes between job claim
and completion.

The parser commits the claim:

    ("fetched", NULL)
    -> ("fetched", "parsing")
    -> COMMIT

If the process then stops unexpectedly, the database can legitimately contain:

    ("fetched", "parsing")

on the next program start.

The recovery rule is:

    ("fetched", "parsing")
    -> ("fetched", NULL)

The row remains fetched because the HTML already exists, but parse_status returns
to NULL so the parser can claim it again.

The recovery test therefore arranges:

    fetch_status = "fetched"
    parse_status = "parsing"

commits that state to reproduce a realistic persisted pre-crash condition, then
calls:

    reset_stuck_parsing_jobs(db)

and verifies:

    ("fetched", NULL)

Committing the initial parsing state matters conceptually because recovery is
intended to operate on a state that survived an earlier process execution.

This is different from normal failure handling:

    parsing exception during a live run
        -> parsing_failed

    process interruption leaves parsing persisted
        -> startup recovery resets it to NULL for retry

Recovery is therefore its own transition category, not merely another failure
branch.


**============================================================**
82. TEST SEAMS AND EXTRACTING A RECOVERY RESPONSIBILITY
**============================================================**

reset_stuck_parsing_jobs() was initially nested inside the public parser
function.

Testing recovery only through the full public function creates an observability
problem.

The sequence would be:

    ("fetched", "parsing")
    -> reset to ("fetched", NULL)
    -> main parser immediately selects the row again
    -> ("fetched", "parsing")
    -> parsed_succeeded / parsing_failed

The intermediate recovery state would disappear before the test could inspect
it.

Two legitimate approaches were identified.

Approach A: control downstream behavior

    run the public function
    + patch get_fetched_product() after recovery so it reports no work
    + inspect the reset state

This avoids changing production structure but couples the test more closely to
the orchestration sequence.

Approach B: extract reset_stuck_parsing_jobs() to module level

    arrange persisted parsing state
    -> call reset_stuck_parsing_jobs(db) directly
    -> assert reset state

The second approach was chosen because recovery already has a coherent,
independent responsibility.

General principle:

    Extracting a helper merely because pytest cannot conveniently reach it is
    not automatically good design.

    Extracting a helper is justified when the behavior represents a meaningful
    operation with its own contract and the extraction also clarifies production
    responsibilities.

This is another form of creating a test seam, but the seam follows the domain
rather than existing only for the test framework.


**============================================================**
83. STATE-MACHINE TESTING WITHOUT EXHAUSTIVE PERMUTATIONS
**============================================================**

The purpose of state-machine testing is not to generate every possible pair of
status strings.

The useful coverage obtained here comes from a small number of conceptually
different rules:

    legal transition:
        ("fetched", NULL)
        -> ("fetched", "parsing")

    forbidden transition:
        ("fetched", "parsed_succeeded")
        -X-> ("fetched", "parsing")

    recovery transition:
        ("fetched", "parsing")
        -> ("fetched", NULL)

    invariant:
        failed / failed_unfetchable
        -> parse_status must remain NULL

    broader invariant:
        parse_status is not NULL
        -> fetch_status must be fetched

These cases represent different testing ideas. Adding many more status
permutations would mostly repeat the same reasoning.

The stopping rule therefore remains:

    Add another state-machine test when it protects a distinct lifecycle rule,
    invariant, guard, or recovery behavior.

    Do not enumerate combinations merely because they can be generated.


**============================================================**
84. CURRENT LEARNING POSITION AFTER STATE-MACHINE TESTING
**============================================================**

The crawler has now been used to move from individual branch/state assertions to
explicit lifecycle modeling.

State-machine concepts now practiced include:

- composite state represented by multiple database columns;
- transient/intermediate states;
- terminal states;
- stage-relative terminality;
- nested state machines;
- valid and invalid state combinations;
- state invariants;
- transition rules;
- transition guards;
- legal transitions;
- forbidden transitions;
- recovery transitions after interruption;
- persisted crash/restart state;
- testing returned values together with persistent transitions;
- avoiding false positives caused by invalid test data;
- creating a test seam by extracting a meaningful recovery responsibility;
- stopping state-machine testing once the distinct lifecycle rules are covered.

The progression in the project is now roughly:

    pytest mechanics
    -> controlled dependencies and mocks
    -> integration across DB/files
    -> orchestration and continuation
    -> state vs interaction verification
    -> failure injection and regression protection
    -> partial failure and semantic exception boundaries
    -> database transactions and rollback
    -> state-machine and lifecycle testing

Application-level pipeline testing is now IN PROGRESS.

Practiced so far:

    execution order of enabled stages

Still to practice within this topic:

    skipped stages genuinely skipped
    context passed through correctly
    stage-failure and continuation/stop semantics

After that, the existing roadmap remains:

    contract tests across site implementations
    property-based testing
    controlled end-to-end slice testing
    later, concurrency/race-condition testing

**============================================================**
85. APPLICATION-LEVEL PIPELINE TESTING
**============================================================**

The next testing level reached in the crawler is application-level pipeline
testing.

The target is:

    run_pipeline(stages, stage_pipeline, context)

Earlier orchestration tests focused on one scraper loop or parser workflow.
run_pipeline() sits above those components. Its responsibility is to coordinate
the application's stage objects.

The first contract practiced is:

    given an ordered sequence of enabled stages
    -> run_pipeline() executes those stages
    -> in that same order

For example:

    seed
    -> search_scraper
    -> search_parser
    -> product_scraper
    -> product_parser

The test does not need the real crawler stages to prove this contract. Real
stages would introduce unrelated database, browser, parsing, and filesystem
behavior.

This is a higher-level orchestration test:

    the stage implementations are controlled
    the orchestration logic in run_pipeline() remains real


**============================================================**
86. EXECUTION ORDER AS A MEANINGFUL INTERACTION CONTRACT
**============================================================**

Earlier testing work established that interaction verification should not be
used merely to freeze implementation details.

Pipeline order is an important exception because the order itself affects
correctness.

For example:

    search_parser before search_scraper

would be semantically different from:

    search_scraper before search_parser

even if both stages eventually ran.

Therefore, for this test:

    execution order

is not incidental implementation detail. It is part of the observable contract.

This deepens the earlier state-vs-interaction rule:

    If changing an interaction while preserving all other behavior would still
    make the application incorrect, that interaction belongs to the contract.

The pipeline test therefore legitimately verifies:

    stage A ran before stage B
    stage B ran before stage C
    ...

rather than merely verifying that every stage was called at some point.


**============================================================**
87. MINIMAL FAKE STAGES FOR ORCHESTRATION TESTS
**============================================================**

A fake stage only needs to satisfy the interface that run_pipeline() actually
uses.

For the current implementation, that means providing:

    stage.key
    stage.display_name
    stage.run(context)

The fake does not need to implement:

    real scraping
    real parsing
    real database work
    real browser work

This is a deliberate test-boundary choice.

The question under test is:

    Does run_pipeline() coordinate the stages correctly?

not:

    Does each real stage perform its own job correctly?

Those lower-level contracts belong to their own tests.

General principle:

    Use the smallest fake that preserves the collaborator behavior relevant to
    the contract being tested.


**============================================================**
88. STATEFUL FAKES AS EXECUTION-HISTORY RECORDERS
**============================================================**

Stateful fakes were previously used mainly to model behavior that changes across
calls, such as:

    first call -> fail
    second call -> succeed

The pipeline test introduced another use.

Each fake stage records its execution in shared mutable state:

    run(stage)
    -> append stage.key to shared_state

After run_pipeline() finishes, the list contains a history such as:

    [
        "seed",
        "search_scraper",
        "search_parser",
        "product_scraper",
        "product_parser",
    ]

The shared state therefore preserves:

    which stages ran
    +
    the order in which they ran

This is useful when the contract concerns a global sequence across several
objects.

A stateful fake can therefore be used not only to change its future behavior,
but also to accumulate observable evidence about how the system interacted with
it.


**============================================================**
89. PER-STAGE FLAGS VS GLOBAL EXECUTION ORDER
**============================================================**

A fake stage may also contain:

    run_flag = False

and then:

    def run(...):
        self.run_flag = True

That flag can prove afterward:

    this particular stage ran

However, if all five stages have run_flag == True, that does not prove their
relative order.

The following facts:

    seed.run_flag == True
    search_scraper.run_flag == True
    search_parser.run_flag == True

are compatible with many different execution sequences.

Therefore:

    per-stage flag
        -> useful evidence for whether one stage ran

    ordered shared execution history
        -> useful evidence for global ordering

A related control-flow point was clarified.

Inside:

    def run(...):
        self.run_flag = True

        if self.run_flag:
            shared_state.append(self.key)

the if condition does not detect whether run() was called. If run() was never
called, none of the method body executes. Once execution has entered run(), the
assignment has already made run_flag True.

Therefore the conditional is redundant for recording execution:

    def run(...):
        self.run_flag = True
        shared_state.append(self.key)

The flag may still be kept if another test needs to inspect it directly.


**============================================================**
90. SHARED MUTABLE TEST STATE AND TEST ISOLATION
**============================================================**

The execution-history technique used a module-level list:

    shared_state = []

This state persists for the lifetime of the Python process.

If one test leaves entries in the list, a later test could observe those entries
and fail or pass for reasons unrelated to its own setup.

Therefore the test must deliberately start from a known state, for example:

    shared_state.clear()

during Arrange.

This reinforces a general test-isolation rule:

    A test should not depend on which other tests ran before it.

Shared mutable state can be useful, but its lifecycle must be controlled just
like temporary files, databases, mock call histories, or other test resources.


**============================================================**
91. ASSERTIONS MUST INSPECT EXECUTION EVIDENCE
**============================================================**

An early version of the pipeline test ended with:

    assert run_pipeline

This does not prove that the pipeline executed correctly.

run_pipeline in that expression is the function object itself. Function objects
are truthy, so the assertion succeeds simply because the function exists.

It would still pass if:

    the stages ran in the wrong order
    no stage ran
    run_pipeline's internal behavior were broken

The meaningful assertion instead inspects evidence produced by execution:

    actual execution history
    ==
    expected execution history

This is a concrete example of the earlier strength check:

    Could the test still pass if the production behavior it claims to test were
    removed or broken?

If yes, the assertion is not strong enough.

General lesson:

    assert function_name

usually says something about the object itself, not about the behavior produced
when the function was called.


**============================================================**
92. MOCK(CrawlerContext), INSTANCE ATTRIBUTES, AND PATCHED MOCKS
**============================================================**

The pipeline test also exposed a subtle difference between a plain Mock and a
Mock whose specification is based on CrawlerContext.

CrawlerContext creates fields such as:

    self.db
    self.paths_dict
    self.logger
    self.error_logger

inside __init__.

These are instance attributes. They do not exist merely because the class object
CrawlerContext exists.

Therefore:

    Mock(CrawlerContext)

can be more restrictive than expected when production code accesses attributes
such as:

    context.logger

because the class used as the spec may not expose attributes that are created
only after __init__ runs on a real instance.

By contrast:

    Mock()

is permissive. Accessing:

    mock_context.logger.info(...)

automatically creates child mocks as needed.

The test used:

    with patch("main.CrawlerContext") as mock_context:
        run_pipeline(..., mock_context)

This works, but the precise reason matters.

run_pipeline() does not construct CrawlerContext internally. The patch is not
intercepting a call such as:

    CrawlerContext(...)

inside run_pipeline().

Instead:

    patch() creates a permissive mock replacement
    +
    the test explicitly passes that mock as the context argument

So the mock works as the supplied dependency.

General lesson:

    Understand whether patch is affecting a lookup performed by production code
    or merely being used as a convenient way to obtain a test double.

Those are different reasons for a patch to appear effective.


**============================================================**
93. PYTEST IMPORT ROOTS AND TEST MODULE PATHS
**============================================================**

The project structure places main.py at:

    src/crawler_codebase/main.py

while crawler modules live under:

    src/crawler_codebase/crawler/

The project's pytest.ini adds:

    src/crawler_codebase

to pytest's Python import path.

Therefore tests can import the application-level function as:

    from main import run_pipeline

not:

    from crawler.main import run_pipeline

because main.py is not inside the crawler package.

This distinguishes two related concerns:

    editor/Pylance path configuration
        -> helps static import resolution in the editor

    pytest pythonpath configuration
        -> controls import resolution when pytest runs

A test's import path is determined by the project's actual package/import-root
configuration, not merely by the physical proximity of the test file to the
module under test.


**============================================================**
94. CURRENT LEARNING POSITION: PIPELINE TESTING IN PROGRESS
**============================================================**

Application-level pipeline testing has now begun.

Practiced so far:

    ordered stage pipeline supplied to run_pipeline()
    -> fake stages execute
    -> stateful execution history records the sequence
    -> actual order is compared with expected order

Concepts reinforced or extended:

- application-level orchestration as a separate test level;
- execution order as a meaningful interaction contract;
- minimal fake collaborators at the correct test boundary;
- stateful fakes used to record global execution history;
- distinction between per-object execution flags and global ordering evidence;
- shared mutable state and test isolation;
- assertion strength and false assurance from object truthiness;
- instance attributes versus class-based Mock specifications;
- distinguishing patch-as-interception from patch-as-a-source-of-a-test-double;
- pytest import roots for top-level application modules.

Application-level pipeline testing is not complete yet.

Still to practice:

    skipped stages genuinely skipped
    context passed through correctly
    stage-failure and continuation/stop semantics

The broader learning progression is now:

    pytest mechanics
    -> controlled dependencies and mocks
    -> integration across DB/files
    -> scraper orchestration and continuation
    -> state vs interaction verification
    -> failure injection and regression protection
    -> semantic exception boundaries
    -> database transactions and rollback
    -> state-machine and lifecycle testing
    -> application-level pipeline testing (in progress)

After pipeline testing, the planned topics remain:

    contract tests across site implementations
    property-based testing
    controlled end-to-end slice testing
    later, concurrency/race-condition testing


**============================================================**
95. SKIPPED STAGES AND CONTINUATION THROUGH THE PIPELINE
**============================================================**

Pipeline testing was extended to disabled stages.

The scenario selected was deliberately strong:

    seed             = disabled
    search_scraper   = disabled
    search_parser    = disabled
    product_scraper  = disabled
    product_parser   = enabled

The expected execution history contains only:

    product_parser

This single controlled scenario proves several related facts:

- disabled stages do not execute their run(context) methods;
- encountering a disabled stage does not terminate run_pipeline();
- the loop continues across several consecutive disabled stages;
- an enabled stage at the end of the pipeline is still reached and executed.

The relevant control-flow distinction is:

    continue
        -> stop the current loop iteration
        -> proceed to the next stage

    return
        -> exit run_pipeline() completely
        -> no later stage is considered

The test is therefore also a regression test against accidentally replacing
the disabled-stage continue with return.

General lesson:

    A boundary case can prove more than one branch property when the evidence
    remains exact and easy to interpret.


**============================================================**
96. CLASS BLUEPRINTS, INSTANCE ATTRIBUTES, AND MOCK SPECS
**============================================================**

The difference between a class and an initialized instance was consolidated.

CrawlerContext assigns attributes inside __init__:

    self.db = db
    self.paths_dict = paths_dict
    self.logger = logger
    self.error_logger = error_logger

These assignments run only when a CrawlerContext object is constructed.

Therefore:

    CrawlerContext
        -> is the class or blueprint
        -> does not itself contain the values assigned to self.logger, self.db,
           and the other instance fields

    CrawlerContext(...)
        -> constructs an instance
        -> runs __init__
        -> creates those attributes on that particular object

This is similar to constructor injection in C#:

    a dependency is passed into the constructor
    -> the constructor stores it on the new instance
    -> different instances may contain different dependency values

There is an important language difference. C# fields are normally declared in
the class definition. Python can create an attribute dynamically through:

    self.logger = logger

while __init__ is running.

That explains the observed mock behavior:

    Mock(CrawlerContext)
        -> uses the class as a specification
        -> may reject logger because logger is created only on instances

    Mock()
        -> is permissive
        -> accessing mock.logger creates a child mock automatically

If logger were assigned directly in the class body:

    class CrawlerContext:
        logger = ...

then it would be a class attribute and a class-based mock specification could
see it.

The production class should not be changed merely to make a test double easier
to construct. For the pipeline tests, a plain Mock() is sufficient because the
test needs only a context-like object with a usable logger and a stable identity.


**============================================================**
97. CONTEXT PASS-THROUGH, OBJECT IDENTITY, AND CARDINALITY
**============================================================**

The next pipeline contract tested was context pass-through:

    run_pipeline() receives one context object
    -> every enabled stage receives that exact same object

The contract concerns object identity, not merely type or equal values.

Two different CrawlerContext objects could contain equivalent data while still
being different objects. The relevant comparison is therefore:

    received_context is original_context

not merely:

    received_context == original_context

The fake stages record received contexts in a separate list:

    shared_state
        -> records stage keys and execution order

    received_contexts
        -> records context object references

Keeping these evidence streams separate makes each assertion easier to reason
about.

The test also exposed an empty-collection false positive.

An initial helper returned False when it found a different context and True at
the end. If received_contexts were empty, the loop would execute zero times and
the helper would incorrectly return True.

The same principle appears with Python's built-in all():

    all([]) == True

That behavior is mathematically consistent, but it can create weak test evidence
if the test forgets to prove that collaborators actually produced observations.

The corrected evidence has two parts:

    cardinality:
        exactly five contexts were recorded for five enabled stages

    identity:
        every recorded context is the original context object

The count check must occur before a loop over the collection. A check placed
inside the loop cannot detect an empty list because the loop body never runs.

General lesson:

    When verifying every item in a collection, also prove that the collection
    contains the number of observations required by the contract.


**============================================================**
98. MOCKED COLLABORATORS MUST SATISFY THE USED INTERFACE
**============================================================**

The stage-failure test used a Mock as the failing search-scraper stage.

A first attempt created a callable mock with an exception side_effect. However,
run_pipeline() does not call the stage object itself. It uses three members:

    stage.key
    stage.display_name
    stage.run(context)

Therefore the mocked stage must provide that interface.

The members serve different production purposes:

    key
        -> looks up whether the stage is enabled in the stages dictionary

    display_name
        -> supplies the human-readable name used in log messages

    run(context)
        -> performs the stage behavior

A plain Mock creates child mocks for unknown attributes. That permissiveness
does not automatically make their values semantically correct.

For example, if stage.key remains an automatically created child mock, then:

    stages[stage.key]

does not look up the string key "search_scraper" required by the configuration.

General lesson:

    A permissive mock prevents some AttributeError failures, but the test author
    must still configure values that production code interprets semantically.


**============================================================**
99. SIDE_EFFECT BELONGS ON THE METHOD ACTUALLY CALLED
**============================================================**

The failure test reinforced the rule:

    Configure behavior on the lookup and call performed by production code.

Attaching side_effect to the stage object means the exception occurs only if
production calls:

    stage(...)

But run_pipeline() calls:

    stage.run(context)

Therefore the exception side_effect belongs on the run mock.

This is closely related to the earlier patching rule:

    patch where a name is looked up

The more general formulation is:

    attach controlled behavior to the exact collaborator operation used by the
    production path under test.


**============================================================**
100. EXPECTED STAGE FAILURE AND STOP SEMANTICS
**============================================================**

The final unfinished pipeline contract concerned stage failure.

The selected scenario was:

    seed succeeds
    -> search_scraper is attempted
    -> search_scraper raises RuntimeError
    -> later stages do not run

run_pipeline() contains no try/except around stage.run(context). Therefore the
current contract is stop semantics:

    the exception propagates out of run_pipeline()
    +
    the for loop ends immediately

The outer main() function catches the exception later and its finally block
closes the database, but run_pipeline() itself does not continue to later stages.

The test uses:

    pytest.raises(RuntimeError)

This declares the exact failure type as expected and allows the test to inspect
evidence after the exception.

Two kinds of evidence are combined:

    shared_state == ["seed"]
        -> the earlier stage completed
        -> normal later fake stages did not run

    failing_stage.run.assert_called_once_with(fake_context)
        -> the failing stage was attempted exactly once
        -> it received the correct context

This distinction matters. An execution history containing only seed would not,
by itself, prove where the exception originated. The mock-call assertion ties
the expected failure to the intended collaborator operation.

Using RuntimeError rather than a broad Exception expectation also reduces the
chance that an unrelated programming error accidentally satisfies the test.


**============================================================**
101. CURRENT LEARNING POSITION: PIPELINE TESTING COMPLETE
**============================================================**

Application-level pipeline testing is now complete for the current
run_pipeline() contract.

Practiced and passing:

    all enabled stages execute in order
    disabled stages are genuinely skipped
    consecutive skips do not terminate the pipeline
    an enabled final stage is still reached
    the same context object is passed to every enabled stage
    context evidence includes both exact count and identity
    a stage exception propagates
    a stage exception stops later stages
    the failing stage is proven to have been attempted

Concepts newly consolidated:

- continue versus return inside a stage loop;
- boundary scenarios for orchestration tests;
- class blueprints versus initialized instances;
- constructor-created Python attributes;
- permissive Mock objects versus class-based specifications;
- object identity with is;
- separating execution-order evidence from context evidence;
- collection cardinality as protection against empty-evidence false positives;
- all([]) and vacuous truth in test assertions;
- mocked collaborators satisfying a semantic interface;
- attaching side_effect to the method production actually calls;
- expected exception testing with a specific exception type;
- combining stateful fake history with mock interaction assertions;
- stop semantics at the application pipeline level.

The broader learning progression is now:

    pytest mechanics
    -> controlled dependencies and mocks
    -> integration across DB/files
    -> scraper orchestration and continuation
    -> state vs interaction verification
    -> failure injection and regression protection
    -> semantic exception boundaries
    -> database transactions and rollback
    -> state-machine and lifecycle testing
    -> application-level pipeline testing (complete)

The next planned topic is:

    contract tests across site implementations


**============================================================**
102. NEXT TOPIC: CONSUMER-DRIVEN CONTRACT TESTS FOR SITE ADAPTERS
**============================================================**

The crawler has three registered site adapters:

    BooksToScrape
    Amazon
    MercadoLibre

The next learning step should begin with contract discovery, not immediately
with a parametrized test.

A useful contract is defined by what downstream crawler stages require from a
site adapter. Reading the current consumers reveals several interfaces.

Seed-stage requirements:

    pagination_mode
    build_pagination_url(base_url, page_number)
    discover_first_paginated_url(seed_url) when pagination_mode is dynamic

Search-scraper requirement:

    selector_to_start_process

Search-parser requirements:

    product_extraction(soup)
        -> returns an iterable collection
        -> each product used for insertion contains a "link" key

Product-scraper requirement:

    wait_selector

Product-parser requirements:

    individual_product_data_extraction(soup)
        -> returns a product dictionary containing:

            slug
            currency
            price
            product_code
            reviews
            images

        -> images contains at least one element because images[0] is read

This is an especially appropriate next topic because the current abstract base
class requires only product_extraction(), while the pipeline consumers rely on
additional attributes and methods.

The current adapters also contain candidate contract discrepancies worth
discovering through tests rather than assuming away:

- Amazon.product_extraction() currently builds dictionaries without "link",
  while insert_product_url() reads individual_product["link"];
- Amazon and MercadoLibre should be checked against the product scraper's
  wait_selector requirement;
- Amazon should be checked against the individual-product extraction contract;
- BooksToScrape.product_extraction() may return None when no containers exist,
  while the search parser immediately calls len() on the result.

These observations should first become explicit contract questions:

    Is the consumer requirement intentional?
    Should every registered adapter satisfy it?
    Is the method required for every site or only for sites using a certain
    pipeline stage?
    Should an empty extraction return [] or None?

Only after deciding those domain contracts should the tests be written.

Recommended learning sequence:

    1. Map each crawler consumer to the adapter members it uses.
    2. State one minimal shared contract in plain language.
    3. Write one test against one adapter.
    4. Parametrize the same contract across registered adapters.
    5. Observe genuine interface failures without weakening the test.
    6. Decide whether production adapters or the declared contract should
       change.
    7. Consider making the interface explicit with an ABC, Protocol, or separate
       capability contracts only after the tests clarify the design.

This topic will connect testing to architecture:

    repeated contract-test failures
    -> reveal interface inconsistency
    -> motivate a clearer adapter boundary


**============================================================**
103. LEARNING DIRECTION: DEPTH RATHER THAN COMPLETENESS
**============================================================**

The crawler already has substantial tests covering:

- pure input/output behavior;
- parametrization and fixtures;
- mocks, fakes, autospec, patch, call histories, and side_effect;
- retry paths and exception control flow;
- real temporary filesystem and SQLite integration;
- scraper-loop success, failure, and continuation;
- database state transitions and recovery;
- cross-resource partial failure;
- transactions, rollback, and recovery transactions;
- state-machine and lifecycle behavior;
- application-level pipeline orchestration.

The next goal is not:

    test every remaining function and branch for completeness

The next goal is:

    use this crawler to learn testing techniques that expose new categories of
    risk or provide a new kind of evidence

This changes how future exercises should be selected.

A proposed test should answer:

    What new testing concept does this teach?
    What risk can this technique reveal that the existing suite cannot reveal
    as clearly?
    Is the chosen crawler behavior important enough to justify the exercise?

Tests that merely repeat familiar Arrange/Act/Assert patterns against another
small helper should normally be skipped unless they are being used briefly to
learn the mechanics of a genuinely new technique.


**============================================================**
104. PROPERTY-BASED SLUGIFY TESTING: USEFUL TECHNIQUE, WEAK NEXT TARGET
**============================================================**

The existing slugify tests already practice example-based parametrization.

Adding more hand-written slug examples would be a step backward relative to the
current learning position. It would repeat:

    pure input/output testing
    parametrized examples
    exact expected-value assertions

Property-based testing itself is not a step backward.

It introduces genuinely new concepts:

- generated inputs;
- properties and invariants rather than individual examples;
- shrinking a failure to a minimal counterexample;
- separating the input domain from a few values imagined by the test author.

However, slugify is a pedagogical toy for this technique. It is deterministic,
pure, and easy to reason about, so it can be used as a short Hypothesis syntax
exercise. It should not become the next main learning phase.

For deeper learning, property-based techniques should later be applied to the
crawler's database lifecycle through model-based or stateful testing.

Conclusion:

    more example-based slugify tests
        -> a step backward

    a brief property-based slugify exercise
        -> acceptable as a tool warm-up

    property-based state-machine testing of crawler jobs
        -> the meaningful advanced target


**============================================================**
105. MUTATION TESTING AND TEST-SUITE ADEQUACY — PHASE COMPLETE
**============================================================**

Traditional execution asks:

    Does the test suite pass against the current program?

Mutation testing asks:

    If the program were subtly wrong, would the test suite notice?

The crawler mutation phase was practiced manually and with Cosmic Ray.

Manual mutations covered meaningful crawler contracts such as:

    remove page_counter += 1
    change fetched to failed
    remove commit()
    replace continue with return in pipeline orchestration
    remove rollback() from parser recovery

The automated phase then ran Cosmic Ray against crawler_product_scraper.py.
The first automated session generated 87 jobs. All jobs completed and the report
showed 33 survivors, a survival rate of 37.93%.

The percentage was treated as a diagnostic summary rather than a quality target.
The important work was survivor classification.

Two especially useful automated survivors were investigated:

1. No-product-URL branch:

       continue
       -> break

   The old test used only one no-URL row, so continue and break were
   observationally equivalent in that scenario. A focused continuation test with
   a later valid product killed the mutant.

2. Special-wait condition:

       page_counter != 0
       -> page_counter == 0

   The old assertion used assert_any_call(6). Because another wait branch could
   independently produce countdown_sleep_timer(6), the evidence was compatible
   with the intended branch without uniquely proving it. Refactoring the special
   wait behind a helper created a better test boundary and a focused helper test
   killed the mutant.

Important mutation-testing conclusions now practiced:

- a surviving mutant is a question, not automatically a defect;
- a killed mutant proves that some test distinguishes the changed behavior, not
  that every semantic aspect of the mutation is directly tested;
- mutation testing can expose missing scenarios, ambiguous evidence, or a poor
  test boundary;
- syntax-driven mutation tools generate noise, including meaningless mutations of
  type-hint operators;
- an interaction assertion can be technically valid yet non-discriminating;
- mutation score should guide investigation, not become a target to maximize;
- source refactoring can make an old mutation session stale;
- tests should not be added merely to kill low-value mutants.

The automated session was sufficient for the learning objective because it added
what manual mutation testing could not:

    automatic mutant generation
    -> many mutants at once
    -> survivor reports
    -> classification at scale
    -> tool noise and stale-session reasoning

No additional Cosmic Ray run is currently required. Mutation testing can be
revisited later when there is a specific regression-risk question, but it is no
longer the active learning phase.

**============================================================**
106. CONSUMER-DRIVEN SITE-ADAPTER CONTRACTS — NOW PRACTICED
**============================================================**

The contract-testing phase moved from architectural planning to direct tests
against the real site adapters.

The central method practiced was:

    identify a real consumer
    -> inspect what it actually reads or calls
    -> state only the promise the consumer requires
    -> apply that same promise to participating providers
    -> treat failures as architectural evidence rather than weakening the test

This differs from starting with a provider and asking what all of its methods do.
The consumer determines the relevant contract.

A. Search-parser product_extraction() contract

The search parser ultimately consumes product dictionaries through a "link" key.
The first contract test used BooksToScrape as the controlled reference provider,
then applied the same assertions to MercadoLibre and Amazon.

The successful-extraction contract practiced was approximately:

    product_extraction(soup)
        -> returns the agreed collection type for a successful extraction
        -> extracted product is a dictionary
        -> product dictionary contains "link"

An important correction was made during the exercise:

    "link" exists
    !=
    "link" is always a usable URL

The current crawler explicitly tolerates:

    {"link": None}

because the downstream product scraper has a failed_unfetchable path for product
rows whose URL is None. Therefore the shared contract should not silently become
stronger than the real application behavior.

Another distinction was clarified:

    provider-specific parsing test
        -> may assert the exact URL extracted from one BooksToScrape page

    shared contract test
        -> asserts only the properties the consumer depends on

The contract test used small provider-specific HTML inputs while keeping the
contract assertions identical. This made the separation visible:

    different HTML structure
    + different adapter implementation
    -> same consumer-facing promise

Observed provider results:

    BooksToScrape   -> PASS
    MercadoLibre    -> PASS
    Amazon          -> XFAIL because its product dictionaries currently omit
                       the "link" key

The empty/no-container case remains intentionally separate from the successful
contract. BooksToScrape currently returns None when its expected product
containers are absent. It has not yet been decided whether:

    None -> extraction structure unavailable / extraction failure
    []   -> valid extraction with zero products

should remain distinct semantics or be unified.

B. Parametrized provider verification

pytest.mark.parametrize() was used to apply one contract to several providers.

A clearer syntax for multiple parameter names was learned:

    @pytest.mark.parametrize(
        ("adapter_class", "test_html"),
        [
            (BooksToScrape, books_html),
            (MercadoLibre, ml_html),
            ...
        ],
    )

The first argument may be a comma-separated string, but a tuple of names can make
the positional structure more explicit.

The conceptual mapping is:

    ("adapter_class", "test_html")
              ^              ^
              |              |
        (BooksToScrape, books_html)

Each row runs the same test again with new values.

A distinction was also consolidated:

    fixture
        -> value supplied by pytest's fixture system

    parametrized argument
        -> value supplied by one row of @pytest.mark.parametrize

They can appear together in the same test function, but they are not the same
mechanism.

Parametrization is per test. A later contract that needs only adapter_class does
not need to reuse the earlier (adapter_class, test_html) pair.

C. isinstance() and runtime type evidence

The contract exercise introduced isinstance():

    isinstance(object, expected_type)

Examples:

    isinstance(result, list)
    isinstance(product, dict)

A failed attempt clarified an important Python distinction:

    isinstance(result, list[dict])

raises:

    TypeError: isinstance() argument 2 cannot be a parameterized generic

because:

    list
        -> runtime class usable by isinstance()

    list[dict]
        -> parameterized generic primarily used for static type description

Therefore a runtime test decomposes list[dict] into separate evidence:

    result is a list
    + each relevant element is a dict

The existing all([]) / vacuous-truth lesson still applies if all elements are
checked with all(...). A successful fixture should separately prove that at least
one product was actually extracted when non-empty evidence is required.

D. xfail and XPASS for known provider incompatibilities

pytest.mark.xfail was introduced through incomplete adapters.

Mental model:

    XFAIL
        -> this real test still runs
        -> current failure is known and documented

    XPASS
        -> the case unexpectedly satisfied the contract
        -> the old xfail may now be stale and removable

A parametrized case can carry its own expected-failure mark:

    pytest.param(
        Amazon,
        amazon_html,
        marks=pytest.mark.xfail(reason="known contract gap"),
    )

This differs from pytest.raises():

    pytest.raises(...)
        -> asserts that production behavior should raise a specific exception

    xfail
        -> records that the whole current test case is expected not to satisfy its
           assertion yet

It also differs from skipping:

    skip
        -> do not execute the test

    xfail
        -> execute it and observe whether the known failure still exists

The useful analogy developed was an executable post-it attached to a known
incompatibility.

E. Product-scraper wait_selector capability contract

The product scraper reads:

    specific_site_config.wait_selector

before passing the value into its fetch dependency. This creates a capability
contract:

    any adapter actually participating in the product-scraping stage
    -> must expose wait_selector

This is narrower than:

    every site adapter in the project must expose wait_selector

because the current adapters are not all complete implementations of every
pipeline stage.

The first version of the test called process_single_url() and contained no explicit
assertion. That test could still fail through an uncaught AttributeError, but it
also dragged unrelated behavior into the test boundary.

The test was refined to direct structural evidence:

    assert hasattr(adapter, "wait_selector")

This introduced hasattr() and reinforced the minimum-sufficient-evidence rule:

    if the contract is attribute existence,
    test attribute existence directly

rather than executing a whole downstream workflow that can fail for unrelated
reasons.

Observed provider results:

    BooksToScrape   -> PASS
    MercadoLibre    -> XFAIL: wait_selector currently absent
    Amazon          -> XFAIL: wait_selector currently absent

This exposed a capability/interface question without forcing unfinished adapters
to implement every stage immediately.

F. Contract tests as executable architecture checks

The most important conceptual result of the phase is that contract tests rapidly
surface explicit and implicit architectural assumptions.

For example:

    individual_product["link"]

silently implies a provider promise even if no formal Protocol or abstract method
states it.

The shared test turns that hidden dependency into executable evidence.

Repeated provider failures can therefore motivate later architectural choices such
as:

    narrower capability interfaces
    Protocols
    abstract base classes
    explicit declarations of which pipeline stages an adapter supports

The tests should clarify those boundaries before the architecture is formalized.

**============================================================**
107. MODEL-BASED AND STATEFUL PROPERTY TESTING
**============================================================**

The project has already tested individual legal, forbidden, terminal, and
recovery transitions.

The deeper next step is to build an independent model of the job lifecycle and
generate sequences of actions.

A simplified product lifecycle model could include:

    pending
    -> fetching
    -> fetched
    -> parsing
    -> parsed_succeeded

with failure and recovery branches such as:

    fetching -> failed
    parsing -> parsing_failed
    interrupted fetching -> pending
    interrupted parsing -> unparsed/fetched recovery state

Generated actions could include:

    claim a pending product
    report fetch success
    report fetch failure
    claim a fetched product for parsing
    report parse success
    report parse failure
    simulate interruption
    perform recovery

After every generated action:

    compare the real SQLite row with the independent model
    verify global state invariants

This teaches:

- model-based testing;
- stateful property testing;
- generated operation histories;
- invariants checked after every transition;
- shrinking a long failing sequence to its minimal cause;
- discovering bugs caused by combinations rather than one isolated branch.

This is the recommended serious application of property-based testing in the
crawler.


**============================================================**
108. CONTROLLED END-TO-END SLICE TESTING
**============================================================**

After adapter contracts and model-based lifecycle testing, create one controlled
local end-to-end slice.

Use BooksToScrape because it is the configured educational site and saved HTML
fixtures already exist.

Recommended local slice:

    seed URL generation
    -> temporary SQLite database
    -> saved search HTML fixture
    -> search parsing and ProductPages insertion
    -> saved product HTML fixture
    -> product parsing and final database fields

Keep real:

    SQLite
    filesystem in tmp_path
    BeautifulSoup parsing
    BooksToScrape adapter
    crawler stage functions

Replace or exclude:

    live network access
    Playwright browser launch
    random sleep and scrolling

The evidence should be final database state and relevant archived-file state,
not a long list of internal calls.


New concepts to emphasize:

- choosing a vertical slice rather than testing the entire application;
- deciding which boundaries remain real and which remain controlled;
- detecting incompatible assumptions between components that pass separately;
- final-state evidence at a system boundary;
- diagnosing failures in a broader test without replacing it with internal-call
  assertions.

This exercise is valuable, but it is less conceptually new than mutation or
contract testing because the existing suite already combines real files,
SQLite, parsing, and production functions.


**============================================================**
109. DETERMINISTIC CONCURRENCY AND ATOMIC JOB CLAIMING
**============================================================**

Delay this until the controlled end-to-end slice is stable.

The strongest future candidate is job claiming in SQLite:

    two workers attempt to claim the same pending or fetched row
    -> no row should be processed twice
    -> state transitions remain legal
    -> interruption recovery does not return actively owned work prematurely

This topic may require a production change because the current select-then-update
claim sequence should first be evaluated for atomicity under multiple database
connections.


The learning objective is not to run the same test repeatedly and hope for a
rare failure.

The learning objective is to force a meaningful interleaving with two workers
or two SQLite connections.

New concepts:

- deterministic race orchestration;
- barriers and controlled interleavings;
- database isolation;
- atomic claims;
- linearizability;
- distinguishing a concurrency invariant from an implementation detail;
- proving that one job cannot be owned by two workers simultaneously.


**============================================================**
110. EXCEPTION SAFETY AND RESOURCE OWNERSHIP
**============================================================**

Another advanced, bounded topic is cleanup at the application's composition
root.

Relevant resources include:

    SQLite cursor and connection
    Playwright browser and context
    temporary and final HTML files

Questions worth testing include:

    If pipeline execution fails, is the database still closed?
    Is each owned resource closed exactly once?
    What happens when initialization fails halfway through?
    Can cleanup failure hide the original application failure?
    Which function owns each resource's lifecycle?

This teaches:

- composition-root testing;
- resource ownership;
- setup/work/teardown failure injection;
- cleanup guarantees;
- exception safety;
- preserving the primary failure while reporting cleanup problems.

This should be kept narrow. The goal is not to mock every line of main(), but to
prove a small number of important lifecycle guarantees.


**============================================================**
111. OPTIONAL METAMORPHIC TESTING FOR HTML PARSERS
**============================================================**

Metamorphic testing is a useful optional topic for the site parsers.

Instead of creating a new exact expected result for every HTML input, start with
a valid saved fixture and apply transformations that should preserve meaning:

    add irrelevant elements
    change whitespace
    reorder unrelated attributes
    add non-product containers
    alter formatting without changing product values

Then verify:

    original extraction == transformed extraction

This teaches:

- metamorphic relations;
- testing when a separate exact oracle is expensive;
- robustness against semantically irrelevant input changes;
- distinguishing intentional selector contracts from accidental dependence on
  fixture formatting.

This is more valuable than adding many hand-written parser examples, but it is
lower priority than mutation, contracts, and lifecycle modeling.


**============================================================**
112. HISTORICAL ADVANCED ROADMAP — SUPERSEDED BY CURRENT STATUS
**============================================================**

At this earlier point in the learning process, the recommended sequence was:

    mutation testing
    -> consumer-driven contracts
    -> model-based/stateful property testing
    -> controlled local end-to-end slice
    -> deterministic concurrency
    -> exception safety/resource ownership
    -> optional metamorphic parser testing

That overall progression remains useful, but the status has changed:

    mutation testing
        -> now complete for the current learning goals

    consumer-driven contracts
        -> now practiced through product_extraction and wait_selector contracts
        -> one final individual-product parser contract is in progress

The current actionable roadmap is recorded in sections 123-124. This section is
kept as a historical record of how the advanced sequence was originally planned.

**============================================================**
113. MANUAL MUTATION TESTING: REAL CRAWLER RESULTS
**============================================================**

Mutation testing moved from theory to direct experiments against
scrape_product_urls().

The working method was:

    choose one meaningful production behavior
    -> introduce one small deliberate defect
    -> predict which existing test should detect it
    -> run the relevant test
    -> inspect the exact failing or surviving evidence
    -> restore production code

This is preferable to changing arbitrary lines. The mutation should represent a
plausible defect in a contract that matters to the crawler.

The first three product-scraper mutations were practiced as follows.
Additional application-level and rollback mutations are recorded later.

1. Remove the successful page-counter increment

   Production behavior:

       successful write
       -> product_N.html is created
       -> page_counter += 1

   Mutation:

       remove page_counter += 1

   Two existing tests behaved differently.

   test_page_counter_does_not_advance still passed.

   That did not make the test useless. Its contract is narrower:

       failed product
       -> must not consume the next filename number

   The test has no later successful product after the increment point from which
   it could observe whether a successful write actually advanced the counter.

   test_scrape_urls_happy_path_two_urls failed.

   Normal behavior:

       first success  -> product_1.html
       counter = 2
       second success -> product_2.html

   Mutated behavior:

       first success  -> product_1.html
       counter remains 1
       second success -> product_1.html again

   The killing assertion was the observable filesystem consequence:

       assert html_path_2.exists()

   General lesson:

       A test may survive one mutation because it protects a different contract.
       Ask what the test actually observes rather than judging it only by whether
       it killed a particular mutant.

   Another lesson is the importance of an observation point. If a state change
   matters only to later behavior, the test needs later behavior that exposes the
   missing change.

2. Change the successful database status from fetched to failed

   Mutation:

       status='fetched'
       -> status='failed'

   The test still proved that:

       fetch_html was called correctly
       product_1.html existed
       product_2.html existed
       both files contained the expected HTML

   It then failed on database-state evidence:

       assert result[0] == 'fetched'

   This demonstrated that one workflow can be correct in several observable
   dimensions and still violate another part of its contract:

       fetching          correct
       file creation     correct
       file contents     correct
       persistent status wrong

   General lesson:

       Strong orchestration tests often combine different evidence types because
       the workflow contract itself spans several resources or states.

3. Remove commit() from update_fetch_status_in_product_pages()

   Mutation:

       execute UPDATE
       -> do not commit

   The existing same-connection database assertions initially still passed.

   This produced a genuine surviving mutant relative to that evidence.

   The reason was not that commit() was irrelevant. The test was reading through
   the same SQLite connection that performed the UPDATE, and that connection can
   observe its own current uncommitted transaction state.

   The test boundary was therefore strengthened by opening a second connection to
   the same temporary SQLite database file.

   Important distinction:

       two connections to the same database file
       !=
       two different temporary database files

   The second connection supplied evidence about committed visibility rather than
   merely the first connection's private transaction state.

   An additional subtlety appeared with two products.

   Product 1's final fetched update had no explicit commit under the mutation, but
   a later commit performed while claiming product 2 committed the current
   transaction, including product 1's earlier uncommitted update.

   Therefore product 1 could still appear fetched from connection 2.

   Product 2 exposed the defect more clearly:

       product 2 claimed
       -> status = fetching
       -> COMMIT
       -> scraping succeeds
       -> status = fetched
       -> missing COMMIT mutation
       -> no later commit occurs

   Connection 1 saw fetched.
   Connection 2 still saw fetching.

   The second-connection assertion therefore killed the mutant:

       expected: fetched
       observed: fetching

General mutation-testing lessons consolidated by these experiments:

- killed means that at least one test detects the introduced defect;
- surviving means the current evidence does not distinguish the mutant from the
  original behavior, or the mutation may be behaviorally equivalent;
- a surviving mutant is a prompt to inspect the contract and the evidence, not an
  automatic instruction to add an assertion;
- a test surviving one mutant does not imply that the test is weak if it protects
  another meaningful contract;
- mutations are most useful when tied to domain behavior such as filenames,
  lifecycle states, transaction durability, continuation, or ordering;
- mutation testing can reveal that an assertion observes the right value through
  the wrong boundary;
- strengthening the boundary can be more valuable than adding more mock
  assertions;
- the goal remains protection of important behavior, not a perfect mutation
  score.


**============================================================**
114. SQLITE TRANSACTION VISIBILITY AS TEST EVIDENCE
**============================================================**

The missing-commit mutation clarified several transaction concepts that are
important for testing SQLite workflows.

1. SQL execution and transaction durability are different facts

   This:

       cursor.execute("UPDATE ...")

   proves that an update was issued inside the current transaction.

   This:

       connection.commit()

   establishes the transaction boundary that makes the current transaction's
   changes committed.

2. Same-connection reads can be weak evidence for commit behavior

   Under the normal SQLite setup used by this project, the connection that issued
   an UPDATE can read its own uncommitted change.

   Therefore:

       connection 1: UPDATE -> no commit -> SELECT

   may still show the new value.

   A same-connection SELECT can prove that the UPDATE affected the transaction,
   but it does not by itself prove that the state is committed.

3. A second connection can provide stronger commit evidence

   For the temporary test database:

       connection 1 ----\
                         -> same temp_db.sqlite
       connection 2 ----/

   connection 2 gives a separate observation boundary.

   The contract tested in the product-scraper happy path became:

       successful scrape
       -> final fetch_status is fetched
       -> that final state is committed
       -> another connection can observe fetched

4. commit() belongs to the transaction, not to one SQL statement

   A later commit on the same connection can also commit earlier uncommitted
   changes that remain in the current transaction.

   This explained why product 1 did not expose the missing final-status commit:
   the later product-claim commit also made product 1's fetched update durable.

   Product 2 was a better observation point because no later commit masked its
   missing final commit.

5. Contract evidence is stronger than implementation evidence when possible

   This interaction assertion:

       mock_commit.assert_called()

   would prove that code invoked a method named commit.

   The second-connection state assertion proves the behavior the rest of the
   system needs:

       the final state is actually committed and externally observable

   The latter is preferable for this contract.

   It also keeps the test less coupled to where the transaction boundary is
   implemented. If transaction ownership later moves to a higher-level
   orchestrator but the same durability contract is preserved, the state-based
   test can remain valid.

Important diagnostic distinction:

    second-connection assertion fails
        -> the committed final-state contract is broken

    it does not automatically prove
        -> one particular helper's commit() line is the cause

Possible causes include a missing commit, rollback, wrong UPDATE, wrong row,
wrong status, or a transaction boundary that is never reached.

A test is an alarm for a violated contract; debugging identifies the cause.


**============================================================**
115. YIELD FIXTURES, GENERATOR OBJECTS, AND RESOURCE HANDOFF
**============================================================**

Creating the second SQLite connection revisited the mechanics behind yield-based
pytest fixtures.

A Python function that contains yield is a generator function.

Calling it directly does not immediately return the yielded dictionary:

    generator = connection_number_two_on_same_db(...)

The result is a generator object.

Conceptually:

    value = next(generator)

starts execution and pauses at:

    yield db

A later next(generator) resumes execution after yield.

This explains why code such as:

    second_conn = connection_number_two_on_same_db(...)
    second_conn['cur']

fails when the function is called directly: second_conn is the generator object,
not the yielded dictionary.

Pytest hides these generator mechanics for yield fixtures.

Given:

    @pytest.fixture
    def second_conn(...):
        create connection and cursor
        yield {'conn': conn, 'cur': cur}
        close cursor and connection

pytest conceptually performs:

    run fixture until yield
    -> inject yielded dictionary into the test
    -> run test
    -> resume fixture after yield
    -> perform cleanup

Therefore the normal test form is:

    def test_something(tmp_db, second_conn):
        second_conn['cur'].execute(...)

The test requests the fixture by parameter name rather than manually calling the
fixture function.

This reinforces the earlier fixture model:

    setup -> handoff -> cleanup

but now with the underlying Python mechanism made explicit:

    generator creation -> next() to yield -> pause -> resume for teardown

For database-resource fixtures, another rule was reinforced:

    a second connection for transaction-visibility testing must point to the same
    SQLite file as the first connection

Creating tmp_db_2.sqlite would create a different database and would not test
visibility of the first connection's transaction.


**============================================================**
116. CURRENT LEARNING POSITION AFTER AUTOMATED MUTATION PRACTICE
**============================================================**

The mutation-testing phase has now progressed through both manual and automated
practice.

Practiced directly before the automated run:

- deliberate manual mutation of real production code;
- predicting which existing test should kill a mutant;
- killed mutants;
- a surviving missing-commit mutant;
- strengthening transaction evidence with a second SQLite connection;
- distinguishing current transactional state from committed visibility;
- observing that a later commit can make an earlier uncommitted change durable;
- filesystem evidence for counter progression;
- database-state evidence for lifecycle status;
- pipeline control-flow mutation;
- rollback mutation in the product parser;
- yield fixtures as generator functions and pytest's setup/handoff/cleanup model.

Practiced directly during the automated run:

- creating a Cosmic Ray configuration for one narrow production module;
- validating the mutation runner's baseline separately from a manual pytest run;
- initializing a mutation session database;
- generating 87 candidate mutation jobs from the real product scraper;
- executing the complete mutation session;
- reading a completed session report;
- interpreting 33 survivors out of 87 jobs as a starting point for investigation,
  not a target score;
- inspecting source diffs for individual survivors;
- recognizing syntax-driven mutation noise;
- distinguishing useful behavioral survivors from low-value survivors;
- adding a focused regression test from an automatically discovered gap;
- using a survivor to expose ambiguous mock evidence;
- refactoring a behavior into a helper to create a cleaner test boundary;
- testing orchestration and helper logic at different levels;
- understanding that patching the helper in an orchestration test means the
  helper's real body is not exercised there;
- keeping the helper real while patching its dependencies in the helper-level
  test;
- recognizing that contract responsibility can move from one test to another
  after refactoring;
- distinguishing "this test kills the mutant" from "this test directly expresses
  every semantic case suggested by the mutant";
- recognizing that a mutation session becomes stale after relevant source
  refactoring.

Current mutation-testing status:

    substantially complete

One concept would still be useful to see concretely if a good example appears:

    equivalent mutant
        -> a generated mutation for which no meaningful input can distinguish
           the mutated program from the original behavior

This should not justify a long search. If the fresh mutation run contains a clear
example, classify it. If not, mutation testing can still be considered sufficiently
practiced for the current learning stage.


**============================================================**
117. AUTOMATED MUTATION RESULT: MISSING NO-URL CONTINUATION CONTRACT
**============================================================**

The automated mutation session generated this control-flow mutant in
scrape_product_urls():

    if product_url is None:
        update status to failed_unfetchable
        continue

became:

    if product_url is None:
        update status to failed_unfetchable
        break

The mutant survived the existing 13 product-scraper tests.

At first this looked surprising because the scraper suite already contained
continuation tests.

Inspection showed that those tests protected different branches:

    fetch_html raises Exception
        -> later product still processed

    fetch_html returns None
        -> later product still processed

but there was no test proving:

    product_url is None
        -> later valid product still processed

The existing one-row no-URL test proved only:

    row with product_url None
        -> fetch_html not called
        -> write_html not called
        -> row becomes failed_unfetchable

With only one row, both:

    continue

and:

    break

produce the same final evidence.

A new focused test was added:

    test_no_product_url_does_not_impede_loop_from_continuing

Its arrangement is:

    row 1 -> product_url None
    row 2 -> valid product URL

Its decisive evidence is that the later valid row reaches the fetching/writing
path.

When the mutant was applied manually, the new test failed because the fetch mock
had zero calls:

    Expected 'mock' to have been called once.
    Called 0 times.

The failure chain was:

    row 1 has no URL
    -> mutant executes break
    -> while loop exits
    -> row 2 is never fetched
    -> continuation assertion fails

This killed the mutant.

General lessons:

- two branches may share the general concept "failure then continue" while still
  representing separate contracts;
- one-row failure tests cannot prove loop continuation;
- a continuation test needs a later observation point;
- automated mutation testing can find a gap that ordinary branch review missed;
- adding a test is justified when the survivor reveals an important contract,
  not merely because the survivor exists.


**============================================================**
118. AUTOMATED MUTATION RESULT: AMBIGUOUS SPECIAL-WAIT EVIDENCE
**============================================================**

Another surviving mutant targeted the special-wait condition:

    if (page_counter % 5 == 0) and (page_counter != 0):

became:

    if (page_counter % 5 == 0) and (page_counter == 0):

The existing test used page_counter=5, patched random.uniform to return 6, and
checked:

    mock_countdown_sleep_timer.assert_any_call(6)

The expectation was that the special-wait branch would call:

    random.uniform(5, 7)
    -> 6
    -> countdown_sleep_timer(6)

However, scrape_product_urls() also contained a normal post-success wait:

    random.uniform(1, 5)
    -> countdown_sleep_timer(wait_time)

Because random.uniform was patched with one stable return value, the normal wait
also returned 6.

Therefore under the mutant:

    special-wait branch does not execute
    -> successful scrape reaches normal wait
    -> mocked random.uniform(1, 5) returns 6
    -> countdown_sleep_timer(6)
    -> assert_any_call(6) still passes

This exposed a new evidence problem:

    expected call observed
        !=
    intended branch proven

The test was technically checking a real interaction, but the interaction was not
unique to the branch it was intended to prove.

The production code was then refactored so the special-wait logic could live
behind a dedicated helper such as:

    occasional_long_pause_to_simulate_browsing(page_counter)

This created two test responsibilities.

Orchestration-level scraper test:

    patch occasional_long_pause_to_simulate_browsing
    -> run scrape_product_urls()
    -> verify the scraper delegates to the helper

Because the helper is patched in this test, its real internal condition is not
executed.

Helper-level test:

    keep occasional_long_pause_to_simulate_browsing real
    patch random.uniform
    patch countdown_sleep_timer
    -> call helper with page_counter=5
    -> call helper with page_counter=4
    -> verify sleep call history is exactly [call(1)]

This proves in the chosen examples:

    5 -> special wait occurs
    4 -> special wait does not occur

When the condition mutant was applied, the helper test produced:

    mock_sleep.call_args_list == []

instead of:

    [call(1)]

and therefore killed the mutant.

Important distinctions learned:

1. Mock the dependency, not the behavior under test.

   In the scraper orchestration test:
       helper is mocked

   In the helper logic test:
       helper is real
       sleep/randomness dependencies are mocked

2. Refactoring can move contract ownership.

   Before extraction:
       scraper test attempted to protect the special-wait condition

   After extraction:
       scraper test protects delegation
       helper test protects the condition itself

3. Killing a mutant and directly expressing its semantic edge case are different.

   The helper test with 5 and 4 killed:
       != 0 -> == 0

   even though it did not call the helper with 0.

   The mutant was killed because the mutated condition also prevented 5 from
   triggering the wait.

4. A test does not need to be strengthened indefinitely once it already proves
   the contract chosen for that test.


**============================================================**
119. ADDITIONAL MANUAL MUTATION RESULTS: PIPELINE AND ROLLBACK
**============================================================**

Two planned high-value mutations from the previous roadmap were also completed.

1. Pipeline skip mutation

Production behavior:

    if not stages[stage.key]:
        log skipped stage
        continue

Mutation:

    continue
    -> return

Existing test:

    only product_parser enabled
    all earlier stages disabled
    -> product_parser must still run

Expected shared state:

    ['product_parser']

Mutated result:

    []

The mutant was killed.

Protected contract:

    a disabled pipeline stage is skipped
    -> pipeline iteration continues
    -> later enabled stages still execute

This is stronger than merely proving that a disabled stage itself does not run.
It protects orchestration continuation.

2. Product-parser rollback mutation

Failure scenario:

    update_product_data() succeeds
    -> update_parse_status(parsed_succeeded) fails
    -> rollback incomplete transaction
    -> recovery marks parsing_failed
    -> recovery transaction commits

Mutation:

    remove db['conn'].rollback()

Expected final database evidence:

    (None, 'parsing_failed')

where the product field remains at its original value because the partial product
update must be rolled back.

Mutated result retained the product update while also recording parsing_failed.

The test therefore failed and killed the mutant.

Protected contract:

    if completion fails after product data has been changed but before the
    successful parse transition completes,
    -> partial product-data changes are rolled back
    -> recovery state parsing_failed is committed

This reinforced the earlier transaction lesson:

    a later commit commits all still-pending changes in the current transaction

so recovery code can accidentally make an earlier partial update durable if the
rollback boundary is missing.


**============================================================**
120. AUTOMATED MUTATION TOOL WORKFLOW
**============================================================**

The automated exercise introduced the mechanics of a real mutation tool rather
than only mutation theory.

Working model:

    configuration
        -> choose production scope
        -> choose test command
        -> choose timeout/execution settings

    baseline
        -> run tests against unmutated code through the mutation tool
        -> confirm the tool can execute the configured suite

    init
        -> scan the target source
        -> generate candidate mutation jobs
        -> store them in a session database

    exec
        -> take one pending job
        -> temporarily apply mutation
        -> run configured tests
        -> record outcome
        -> restore source
        -> continue

    report
        -> inspect killed/survived/etc.
        -> inspect actual mutation diffs

The source file being restored after execution is intentional. The session
database stores the mutation descriptions and outcomes; developers do not need to
manually create every mutant for normal automated mutation testing.

Manual mutation remains useful when reproducing one survivor for study.

The generated operator list also taught that mutation tools are syntax-driven.

For example, Python union type syntax:

    str | None

contains the `|` binary operator syntactically. The mutation engine therefore
generated transformations involving arithmetic or bitwise replacements that are
not meaningful domain defects.

Some of these fail immediately at import or collection.

This is why mutation output must be interpreted:

    generated mutant
        !=
    meaningful possible bug

Tool/execution-problem outcomes also should not be treated as equivalent to a
meaningful killed or surviving behavioral mutant.

The value of an automated mutation tool is:

    systematically challenge assumptions the developer did not manually choose

not:

    accept every generated mutation as an equally important requirement.


**============================================================**
121. MUTATION SCORE, SURVIVOR PRIORITY, AND STOPPING RULES
**============================================================**

The first automated run produced:

    total jobs: 87
    complete: 87
    surviving mutants: 33
    survival rate: 37.93%

The percentage is a useful summary but not a direct measure of software quality.

A high-value survivor changes an important crawler contract.

Example:

    no-URL continue -> break
    -> later products may never be processed

A lower-value survivor may alter a secondary operational choice.

Example:

    random.uniform(1, 5)
    -> random.uniform(0, 5)

Whether this deserves a new test depends on whether the exact lower delay bound
is an important contract.

Refined classification questions:

    1. Does the mutant change externally meaningful crawler behavior?

    2. Is that behavior already protected through another observation point?

    3. Does the survivor expose ambiguous or insufficient evidence?

    4. Is the mutant equivalent for all meaningful inputs?

    5. Is the behavior intentionally left flexible?

    6. Would killing it improve reliability, or merely couple the test to one
       implementation choice?

A survivor therefore has at least four possible dispositions:

    meaningful gap
        -> add or strengthen a test

    ambiguous evidence
        -> improve the test boundary or evidence

    equivalent mutant
        -> no test can meaningfully distinguish it

    unimportant/implementation-flexibility mutant
        -> intentionally leave it alive

The objective is not:

    mutation score -> 100%

The objective is:

    important contracts -> discriminating evidence

A fresh mutation session should be generated after meaningful production
refactoring. The previous session describes mutation locations in the previous
source structure and can become stale.


**============================================================**
122. GIT AS A SAFETY BOUNDARY FOR TESTING EXPERIMENTS
**============================================================**

A Git repository was established before the automated mutation run.

The basic sequence learned was:

    git init
        -> create local repository metadata

    git add .
        -> stage the current project state for the next commit

    git commit -m "..."
        -> record the staged snapshot in repository history

The staging area was distinguished from repository history:

    working directory
        -> git add
    staging area
        -> git commit
    committed history

The command-line syntax was also clarified:

    -m
        -> a short command-line option

    "multi word text"
        -> quotation marks make the text one shell argument

For mutation/refactoring experiments, the useful engineering practice is:

    establish known-green code
    -> commit it
    -> perform risky or automated transformations
    -> use git status / git diff to see unintended changes

Git is not part of mutation testing itself. It is a useful independent safety
boundary when tools or manual exercises deliberately modify production source.


**============================================================**
123. REVISED CONCRETE FOLLOW-UPS FROM THE CURRENT CRAWLER
**============================================================**

A. Finish one final contract exercise already in progress

Current consumer:

    crawler_product_html_parser

It calls:

    specific_site_config.individual_product_data_extraction(soup)

The parser accepts a falsey extraction as parse failure. If extraction succeeds,
update_product_data() reads:

    product["slug"]
    product["currency"]
    product["price"]
    product["product_code"]
    product["reviews"]
    product["images"][0]

Current provider situation in dynamic_crawler(6).zip:

    BooksToScrape
        -> provides individual_product_data_extraction()

    MercadoLibre
        -> provides individual_product_data_extraction()

    Amazon
        -> does not provide that capability

This test is NOT YET COMPLETED.

The useful reasoning questions are:

1. Method capability

       Which adapters claim to participate in individual-product parsing?
       Must they expose individual_product_data_extraction()?

2. Successful return shape

       If the method reports successful extraction, what keys must the returned
       object provide because update_product_data() reads them directly?

3. images[0]

       The minimum consumer requirement is not automatically "images must be a
       list". The consumer specifically requires an images value that supports
       index 0 and has an element there.

4. Falsey return

       Because run_crawler_product_html_parser() checks:

           if not product:

       a falsey extraction is already an accepted failure signal. The contract for
       a successful parse should therefore be distinguished from the failure
       signal.

Recommended exercise:

    derive the contract in plain language
    -> write one shared test
    -> verify BooksToScrape and MercadoLibre
    -> mark Amazon xfail if it is intentionally incomplete
    -> stop the contract-testing phase after the architectural lesson is clear

Do not expand this into a checklist of every adapter attribute.

B. Optional unresolved design question: None versus []

BooksToScrape.product_extraction() currently returns None when no expected product
containers are found.

Only revisit this now if the application needs a semantic distinction between:

    valid search page with zero products
    vs
    extraction structure missing / parser unable to recognize page

If no current behavior depends on that distinction, it can remain a design note
rather than another test exercise.

C. Move to model-based/stateful property testing

After the current parser contract, this is the strongest next learning step because
it introduces a new kind of evidence rather than another pytest API variation.

Use the ProductPages lifecycle as the model target.

A useful first model includes states such as:

    pending
    fetching
    fetched
    parsing
    parsed_succeeded
    parsing_failed
    failed
    failed_unfetchable

with recovery behavior such as:

    interrupted fetching -> pending
    stuck parsing -> parse_status reset for later work

The important move is to create an independent model of the expected state, then
apply actions to both:

    model state
    real temporary SQLite row

After every action:

    compare model and database
    assert global invariants

A good learning progression is:

    1. one small deterministic model and hand-chosen action sequence
    2. then Hypothesis stateful generation / RuleBasedStateMachine
    3. let Hypothesis generate operation histories and shrink a failing history

This avoids learning Hypothesis syntax before understanding what the independent
model is supposed to prove.

D. Controlled local end-to-end slice

After stateful testing, build one vertical slice around BooksToScrape.

BooksToScrape remains the appropriate reference provider because it was chosen to
exercise the crawler without live-site/server-side instability.

Keep real:

    temporary SQLite
    tmp_path filesystem
    BeautifulSoup
    BooksToScrape adapter
    crawler stage logic

Keep the network/browser boundary controlled or excluded.

Useful slice:

    seed/search page state
    -> saved search HTML
    -> product URL insertion
    -> saved product HTML
    -> product parsing
    -> final ProductPages database state

This teaches system-level confidence without making the test depend on the live
internet.

E. Deterministic concurrency and atomic job claiming

Later, reuse the two-connection SQLite technique already learned during commit
visibility testing.

Candidate question:

    Can two workers observe and claim the same pending ProductPages row?

This is a natural entry into:

    race conditions
    atomic claiming
    transaction isolation
    controlled interleavings

F. Exception safety and resource ownership

After concurrency, test a small number of composition-root guarantees:

    database connection closes after pipeline failure
    owned resources close exactly once
    partial initialization is cleaned up
    cleanup failures do not silently replace the primary application failure

G. Optional metamorphic parser testing

Only after the higher-priority topics, use HTML transformations that should not
change parser meaning:

    whitespace changes
    irrelevant elements
    unrelated attribute reordering
    extra non-product containers

Then compare original and transformed extraction results.

**============================================================**
124. UPDATED ADVANCED LEARNING ROADMAP AFTER CONTRACT PRACTICE
**============================================================**

Current status:

    mutation testing
        -> complete for current learning goals

    consumer-driven contracts
        -> complete for current learning goals
        -> three meaningful contracts practiced

Completed contract sequence:

    1. Search-parser product contract

       Consumer:
           crawler_search_html_parser

       Provider operation:
           product_extraction(soup)

       Practiced evidence:
           successful result is a list
           representative products are dictionaries
           "link" exists as a consumer-required key

       Important semantic correction:
           the current crawler can deliberately tolerate:
               {"link": None}

           because later product-scraper logic recognizes an unfetchable product URL
           and moves that row to failed_unfetchable.

           Therefore:
               "link" key exists
           is not the same contract as:
               "link" is always a usable URL

    2. Product-scraper selector contract

       Consumer:
           scrape_product_urls()

       Required adapter capability:
           wait_selector

       Practiced evidence:
           hasattr(adapter, "wait_selector")

       Architectural lesson:
           the requirement belongs to adapters participating in this capability,
           not automatically to every registered site object.

    3. Individual-product parser contract

       Consumer:
           crawler_product_html_parser / update_product_data()

       Provider operation:
           individual_product_data_extraction(soup)

       Successful-result contract:
           result is a dictionary
           required keys exist:
               slug
               currency
               price
               product_code
               reviews
               images
           images contains at least one element because the consumer reads:
               product["images"][0]

       Current provider capability:
           BooksToScrape -> participates
           MercadoLibre  -> participates
           Amazon        -> does not currently expose this capability

The consumer-driven contract phase is now sufficiently complete.

Do not continue by manufacturing more shared-interface tests merely to cover every
adapter attribute. The central technique has already been practiced in three distinct
forms:

    returned collection/data shape
    structural attribute capability
    method capability + successful returned-value compatibility

Optional unresolved design question:

    BooksToScrape.product_extraction():
        no recognized product containers -> None

This should only be revisited if the application needs to distinguish:

    valid page containing zero products
    vs
    parser could not recognize the expected page structure

It is not a mandatory extra contract exercise.

Immediate next step:

    begin model-based/stateful testing of the ProductPages lifecycle

Recommended sequence from here:

    1. Build one small independent ProductPages state model by hand.

       Do not begin with Hypothesis syntax.

       First define:
           model state
           legal actions
           expected state transitions
           global invariants

    2. Apply one deterministic hand-written action history to:
           the independent model
           the real temporary SQLite row

       After every action:
           compare model state with database state

    3. Introduce Hypothesis stateful testing / RuleBasedStateMachine only after the
       manual model is conceptually clear.

       Then learn:
           generated operation histories
           invariants checked after every action
           shrinking a failing history to a smaller counterexample

    4. Build one controlled local end-to-end BooksToScrape slice:
           real temporary SQLite
           real tmp_path filesystem
           real BeautifulSoup
           real BooksToScrape adapter
           real crawler stage logic
           saved/synthetic HTML
           no live network dependency

    5. Study deterministic concurrency and atomic job claiming.

       Reuse the two-connection SQLite technique already practiced.

       Main question:
           can two workers claim the same pending ProductPages row?

    6. Study exception safety and resource ownership at the composition boundary.

    7. Use metamorphic parser testing only as an optional later robustness topic.

The learning criterion remains:

    each new exercise should introduce a new kind of evidence,
    failure mode,
    or design question

not:

    accumulate tests,
    attributes,
    mocks,
    branches,
    mutation-score points,
    contract cases,
    or pytest syntax because they exist

**============================================================**
125. CONTRACT TESTS: SHARED PROMISE VS PROVIDER-SPECIFIC BEHAVIOR
**============================================================**

A distinction now practiced directly is:

    provider-specific test
        -> asks whether one implementation produces its exact expected result

    contract test
        -> asks whether an implementation satisfies the promise required by a
           consumer

Example:

    exact BooksToScrape URL equality
        -> provider-specific parsing evidence

    result is the agreed collection type
    product is a dictionary
    "link" exists
        -> shared consumer-contract evidence

A contract test can still use BooksToScrape as the provider under test. What makes
it a contract test is not the name of the provider; it is that the assertions are
about the shared consumer requirement and can be reused against another provider.

This is why contract tests can act as executable architecture documentation.



**============================================================**
126. PARAMETRIZATION, FIXTURES, AND PROVIDER-SPECIFIC INPUT
**============================================================**

The contract exercise clarified three independent dimensions:

    contract assertions
        -> shared

    provider implementation
        -> varies

    provider-specific input HTML
        -> varies

pytest.mark.parametrize() is useful because it varies the provider/input while
keeping the contract assertions in one place.

A fixture and a parametrized argument are not interchangeable concepts:

    @pytest.fixture
        -> reusable setup/data supplied through pytest fixture resolution

    @pytest.mark.parametrize
        -> multiple explicit cases supplied to one test

A test may use both simultaneously.

Another practical lesson was that parametrizing file paths creates an accidental
precondition if those files do not actually exist. The contract did not require
real fixture files. Small synthetic HTML snippets were therefore preferable when
they were sufficient to trigger each adapter's extraction logic.

General rule:

    do not let test scaffolding invent production requirements

If a full saved HTML page is not part of the behavior being tested, do not create
one merely because an earlier parametrization example happened to use html_path.



**============================================================**
127. XFAIL, XPASS, SKIP, AND PYTEST.RAISES
**============================================================**

Four outcomes/tools now have distinct meanings:

    ordinary FAIL
        -> unexpected violation

    XFAIL
        -> known current violation; test still executes

    XPASS
        -> the known violation may have disappeared

    SKIP
        -> test is not executed

pytest.raises() belongs to a different category:

    pytest.raises(ExpectedException)
        -> the exception itself is the expected production behavior being asserted

xfail instead describes the expected current status of a whole test case.

Useful rule:

    known incomplete provider that should eventually satisfy the contract
        -> xfail can keep the obligation visible

    provider not participating in that capability at all
        -> consider excluding it from that contract rather than accumulating
           permanent xfails

This distinction prevents xfail from becoming a dumping ground for irrelevant
providers.



**============================================================**
128. HASATTR, ISINSTANCE, AND MINIMUM STRUCTURAL EVIDENCE
**============================================================**

Two Python built-ins became useful for structural contract evidence.

isinstance():

    isinstance(result, list)
    isinstance(product, dict)

This checks runtime class/subclass relationships.

It cannot directly check a parameterized generic:

    isinstance(result, list[dict])
        -> TypeError

because list[dict] is a type description, not a runtime class accepted by
isinstance() as its second argument.

hasattr():

    hasattr(adapter, "wait_selector")

This directly checks whether an object exposes the named attribute.

The wait_selector exercise showed why the narrowest evidence is often strongest:

    contract:
        adapter must expose wait_selector

    focused evidence:
        assert hasattr(adapter, "wait_selector")

Calling process_single_url() merely to discover the missing attribute would also
fail, but it would introduce unrelated Page, Logger, browser-loading, and fetching
behavior into the diagnosis.

A test can technically pass or fail without an explicit assert because an
unexpected exception is itself a pytest failure. That does not mean a no-assert
workflow test is the clearest evidence for a narrow structural contract.



**============================================================**
129. TOOLING NOTE: PYTEST IMPORTS VS PYLANCE STATIC RESOLUTION
**============================================================**

A development-tooling issue clarified that runtime imports and editor static
analysis can have different search paths.

Observed situation:

    pytest
        -> tests imported crawler modules successfully

    Pylance
        -> reported unresolved imports and could not provide reliable Peek/
           definition navigation

The project uses a src-style import root. Adding the crawler source root to VS
Code/Pylance analysis paths restored editor navigation without changing the
working pytest imports.

Useful distinction:

    Python/pytest runtime import resolution
    !=
    Pylance static-analysis resolution

An editor error can therefore indicate missing analysis configuration rather than
a broken runtime import.



**============================================================**
130. INDIVIDUAL-PRODUCT PARSER CONTRACT — COMPLETED
**============================================================**

The third and intended final consumer-driven adapter contract has now been practiced.

Consumer:

    crawler_product_html_parser

Provider operation:

    individual_product_data_extraction(soup)

The consumer first obtains:

    product = specific_site_config.individual_product_data_extraction(soup)

A falsey result belongs to the parsing-failure path.

For a successful result, downstream update logic directly reads:

    product["slug"]
    product["currency"]
    product["price"]
    product["product_code"]
    product["reviews"]
    product["images"][0]

The contract was derived from these consumer operations rather than from the exact
implementation of any one provider.

Minimal successful-result contract:

    adapter participating in individual-product parsing
        -> exposes individual_product_data_extraction(soup)

    successful extraction
        -> returns a dict

    returned dict
        -> contains:
            slug
            currency
            price
            product_code
            reviews
            images

    images
        -> supports index 0
        -> contains at least one element

The shared test written for participating providers follows the form:

    soup = BeautifulSoup(test_html, "html.parser")
    adapter_used = adapter_class()

    result = adapter_used.individual_product_data_extraction(soup)

    assert isinstance(result, dict)
    assert "slug" in result
    assert "currency" in result
    assert "price" in result
    assert "product_code" in result
    assert "reviews" in result
    assert "images" in result
    assert len(result["images"]) > 0

The exact provider HTML may differ while the assertions remain shared.

This is the same consumer-driven structure practiced earlier:

    provider-specific input
    + provider-specific implementation
    + shared consumer requirement


**============================================================**
131. METHOD EXISTENCE VS RETURNED-DATA COMPATIBILITY
**============================================================**

The final contract exercise clarified two layers that should not be confused.

Layer 1: method capability

    Can the consumer make this call at all?

        adapter.individual_product_data_extraction(soup)

If the method does not exist, Python raises AttributeError.

Layer 2: successful returned-data compatibility

    If the call succeeds and represents a successful parse,
    can the consumer actually use the returned object?

That requires:

    dict shape
    required keys
    an images value compatible with images[0]

This distinction generalizes beyond the crawler:

    interface member exists
        !=
    returned value satisfies the behavioral/data contract

A provider can expose the correct method name while still be incompatible with
its consumer because its return shape is wrong.


**============================================================**
132. KEY EXISTENCE VS VALUE USABILITY
**============================================================**

A new evidence-strength distinction was practiced directly.

This assertion:

    assert "images" in result

proves only:

    the dictionary contains the key

It does not prove that the consumer operation:

    result["images"][0]

is valid.

For example, all of these satisfy key existence:

    {"images": []}
    {"images": None}
    {"images": some_incompatible_value}

but they do not necessarily satisfy the actual consumer operation.

The stronger evidence chosen was:

    assert len(result["images"]) > 0

because the current provider contract is intended to supply an indexable image
collection and the consumer requires at least one element.

General rule:

    derive assertions from the operation the consumer performs,
    not merely from superficial presence of a field

This is another form of the minimum-sufficient-evidence principle:

    weak structural fact:
        key exists

    consumer-relevant fact:
        value can support the operation the consumer performs


**============================================================**
133. IMPLICIT FAILURE EVIDENCE VS EXPLICIT STRUCTURAL ASSERTIONS
**============================================================**

The final exercise also refined when hasattr() is useful.

For wait_selector, the narrow contract itself was:

    adapter exposes wait_selector

Therefore:

    assert hasattr(adapter, "wait_selector")

was direct and focused evidence.

For individual_product_data_extraction(), the test immediately executes:

    adapter.individual_product_data_extraction(soup)

If the method is absent, the test already fails with AttributeError.

Therefore a separate:

    assert hasattr(adapter, "individual_product_data_extraction")

is not strictly required for that test.

This is not a rule that hasattr() should never be used for methods.

The design question is:

    What is the clearest minimum evidence for this particular contract?

If the method call is already necessary to test the returned-data contract, method
absence is naturally exposed by that call.

If only structural capability is being tested, hasattr() may express the requirement
more directly.


**============================================================**
134. CONSUMER-DRIVEN CONTRACT TESTING — PHASE COMPLETE
**============================================================**

Three different contract forms have now been practiced.

1. Shared returned collection/data contract

       product_extraction(soup)

       learned:
           same assertions across providers
           provider-specific HTML input
           runtime type checks
           required consumer key
           known incompatibility through xfail

2. Structural capability contract

       wait_selector

       learned:
           capability requirements belong to participating consumers/providers
           hasattr() can express a narrow structural promise
           do not call an entire downstream workflow merely to prove one attribute

3. Method + successful returned-data contract

       individual_product_data_extraction(soup)

       learned:
           method existence and return compatibility are separate layers
           required fields come from consumer operations
           key existence is weaker than value usability
           images[0] creates a non-empty/indexability requirement

Concepts consolidated across the phase:

    consumer-driven contract
    provider verification
    shared contract assertions
    provider-specific input
    capability-based interface reasoning
    structural compatibility
    behavioral/data compatibility
    substitutability
    xfail as visible known incompatibility
    XFAIL vs XPASS vs SKIP vs pytest.raises
    fixture vs parametrized argument
    isinstance() runtime checks
    parameterized generics are not runtime isinstance() classes
    hasattr()
    synthetic HTML as minimum test scaffolding
    direct contract evidence over unrelated workflow execution
    minimum sufficient evidence
    contract tests as executable architecture documentation

Stopping rule:

    The crawler has enough contract examples to establish the technique.

Adding more adapter contract tests now would mostly repeat the same reasoning with
different member names.

The phase is complete.


**============================================================**
135. CURRENT LEARNING POSITION: BEGIN MODEL-BASED/STATEFUL TESTING
**============================================================**

The next topic is not another pytest assertion API.

The crawler already has many individually tested state transitions. The next new
testing problem is:

    Can a sequence of individually valid operations produce an invalid lifecycle?

The recommended target is ProductPages because it already has a meaningful workflow.

Relevant states in the current learning model include:

    pending
    fetching
    fetched
    parsing
    parsed_succeeded
    parsing_failed
    failed
    failed_unfetchable

Recovery behavior already seen in the project includes:

    interrupted fetching -> pending
    stuck parsing -> a state eligible for later parsing/recovery

The new technique is to maintain an independent model:

    expected_state = ...

Then perform the same conceptual action against:

    the model
    the real temporary SQLite database

After each operation:

    assert database_state == model_state

This differs from the state-machine tests already practiced.

Earlier state tests asked:

    Is this one transition legal?
    Does this one recovery transition work?
    Is this terminal state protected?

Model-based/stateful testing asks:

    Across a sequence of actions, does the real implementation remain equivalent
    to an independent model after every step?

First exercise recommendation:

    Do NOT install or write Hypothesis machinery immediately.

    Start with:
        one ProductPages row
        one explicit model variable
        three or four meaningful actions
        one hand-selected action sequence
        comparison after every action

Candidate first sequence:

    pending
    -> claim for fetching
    -> fetching
    -> report successful fetch
    -> fetched
    -> claim for parsing
    -> parsing
    -> report parse failure
    -> parsing_failed

The purpose of this first sequence is not to discover a bug.

It is to learn the model-testing structure:

    model action
    + real action
    + compare after every step

Only after that structure is clear should Hypothesis generate alternative histories.

High-value follow-up after the hand-built model:

    Hypothesis RuleBasedStateMachine

Then learn:

    rules/actions
    preconditions
    invariants
    generated histories
    shrinking

This is the current recommended next learning phase.


**============================================================**
136. FOLLOW-UP ROADMAP FROM THE CURRENT CRAWLER
**============================================================**

A. Immediate: manual independent lifecycle model

    Use ProductPages.

    Goal:
        learn model-based evidence without first learning library syntax

    New evidence:
        equivalence between real persistent state and an independent expected model
        after every operation in a history

B. Then: generated stateful property testing

    Introduce Hypothesis only after the manual model works.

    Goal:
        generate histories the test author did not enumerate manually

    New concepts:
        rule-based state machines
        preconditions
        invariants
        shrinking operation sequences

C. Controlled BooksToScrape end-to-end slice

    Keep real:
        SQLite
        tmp_path filesystem
        BeautifulSoup
        BooksToScrape adapter
        crawler stage logic

    Control:
        browser/network boundary

    Follow one product through several crawler stages and verify final persistent
    state.

    New evidence:
        vertical system-level cooperation across real components

D. Deterministic concurrency and atomic claiming

    Candidate:
        two SQLite connections / two simulated workers

    Question:
        can both workers claim the same pending row?

    New concepts:
        race condition
        controlled interleaving
        transaction isolation
        atomic claim operation

E. Exception safety and resource ownership

    Candidate guarantees:
        DB closes after pipeline failure
        owned resources close exactly once
        partial initialization is cleaned up
        cleanup failure does not silently hide the primary failure

    New concepts:
        composition-root testing
        resource ownership
        setup/work/teardown failure injection

F. Optional metamorphic parser testing

    Transform valid HTML without changing meaning:

        whitespace changes
        irrelevant nodes
        unrelated attribute order
        extra non-product containers

    Then assert:
        transformed extraction == original extraction

    New evidence:
        semantic stability without writing a new exact oracle for every transformed
        input

Priority order:

    manual model
    -> Hypothesis stateful generation
    -> controlled local E2E slice
    -> deterministic concurrency
    -> exception safety/resource ownership
    -> optional metamorphic parser robustness

The governing rule remains:

    move on when the concept is learned

not:

    keep adding tests because more tests can be written
