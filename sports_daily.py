import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# 抓取 NBA 今日最新比分與賽事狀態 (ESPN API)
# ==========================================
def fetch_nba_scores() -> str:
    print("🏀 正在抓取 NBA 最新賽果與戰績...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        events = data.get("events", [])
        if not events:
            return "🏀 **NBA 賽事**：今日無排定賽事。"

        lines = ["🏀 **NBA 今日賽果與即時比分**"]
        for event in events:
            status = event.get("status", {}).get("type", {}).get("shortDetail", "未開打")
            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            
            if len(competitors) == 2:
                home = competitors[0]
                away = competitors[1]
                
                home_team = home.get("team", {}).get("displayName", "")
                home_score = home.get("score", "0")
                away_team = away.get("team", {}).get("displayName", "")
                away_score = away.get("score", "0")
                
                lines.append(f"▸ {away_team} {away_score} vs {home_score} {home_team} [{status}]")
                
        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ NBA 數據抓取失敗：{e}")
        return "🏀 **NBA 賽事**：戰績數據暫時無法取得。"

# ==========================================
# 抓取 MLB / 第二賽事戰績數據
# ==========================================
def fetch_mlb_scores() -> str:
    print("⚾ 正在抓取 MLB / 焦點賽事比分...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        events = data.get("events", [])
        if not events:
            return "⚾ **MLB 賽事**：今日無排定賽事。"

        lines = ["⚾ **MLB 今日焦點賽果**"]
        for event in events[:5]:  # 取前 5 場焦點賽事
            status = event.get("status", {}).get("type", {}).get("shortDetail", "未開打")
            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            
            if len(competitors) == 2:
                home = competitors[0]
                away = competitors[1]
                lines.append(f"▸ {away.get('team', {}).get('displayName', '')} {away.get('score', '0')} vs {home.get('score', '0')} {home.get('team', {}).get('displayName', '')} [{status}]")
                
        return "\n".join(lines)
    except Exception as e:
        return "⚾ **MLB 賽事**：數據暫時無法取得。"

# ==========================================
# Telegram 推播
# ==========================================
def send_telegram_message(text: str):
    print("📲 發送體育賽果至 Telegram...")
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
    print("🚀 開始執行體育戰績推播...")
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    
    nba_report = fetch_nba_scores()
    mlb_report = fetch_mlb_scores()
    
    full_report = f"🏆 **【今日焦點體育戰績速報】({today_str})**\n\n{nba_report}\n\n{mlb_report}"
    send_telegram_message(full_report)

if __name__ == "__main__":
    main()