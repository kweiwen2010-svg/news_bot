import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 1. 台日韓職棒 (CPBL / NPB / KBO) 賽事抓取
# ==========================================
def fetch_asian_baseball() -> str:
    print("⚾ 正在抓取台日韓職棒 (CPBL/NPB/KBO) 賽況...")
    lines = ["⚾ **台日韓職棒 (CPBL / NPB / KBO) 今日賽事**"]
    try:
        url = "https://tw.sports.yahoo.com/baseball/"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 解析焦點賽事區塊
        game_items = soup.find_all('div', class_=lambda x: x and ('game' in str(x).lower() or 'match' in str(x).lower()))
        
        extracted = []
        for item in game_items:
            text = " ".join(item.text.split())
            if any(k in text for k in ["中職", "日職", "韓職", "兄弟", "統一", "樂天", "味全", "富邦", "台鋼", "巨人", "阪神"]):
                extracted.append(text[:50])

        if extracted:
            for g in extracted[:5]:
                lines.append(f"▸ {g}")
        else:
            lines.append("▸ 中職/日職/韓職：賽事主要於下午/傍晚開打，目前無即時賽果或今日休賽。")
            
        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ 亞職數據抓取錯誤：{e}")
        return "⚾ **台日韓職棒**：賽事數據更新中。"

# ==========================================
# 2. NBA 賽事比分 (ESPN API)
# ==========================================
def fetch_nba_scores() -> str:
    print("🏀 正在抓取 NBA 最新賽果...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        events = data.get("events", [])
        
        if not events:
            return "🏀 **NBA 賽事**：今日無排定賽事。"

        lines = ["🏀 **NBA 今日賽果與即時比分**"]
        for event in events[:5]:
            status = event.get("status", {}).get("type", {}).get("shortDetail", "未開打")
            comp = event.get("competitions", [{}])[0].get("competitors", [])
            if len(comp) == 2:
                home, away = comp[0], comp[1]
                lines.append(f"▸ {away.get('team', {}).get('displayName', '')} {away.get('score', '0')} vs {home.get('score', '0')} {home.get('team', {}).get('displayName', '')} [{status}]")
        return "\n".join(lines)
    except Exception as e:
        return "🏀 **NBA 賽事**：數據暫時無法取得。"

# ==========================================
# 3. MLB 賽事比分 (ESPN API)
# ==========================================
def fetch_mlb_scores() -> str:
    print("⚾ 正在抓取 MLB 焦點賽果...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        events = data.get("events", [])
        
        if not events:
            return "⚾ **MLB 賽事**：今日無排定賽事。"

        lines = ["⚾ **MLB 美職棒焦點賽果**"]
        for event in events[:5]:
            status = event.get("status", {}).get("type", {}).get("shortDetail", "未開打")
            comp = event.get("competitions", [{}])[0].get("competitors", [])
            if len(comp) == 2:
                home, away = comp[0], comp[1]
                lines.append(f"▸ {away.get('team', {}).get('displayName', '')} {away.get('score', '0')} vs {home.get('score', '0')} {home.get('team', {}).get('displayName', '')} [{status}]")
        return "\n".join(lines)
    except Exception as e:
        return "⚾ **MLB 賽事**：數據暫時無法取得。"

# ==========================================
# Telegram 發送
# ==========================================
def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code != 200:
        payload.pop('parse_mode')
        requests.post(url, data=payload, timeout=15)

def main():
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    print(f"🚀 開始執行全球體育戰績推播 ({today_str})...")
    
    asian = fetch_asian_baseball()
    nba = fetch_nba_scores()
    mlb = fetch_mlb_scores()
    
    full_report = f"🏆 **【全球重點體育戰績速報】({today_str})**\n\n{asian}\n\n{nba}\n\n{mlb}"
    send_telegram_message(full_report)

if __name__ == "__main__":
    main()