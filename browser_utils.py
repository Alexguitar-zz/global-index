import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    CHART_SWITCH_TIMEOUT,
    CHROME_OPTIONS,
    DEFAULT_TIME_RANGE,
    PAGE_LOAD_TIMEOUT,
)

AD_REMOVAL_JS = """
    var ads = document.querySelectorAll(
        '[class*="overlap"], [class*="dialog"], [class*="popup"], [class*="drawer"]'
    );
    ads.forEach(el => el.remove());
    var backdrop = document.querySelector('.tv-dialog__backdrop');
    if(backdrop) backdrop.remove();
"""


def create_driver(chrome_options=None):
    """Create and return a configured Chrome WebDriver instance."""
    options = Options()
    for opt in chrome_options or CHROME_OPTIONS:
        options.add_argument(opt)
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


def load_chart(driver, url, timeout=None):
    """Navigate to a chart URL and wait for it to load."""
    driver.get(url)
    time.sleep(timeout or PAGE_LOAD_TIMEOUT)


def dismiss_popups(driver):
    """Dismiss ads, popups, and overlay dialogs on the current page."""
    actions = webdriver.ActionChains(driver)
    actions.send_keys(Keys.ESCAPE).perform()
    time.sleep(1)
    driver.execute_script(AD_REMOVAL_JS)


def switch_time_range(driver, time_range=None):
    """Switch the TradingView chart to the specified time range."""
    actions = webdriver.ActionChains(driver)
    actions.send_keys(time_range or DEFAULT_TIME_RANGE)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(CHART_SWITCH_TIMEOUT)


def capture_screenshot(driver):
    """Capture and return a base64-encoded screenshot."""
    return driver.get_screenshot_as_base64()
