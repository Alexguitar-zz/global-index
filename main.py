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

# === 基礎配置 ===
GAS_URL = "你的最新_GAS_URL"

TARGET_CHARTS = {
    "1. S&P 500 指數": "https://www.tradingview.com/chart/?symbol=SPX",
    "2. 台積電 (2330)": "https://www.tradingview.com/chart/?symbol=TWSE:2330"
}

def capture_and_send():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        for name, url in TARGET_CHARTS.items():
            print(f"🚀 正在進入 {name}...")
            driver.get(url)
            time.sleep(15) 

            # --- 修正廣告與時間範圍 ---
            try:
                # 1. 模擬按下 ESC 鍵兩次，這可以關閉大部分 TradingView 的彈出廣告
                actions = webdriver.ActionChains(driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                actions.send_keys(Keys.ESCAPE).perform()
                
                # 2. 強制刪除網頁上的廣告元素 (JavaScript)
                driver.execute_script("""
                    var ads = document.querySelectorAll('[class*="overlap"], [class*="dialog"], [class*="popup"]');
                    for (var i = 0; i < ads.length; i++) { ads[i].remove(); }
                """)

                # 3. 切換到 6M 視圖 (按 180D + ENTER)
                print("   -> 正在切換至半年視圖...")
                actions.send_keys("180D").send_keys(Keys.ENTER).perform()
                time.sleep(10) 
            except Exception as e:
                print(f"   -> ⚠️ 處理彈窗失敗: {e}")

            print(f"📷 正在擷取截圖...")
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            payload = {"name": name, "image_data": screenshot_b64}
            response = requests.post(GAS_URL, json=payload)
            print(f"✅ {name} 傳送結果: {response.text}")
            
    except Exception as e:
        print(f"🚨 執行出錯: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_and_send()
