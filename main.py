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
# 請在此填入你剛才建立的那份 Google 文件的 ID
TARGET_DOC_ID = "1pTKuW4hhvgFrZ4OVsADWVG2gzhD5zty-42K1mY4Bh_c" 

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

TARGET_CHARTS = {
    "S&P 500 Index": "https://www.tradingview.com/chart/?symbol=SPX",
    "NVIDIA Corp": "https://www.tradingview.com/chart/?symbol=NASDAQ:NVDA"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def capture_charts():
    log("正在啟動瀏覽器擷取圖表...")
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
            log(f"🚀 擷取標的: {name}")
            driver.get(url)
            time.sleep(25) 
            filename = f"{name.replace(' ', '_')}.png"
            driver.save_screenshot(filename)
            if os.path.exists(filename):
                results.append((name, filename))
        return results
    finally:
        driver.quit()

def update_existing_report(chart_files):
    log("正在連線 Google API 並更新報表...")
    try:
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # 1. 取得文件當前狀態以準備清空內容
        doc = docs_service.documents().get(documentId=TARGET_DOC_ID).execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex')

        # 2. 準備更新指令：先清空，再寫入新內容
        requests = []
        if end_index > 2:
            requests.append({'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index - 1}}})

        requests.append({'insertText': {'location': {'index': 1}, 'text': f"Lex 交易觀測日報 (更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')})\n"}})

        for name, filepath in reversed(chart_files):
            # 圖片上傳 (上傳完插入後會立刻刪除，節省空間)
            media = MediaFileUpload(filepath, mimetype='image/png')
            uploaded_file = drive_service.files().create(body={'name': filepath}, media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            
            drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            img_url = f"https://drive.google.com/uc?id={file_id}"

            requests.append({'insertText': {'location': {'index': 1}, 'text': f"\n📈 {name}\n"}})
            requests.append({'insertInlineImage': {'location': {'index': 1}, 'uri': img_url, 'objectSize': {'height': {'magnitude': 350, 'unit': 'PT'}, 'width': {'magnitude': 550, 'unit': 'PT'}}}})

        # 3. 執行文件更新
        docs_service.documents().batchUpdate(documentId=TARGET_DOC_ID, body={'requests': requests}).execute()
        
        # 4. 關鍵清理：刪除剛上傳的圖片釋放空間
        for f in chart_files:
            # 搜尋剛建立的檔案並徹底刪除
            q = f"name = '{f[1]}' and trashed = false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            for item in res.get('files', []):
                drive_service.files().delete(fileId=item['id']).execute()

        log("🎉 報表已成功更新至你的 Google Doc！")
            
    except Exception as e:
        log(f"🚨 錯誤：{e}")
        sys.exit(1)

if __name__ == "__main__":
    images = capture_charts()
    if images:
        update_existing_report(images)
