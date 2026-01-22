import os
import time
import base64
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# === 基礎配置 ===
# 貼上你剛才部署完產生的 GAS URL
GAS_URL = "https://script.google.com/macros/s/AKfycbzlzL_gE_0nfqDI4dOt1wV7q4o6LUfL0DFwbesZk9M/dev"

TARGET_CHARTS = {
    "S&P 500": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA",
    "台積電": "https://www.tradingview.com/chart/?symbol=TWSE:2330"
}

def capture_and_send():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        for name, url in TARGET_CHARTS.items():
            print(f"🚀 正在擷取 {name}...")
            driver.get(url)
            time.sleep(25)
            
            # 將截圖轉為 base64 字串
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            # 傳送給 GAS
            payload = {
                "name": name,
                "image_data": screenshot_b64
            }
            response = requests.post(GAS_URL, json=payload)
            print(f"📡 {name} 傳送結果: {response.text}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_and_send()
