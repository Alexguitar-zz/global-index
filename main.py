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

# === 基礎配置 ===
USER_EMAIL = "alexguitar@gmail.com" 
# 我們改用「名稱」搜尋，不用再擔心 ID 填錯
FOLDER_NAME = "global index" 

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_folder_id(drive_service):
    """自動搜尋名稱為 global index 的資料夾 ID"""
    query = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        log(f"❌ 錯誤：在你的雲端硬碟中找不到名為 '{FOLDER_NAME}' 的資料夾！")
        log("💡 請確認你已將資料夾共用給服務帳戶 Email。")
        return None
    log(f"📂 已成功定位資料夾：{items[0]['name']} (ID: {items[0]['id']})")
    return items[0]['id']

def capture_charts():
    log("正在啟動瀏覽器進行市場觀測...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    results = []
    try:
        for name, url in TARGET_CHARTS.items():
            log(f"🚀 正在擷取圖表: {name}")
            driver.get(url)
            time.sleep(25) 
            filename = f"{name.replace(' ', '_')}.png"
            driver.save_screenshot(filename)
            if os.path.exists(filename):
                results.append((name, filename))
        return results
    finally:
        driver.quit()

def upload_and_create_doc(chart_files):
    log("正在連線 Google API...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # 1. 自動搜尋資料夾 ID
        target_folder_id = get_folder_id(drive_service)
        if not target_folder_id:
            sys.exit(1)

        # 2. 建立文件
        log("📄 正在建立 Google Doc 報表...")
        file_metadata = {
            'name': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [target_folder_id]
        }
        doc_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = doc_file.get('id')

        # 3. 分享給 Lex
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
        ).execute()

        requests = []
        for name, filepath in reversed(chart_files):
            # 圖片上傳到同資料夾
            media = MediaFileUpload(filepath, mimetype='image/png')
            uploaded_file = drive_service.files().create(
                body={'name': filepath, 'parents': [target_folder_id]}, 
                media_body=media, fields='id').execute()
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
            log(f"🎉 任務大功告成！請前往 '{FOLDER_NAME}' 資料夾查看報表。")
            
    except Exception as e:
        log(f"🚨 執行出錯：{e}")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
