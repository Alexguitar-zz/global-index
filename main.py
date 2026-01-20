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
# 這是你剛才確認的資料夾 ID
FOLDER_ID = "1gLds-cG9H3NoRBinJJRylvcY7zTmiNS4" 

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def capture_charts():
    log("正在啟動瀏覽器進行市場觀測...")
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
            log(f"🚀 正在擷取圖表: {name}")
            driver.get(url)
            time.sleep(25) # 給予充足時間加載技術指標
            filename = f"{name.replace(' ', '_')}.png"
            driver.save_screenshot(filename)
            if os.path.exists(filename):
                results.append((name, filename))
        return results
    except Exception as e:
        log(f"❌ 擷取過程出錯: {e}")
        return []
    finally:
        driver.quit()

def upload_and_create_doc(chart_files):
    log("正在啟動 Google API 定向寫入任務...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # 📄 在指定資料夾建立 Google Doc
        log(f"📄 正在資料夾 {FOLDER_ID} 中建立 Google Doc...")
        file_metadata = {
            'name': f"Lex_交易日報_{datetime.now().strftime('%Y-%m-%d')}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [FOLDER_ID]
        }
        doc_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = doc_file.get('id')
        log(f"✅ 報表文件建立成功！ID: {doc_id}")

        # 📧 自動分享給 Lex (alexguitar@gmail.com)
        drive_service.permissions().create(
            fileId=doc_id,
            body={'type': 'user', 'role': 'writer', 'emailAddress': USER_EMAIL}
        ).execute()

        requests = []
        for name, filepath in reversed(chart_files):
            # 📤 圖片也上傳到同一個資料夾
            media = MediaFileUpload(filepath, mimetype='image/png')
            uploaded_file = drive_service.files().create(
                body={'name': filepath, 'parents': [FOLDER_ID]}, 
                media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            
            # 開啟分享權限以便插入 Doc
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
            log("🎉 交易日報已完美生成，請前往雲端硬碟查看！")
            
    except Exception as e:
        log(f"🚨 執行錯誤：{e}")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        upload_and_create_doc(images)
    else:
        log("❌ 未擷取到任何圖表，程式終止。")
        sys.exit(1)
