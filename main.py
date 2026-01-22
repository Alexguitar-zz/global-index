import os
import time
import base64
import requests
import sys
# 新增必要的 Selenium 工具匯入
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === 基礎配置 ===
# 請確認這還是你最新的 GAS URL
GAS_URL = "https://script.google.com/macros/s/AKfycbuZv3MQ9mMxpj6GqfUWHDGzDpLq7wv2Zyv8mLNAqb3NBQvrz4NUnEQMbaaPv1Y8Bd6N/exec"

# 戰情清單
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
    # 設定一個智慧等待時間
    wait = WebDriverWait(driver, 20)
    
    try:
        for name, url in TARGET_CHARTS.items():
            print(f"🚀 正在進入 {name}...")
            driver.get(url)
            
            try:
                print("   -> 正在尋找並點擊 '6M' (6個月) 視圖按鈕...")
                # 1. 等待底部的時間範圍選擇器出現
                # 我們尋找帶有 data-name="time-range-selector" 的元素
                time_range_selector = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-name="time-range-selector"]')))
                
                # 2. 在選擇器中找到 '6M' 按鈕
                # TradingView 的按鈕通常用 data-value="6M" 來標識
                six_month_btn = time_range_selector.find_element(By.CSS_SELECTOR, '[data-value="6M"]')
                
                # 3. 使用 JavaScript 強制點擊 (比普通點擊更穩定)
                driver.execute_script("arguments[0].click();", six_month_btn)
                print("   -> ✅ 已點擊 '6M'，等待圖表重繪...")
                
                # 4. 點擊後給它 8 秒鐘重新繪製圖表
                time.sleep(8)
                
            except Exception as e:
                print(f"   -> ⚠️ 切換時間範圍失敗 (將使用預設視圖): {e}")
                # 如果找不到按鈕，就用舊方法等待一下
                time.sleep(15)

            print(f"📷 正在擷取截圖...")
            # 將截圖轉為 base64
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            # 傳送給 GAS 橋接器
            payload = {
                "name": name,
                "image_data": screenshot_b64
            }
            print(f"📡 正在傳送 {name} 至 Google Doc...")
            response = requests.post(GAS_URL, json=payload)
            print(f"✅ {name} 傳送結果: {response.text}")
            
    except Exception as e:
        print(f"🚨 執行出錯: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_and_send()
