GAS_URL = "https://script.google.com/macros/s/AKfycbzUv3MQ9mMxpj6GqfUWHDGzDpLq7wv2Zyv8mLNAqb3NBQvrz4NUnEQMbaaPv1Y8Bd6N/exec"

TARGET_CHARTS = {
    "1. S&P 500 指數": "https://www.tradingview.com/chart/?symbol=SPX",
    "2. 台積電 (2330)": "https://www.tradingview.com/chart/?symbol=TWSE:2330",
}

CHROME_OPTIONS = [
    "--headless",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

PAGE_LOAD_TIMEOUT = 18
CHART_SWITCH_TIMEOUT = 12
DEFAULT_TIME_RANGE = "180D"
