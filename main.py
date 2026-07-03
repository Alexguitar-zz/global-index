import time
import requests
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# === 【最重要】請將下方引號內的文字替換為你剛剛在 GAS 得到的 URL ===
GAS_URL = "https://script.google.com/macros/s/AKfycbzUv3MQ9mMxpj6GqfUWHDGzDpLq7wv2Zyv8mLNAqb3NBQvrz4NUnEQMbaaPv1Y8Bd6N/exec"

TARGET_CHARTS = {
    "1. S&P 500 指數": "https://www.tradingview.com/chart/?symbol=SPX",
    "2. 台積電 (2330)": "https://www.tradingview.com/chart/?symbol=TWSE:2330"
}

REQUEST_TIMEOUT_SECONDS = 30
CHART_LOAD_WAIT_SECONDS = 18
TIMEFRAME_SWITCH_WAIT_SECONDS = 12


def create_driver():
    """Create and return a configured Chrome WebDriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
    except WebDriverException as e:
        print(f"🚨 無法啟動 WebDriver: {e}")
        raise
    return driver


def dismiss_ads_and_set_timeframe(driver):
    """Dismiss popups/ads and switch to 180-day timeframe.

    Raises on failure so callers know the chart view may be incorrect.
    """
    # 1. 模擬 ESC 鍵關閉彈窗
    actions = webdriver.ActionChains(driver)
    actions.send_keys(Keys.ESCAPE).perform()
    time.sleep(1)

    # 2. 用 JavaScript 強制刪除所有遮罩與廣告視窗 (針對藍色彈窗優化)
    driver.execute_script("""
        var ads = document.querySelectorAll(
            '[class*="overlap"], [class*="dialog"], [class*="popup"], [class*="drawer"]'
        );
        ads.forEach(el => el.remove());
        var backdrop = document.querySelector('.tv-dialog__backdrop');
        if(backdrop) backdrop.remove();
    """)

    # 3. 切換至半年 (180D) 視圖
    print("   -> 正在切換至半年視圖...")
    actions = webdriver.ActionChains(driver)
    actions.send_keys("180D").send_keys(Keys.ENTER).perform()
    time.sleep(TIMEFRAME_SWITCH_WAIT_SECONDS)


def send_screenshot(name, screenshot_b64):
    """Send a screenshot to the GAS endpoint. Raises on failure."""
    payload = {"name": name, "image_data": screenshot_b64}
    try:
        response = requests.post(GAS_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"無法連線至 GAS 伺服器: {e}") from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"傳送至 GAS 超時 ({REQUEST_TIMEOUT_SECONDS}s): {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"傳送至 GAS 發生錯誤: {e}") from e

    if not response.ok:
        raise RuntimeError(
            f"GAS 回傳錯誤 (HTTP {response.status_code}): {response.text}"
        )

    print(f"✅ {name} 傳送結果: {response.text}")


def capture_and_send():
    driver = create_driver()
    failures = []

    try:
        for name, url in TARGET_CHARTS.items():
            print(f"🚀 正在進入 {name}...")
            try:
                driver.get(url)
            except WebDriverException as e:
                print(f"🚨 無法載入 {name} ({url}): {e}")
                failures.append(name)
                continue

            time.sleep(CHART_LOAD_WAIT_SECONDS)

            # --- 廣告清除與時間範圍切換 ---
            try:
                dismiss_ads_and_set_timeframe(driver)
            except WebDriverException as e:
                print(f"   -> ⚠️ 廣告處理/時間範圍切換失敗: {e}")
                print("   -> 繼續擷取截圖，但內容可能不正確")

            # --- 擷取截圖 ---
            print(f"📷 正在擷取截圖...")
            try:
                screenshot_b64 = driver.get_screenshot_as_base64()
            except WebDriverException as e:
                print(f"🚨 截圖失敗 ({name}): {e}")
                failures.append(name)
                continue

            # --- 傳送截圖 ---
            try:
                send_screenshot(name, screenshot_b64)
            except RuntimeError as e:
                print(f"🚨 傳送失敗 ({name}): {e}")
                failures.append(name)
                continue

    finally:
        driver.quit()

    if failures:
        print(f"\n🚨 以下圖表處理失敗: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    capture_and_send()
