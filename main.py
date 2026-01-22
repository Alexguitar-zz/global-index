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
# 請填入你剛剛「重新部署」後得到的最新 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbzUv3MQ9mMxpj6GqfUWHDGzDpLq7wv2Zyv8mLNAqb3NBQvrz4NUnEQMbaaPv1Y8Bd6N/exec"

# 你的 2 張圖測試清單
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
            time.sleep(15) # 等待基礎框架讀取
            
            # 使用鍵盤模擬方式切換到 6個月 (6M) 視圖
            # 在 TradingView 畫面直接按 1, 8, 0, 天 (180D) 是最穩定的切換範圍方式
            try:
                print("   -> 正在切換時間範圍 (約180天)...")
                actions = webdriver.ActionChains(driver)
                actions.send_keys("180D")
                actions.send_keys(Keys.ENTER)
                actions.perform()
                time.sleep(10) # 等待圖表縮放
            except Exception as e:
                print(f"   -> ⚠️ 切換失敗: {e}")

            print(f"📷 正在擷取截圖...")
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            payload = {
                "name": name,
                "image_data": screenshot_b64
            }
            print(f"📡 正在傳送 {name}...")
            response = requests.post(GAS_URL, json=payload)
            
            # 檢查傳送結果，避免 Page Not Found
            if "Page Not Found" in response.text:
                print(f"❌ 傳送失敗：GAS 網址無效或未授權。請重新部署 GAS 為新版本！")
            else:
                print(f"✅ {name} 傳送結果: {response.text}")
            
    except Exception as e:
        print(f"🚨 執行出錯: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_and_send()
