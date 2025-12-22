import time
import random

def stealth_context(browser):

    ua = random.choice([
        # Desktop Chrome-like UAs
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36",
    ])

    viewport = {
        "width": random.randint(1280, 1920),
        "height": random.randint(720, 1080)
    }

    context = browser.new_context(
        user_agent=ua,
        viewport=viewport,
        locale="en-US",
        color_scheme="dark",
        java_script_enabled=True,
        device_scale_factor=random.choice([1, 1.25, 1.5]),
        is_mobile=False,
        has_touch=False,
        extra_http_headers={
            "Accept-Language": "es-ES,es;q=0.9",
            "DNT": "1",
            "Referer": random.choice([
                "https://www.google.com",
                "https://www.bing.com",
                "https://www.yahoo.com",
                "https://www.duckduckgo.com",
            ])
        })
    
    
    #Set language for whole context
    context.add_init_script("""
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-ES', 'es']
    });
    """)

    # Hide webdriver
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => false })"
    )

    #Add plugins
    context.add_init_script("""Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
    """)

    #Hardware concurrency
    context.add_init_script("Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 })")

    #Permissions API
    context.add_init_script("""
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: 'denied' })
            : originalQuery(parameters)
    );
    """)

    return context


def human_scroll(page, min_increment=200, max_increment=450,  timeout=15.0):
    """Scrolls down the page like a human."""
    
    start_time = time.monotonic()

    # get current height
    height = page.evaluate("() => document.body.scrollHeight")
    pos = 0

    while pos < height:
        #Time check
        if time.monotonic() - start_time > timeout:
            break
        # random small increments
        increment = random.randint(min_increment, max_increment)
        pos = min(pos + increment, height)

        # JS scroll
        page.evaluate(f"window.scrollTo(0, {pos})")

        # small pause (like finger pauses)
        time.sleep(random.uniform(0.08, 0.50))

        # update height in case more products load
        new_height = page.evaluate("() => document.body.scrollHeight")
        if new_height != height:
            height = new_height 

        # rare longer pause
        if random.random() < 0.05:
            time.sleep(random.uniform(0.7, 1.3))

        time.sleep(random.uniform(0.8, 1.4))
