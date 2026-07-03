import os
import time
import base64
import requests
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

GAS_URL = "https://script.google.com/macros/s/AKfycbzUv3MQ9mMxpj6GqfUWHDGzDpLq7wv2Zyv8mLNAqb3NBQvrz4NUnEQMbaaPv1Y8Bd6N/exec"

TARGET_CHARTS = {
    "1. S&P 500 指數": "https://www.tradingview.com/chart/?symbol=SPX",
    "2. 台積電 (2330)": "https://www.tradingview.com/chart/?symbol=TWSE:2330"
}

AD_REMOVAL_SCRIPT = """
    var ads = document.querySelectorAll('[class*="overlap"], [class*="dialog"], [class*="popup"], [class*="drawer"]');
    ads.forEach(el => el.remove());
    var backdrop = document.querySelector('.tv-dialog__backdrop');
    if(backdrop) backdrop.remove();
"""


def create_chrome_options():
    """Create and configure Chrome options for headless browsing."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return options


def create_driver(options=None):
    """Create a Chrome WebDriver instance."""
    if options is None:
        options = create_chrome_options()
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


def dismiss_ads(driver):
    """Dismiss ads and popups on the TradingView page."""
    actions = webdriver.ActionChains(driver)
    actions.send_keys(Keys.ESCAPE).perform()
    time.sleep(1)
    driver.execute_script(AD_REMOVAL_SCRIPT)


def switch_to_half_year_view(driver):
    """Switch the chart to the 180-day (half-year) view."""
    actions = webdriver.ActionChains(driver)
    actions.send_keys("180D").send_keys(Keys.ENTER).perform()
    time.sleep(12)


def prepare_chart(driver, url, load_wait=18):
    """Navigate to a chart URL and prepare it for screenshot capture."""
    driver.get(url)
    time.sleep(load_wait)
    try:
        dismiss_ads(driver)
        print("   -> 正在切換至半年視圖...")
        switch_to_half_year_view(driver)
    except Exception as e:
        print(f"   -> ⚠️ 廣告處理出錯: {e}")


def take_screenshot(driver):
    """Take a screenshot and return it as a base64-encoded string."""
    return driver.get_screenshot_as_base64()


def send_screenshot(gas_url, name, image_data):
    """Send a screenshot to the Google Apps Script endpoint."""
    payload = {"name": name, "image_data": image_data}
    return requests.post(gas_url, json=payload)


def capture_and_send(
    gas_url=None, target_charts=None, driver=None
):
    """Main orchestration: capture chart screenshots and send them."""
    if gas_url is None:
        gas_url = GAS_URL
    if target_charts is None:
        target_charts = TARGET_CHARTS

    own_driver = driver is None
    if own_driver:
        driver = create_driver()

    try:
        for name, url in target_charts.items():
            print(f"🚀 正在進入 {name}...")
            prepare_chart(driver, url)

            print(f"📷 正在擷取截圖...")
            screenshot_b64 = take_screenshot(driver)

            response = send_screenshot(gas_url, name, screenshot_b64)
            print(f"✅ {name} 傳送結果: {response.text}")

    except Exception as e:
        print(f"🚨 執行出錯: {e}")
        sys.exit(1)
    finally:
        if own_driver:
            driver.quit()


if __name__ == "__main__":
    capture_and_send()
