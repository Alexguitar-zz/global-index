import sys

from api_utils import send_screenshot
from browser_utils import (
    capture_screenshot,
    create_driver,
    dismiss_popups,
    load_chart,
    switch_time_range,
)
from config import GAS_URL, TARGET_CHARTS


def capture_and_send():
    driver = create_driver()

    try:
        for name, url in TARGET_CHARTS.items():
            print(f"正在進入 {name}...")
            load_chart(driver, url)

            try:
                dismiss_popups(driver)
                print("   -> 正在切換至半年視圖...")
                switch_time_range(driver)
            except Exception as e:
                print(f"   -> 廣告處理出錯: {e}")

            print("正在擷取截圖...")
            screenshot_b64 = capture_screenshot(driver)

            result = send_screenshot(GAS_URL, name, screenshot_b64)
            print(f"{name} 傳送結果: {result}")

    except Exception as e:
        print(f"執行出錯: {e}")
        sys.exit(1)
    finally:
        driver.quit()


if __name__ == "__main__":
    capture_and_send()
