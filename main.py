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

# 預設觀察標的
TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_folder_id(drive_service):
    """自動定位資料夾"""
    query = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        log(f"❌ 找不到資料夾 '{FOLDER_NAME}'，請確認是否已共用給新的服務帳戶。")
        return None
    return items[0]['id']

def capture_charts():
    log("正在啟動瀏覽器擷取圖表...")
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
    finally:
        driver.quit()

def upload_and_create_doc(chart_files):
    log("正在連線 Google API 並確認權限...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        target_folder_id = get_folder_id(drive_service)
        if not target_folder_id:
            sys.exit(1)

        log("📄 正在嘗試建立報表文件...")
        file_metadata = {
            'name': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [target_folder_id]
        }
        
        # 建立文件
        doc_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = doc_file.get('id')
        log(f"✅ 文件建立成功，ID: {doc_id}")

        # 分享權限
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
        ).execute()

        requests = []
        for name, filepath in reversed(chart_files):
            # 圖片上傳 (直接上傳到資料夾)
            media = MediaFileUpload(filepath, mimetype='image/png')
            uploaded_file = drive_service.files().create(
                body={'name': filepath, 'parents': [target_folder_id]}, 
                media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            
            # 開啟分享並插入圖片
            drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            img_url = f"https://drive.google.com/uc?id={file_id}"

            requests.append({'insertText': {'location': {'index': 1}, 'text': f"\n📈 {name}\n"}})
            requests.append({'insertInlineImage': {'location': {'index': 1}, 'uri': img_url, 'objectSize': {'height': {'magnitude': 350, 'unit': 'PT'}, 'width': {'magnitude': 550, 'unit': 'PT'}}}})

        if requests:
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            log("🎉 任務成功！報表已存入雲端硬碟。")
            
    except Exception as e:
        log(f"🚨 執行錯誤：{e}")
        if "quota" in str(e).lower():
            log("💡 提示：目前的機器人空間已滿，請依照建議建立『新的服務帳戶』再試一次。")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
