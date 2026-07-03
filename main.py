import os
import time
import requests
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# === 【最重要】請在環境變數或 GitHub Secrets 中設定 GAS_URL ===
GAS_URL = os.environ.get("GAS_URL")
if not GAS_URL:
    print("🚨 錯誤: 環境變數 GAS_URL 未設定。請在 GitHub Secrets 中設定。")
    sys.exit(1)

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
            time.sleep(18) # 增加等待時間確保圖表完全加載

            # --- 強力廣告清除與時間範圍切換 ---
            try:
                # 1. 模擬 ESC 鍵關閉彈窗
                actions = webdriver.ActionChains(driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                
                # 2. 用 JavaScript 強制刪除所有遮罩與廣告視窗 (針對藍色彈窗優化)
                driver.execute_script("""
                    var ads = document.querySelectorAll('[class*="overlap"], [class*="dialog"], [class*="popup"], [class*="drawer"]');
                    ads.forEach(el => el.remove());
                    // 移除特定廣告遮罩層
                    var backdrop = document.querySelector('.tv-dialog__backdrop');
                    if(backdrop) backdrop.remove();
                """)

                # 3. 切換至半年 (180D) 視圖，確保範圍從去年9月開始
                print("   -> 正在切換至半年視圖...")
                actions.send_keys("180D").send_keys(Keys.ENTER).perform()
                time.sleep(12) 
            except Exception as e:
                print(f"   -> ⚠️ 廣告處理出錯: {e}")

            print(f"📷 正在擷取截圖...")
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            payload = {"name": name, "image_data": screenshot_b64}
            response = requests.post(GAS_URL, json=payload, timeout=30)
            response.raise_for_status()
            print(f"✅ {name} 傳送結果: {response.text}")
            
    except Exception as e:
        print(f"🚨 執行出錯: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_and_send()
