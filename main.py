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
# 請在此填入你的 Google 帳號 Email
USER_EMAIL = "alexguitar@gmail.com" 

# 定義存取範圍 (這是解決 403 錯誤的關鍵)
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def capture_charts():
    log("正在啟動瀏覽器...")
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
            log(f"🚀 正在擷取: {name}")
            driver.get(url)
            time.sleep(25) 
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
    log("正在初始化 Google API 認證...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_raw:
            log("❌ 錯誤：GitHub Secrets 中找不到 GOOGLE_CREDENTIALS")
            return

        creds_info = json.loads(creds_raw)
        # 修正處：明確加入 scopes 授權
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        log("📄 正在嘗試建立 Google Doc...")
        doc_metadata = {'title': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}"}
        doc = docs_service.documents().create(body=doc_metadata).execute()
        doc_id = doc.get('documentId')
        log(f"✅ 文件建立成功！ID: {doc_id}")

        # 分享給 Lex
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
        ).execute()

        requests = []
        for name, filepath in reversed(chart_files):
            media = MediaFileUpload(filepath, mimetype='image/png')
            file_metadata = {'name': filepath}
            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            
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
            log("🎉 報表內容已完美填入！")
            
    except Exception as e:
        log(f"🚨 發生錯誤：{e}")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
    else:
        log("❌ 未擷取到任何圖表，請檢查環境。")
        sys.exit(1)
