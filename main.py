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
FOLDER_NAME = "global index" 

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def cleanup_drive_space(drive_service):
    """大師級空間清理：清空垃圾桶並刪除舊的暫存圖檔"""
    try:
        log("🧹 正在啟動空間清理程序...")
        drive_service.files().emptyTrash().execute()
        log("✨ 垃圾桶已清空。")
    except Exception as e:
        log(f"⚠️ 清理空間時發生微小錯誤 (可忽略): {e}")

def get_folder_id(drive_service):
    query = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        log(f"❌ 找不到資料夾 '{FOLDER_NAME}'")
        return None
    log(f"📂 已成功定位資料夾：{items[0]['name']} (ID: {items[0]['id']})")
    return items[0]['id']

def capture_charts():
    log("正在啟動瀏覽器擷取市場數據...")
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
            log(f"🚀 正在擷取: {name}")
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

        # 1. 執行空間清理，防止 Quota Exceeded 錯誤
        cleanup_drive_space(drive_service)

        # 2. 定位資料夾
        target_folder_id = get_folder_id(drive_service)
        if not target_folder_id:
            sys.exit(1)

        # 3. 建立報表文件
        log("📄 正在建立今日交易日報...")
        file_metadata = {
            'name': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [target_folder_id]
        }
        # 建立文件並立即獲取 ID
        doc_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = doc_file.get('id')

        # 4. 授權給 Lex
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
        ).execute()

        requests = []
        for name, filepath in reversed(chart_files):
            # 圖片上傳
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
            log(f"🎊 自動化任務大獲全勝！請至 '{FOLDER_NAME}' 資料夾查收。")
            
    except Exception as e:
        log(f"🚨 執行出錯：{e}")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
