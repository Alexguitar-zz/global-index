import os
import time
import json
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === 1. 基礎配置 ===
# 請在此填入你的 Google 帳號 Email，機器人會把報表分享給你
USER_EMAIL = "alexguitar@gmail.com" 

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def capture_charts():
    log("正在啟動瀏覽器並擷取圖表...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    results = []
    
    try:
        for name, url in TARGET_CHARTS.items():
            log(f"🚀 擷取標的: {name}")
            driver.get(url)
            time.sleep(25) # 確保圖表完全載入
            filename = f"{name.replace(' ', '_')}.png"
            driver.save_screenshot(filename)
            if os.path.exists(filename):
                results.append((name, filename))
        return results
    except Exception as e:
        log(f"❌ 瀏覽器出錯: {e}")
        return []
    finally:
        driver.quit()

def upload_and_create_doc(chart_files):
    log("正在連線 Google API 建立報表...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_raw:
            log("❌ 錯誤：GitHub Secrets 未設定 GOOGLE_CREDENTIALS")
            return

        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # A. 建立 Google Doc (發生 403 錯誤的地方)
        doc_metadata = {'title': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}"}
        doc = docs_service.documents().create(body=doc_metadata).execute()
        doc_id = doc.get('documentId')
        log(f"📄 文件建立成功！ID: {doc_id}")

        # B. 將文件分享給 Lex 的個人帳號
        if USER_EMAIL != "你的Email@gmail.com":
            drive_service.permissions().create(
                fileId=doc_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
            ).execute()
            log(f"📧 已將文件分享給: {USER_EMAIL}")

        requests = []
        for name, filepath in reversed(chart_files):
            # C. 上傳圖片到 Drive
            media = MediaFileUpload(filepath, mimetype='image/png')
            file_metadata = {'name': filepath}
            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            
            # D. 分享圖片並插入 Doc
            drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            img_url = f"https://drive.google.com/uc?id={file_id}"

            requests.append({'insertText': {'location': {'index': 1}, 'text': f"\n📈 {name}\n"}})
            requests.append({
                'insertInlineImage': {
                    'location': {'index': 1},
                    'uri': img_url,
                    'objectSize': {'height': {'magnitude': 350, 'unit': 'PT'}, 'width': {'magnitude': 550, 'unit': 'PT'}}
                }
            })

        if requests:
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            log("✅ 報表內容填充完成！")
            
    except Exception as e:
        log(f"🚨 Google API 權限錯誤：{e}")
        log("💡 提示：請檢查 Google Cloud 是否啟用了 'Google Docs API' 與 'Google Drive API'")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
    else:
        log("❌ 沒有擷取到任何圖表，請檢查網路或 TradingView 網址。")
        sys.exit(1)
