import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === 1. 配置 Lex 的觀察標的 ===
TARGET_CHARTS = {
    "S&P 500 指數": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA 個股": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def get_browser():
    """配置雲端運行的 Chrome 瀏覽器"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def capture_charts():
    """執行 TradingView 截圖任務"""
    driver = get_browser()
    results = []
    try:
        for name, url in TARGET_CHARTS.items():
            print(f"🚀 正在擷取 {name}...")
            driver.get(url)
            time.sleep(15)  # 等待指標載入
            filename = f"{name.replace(' ', '_')}.png"
            driver.save_screenshot(filename)
            results.append((name, filename))
        return results
    finally:
        driver.quit()

def create_report(images):
    """將圖檔存入 Drive 並建立 Google Doc"""
    # 讀取 GitHub Secrets 裡的密鑰
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_raw:
        print("❌ 錯誤：找不到 GOOGLE_CREDENTIALS 設定")
        return

    creds_info = json.loads(creds_raw)
    creds = service_account.Credentials.from_service_account_info(creds_info)
    
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # 建立新文件
    title = f"Lex_市場日報_{datetime.now().strftime('%Y-%m-%d')}"
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc.get('documentId')

    requests = []
    for name, path in reversed(images):
        # 上傳到 Drive (Doc 需要透過連結插入圖片)
        media = MediaFileUpload(path, mimetype='image/png')
        uploaded = drive_service.files().create(body={'name': path}, media_body=media, fields='id').execute()
        file_id = uploaded.get('id')
        
        # 開啟分享權限
        drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        img_url = f"https://drive.google.com/uc?id={file_id}"

        requests.append({'insertText': {'location': {'index': 1}, 'text': f"\n📈 {name} (日線圖)\n"}})
        requests.append({
            'insertInlineImage': {
                'location': {'index': 1},
                'uri': img_url,
                'objectSize': {'height': {'magnitude': 350, 'unit': 'PT'}, 'width': {'magnitude': 550, 'unit': 'PT'}}
            }
        })

    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    print(f"✅ 完成！文件連結: https://docs.google.com/document/d/{doc_id}")

if __name__ == "__main__":
    captured = capture_charts()
    if captured:
        create_report(captured)
