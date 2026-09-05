import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 1. 台日韓職棒 (CPBL / NPB / KBO)
def fetch_asian_baseball() -> str:
    print("⚾ 正在檢查亞洲職棒昨日賽果...")
    lines = ["⚾ **台日韓職棒 (CPBL / NPB / KBO) 昨日戰績**"]
    try:
        url = "https://tw.sports.yahoo.com/baseball/"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        game_items = soup.find_all('div', class_=lambda x: x and ('game' in str(x).lower() or 'match' in str(x).lower()))
        extracted = []
        for item in game_items:
            text = " ".join(item.text.split())
            if any(k in text for k in ["中職", "日職", "韓職", "兄弟", "統一", "樂天", "味全", "富邦", "台鋼", "巨人", "阪神"]):
                extracted.append(text[:50])

        if extracted:
            for g in extracted[:5]:
                lines.append(f"▸ {g}")
            return "\n".join(lines)
    except Exception:
        pass
    return ""  # 若無有效完賽或休賽期，回傳空字串以保持版面乾淨

# 2. NBA 賽事昨日完賽結果
def fetch_nba_scores() -> str:
    print("🏀 正在抓取 NBA 昨日賽果...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        events = data.get("events", [])
        if not events:
            return ""

        finished_games = []
        for event in events:
            status_type = event.get("status", {}).get("type", {}).get("name", "")
            # 只抓取已完賽 (STATUS_FINAL) 的比賽
            if status_type == "STATUS_FINAL":
                status_detail = event.get("status", {}).get("type", {}).get("shortDetail", "已完賽")
                comp = event.get("competitions", [{}])[0].get("competitors", [])
                if len(comp) == 2:
                    home, away = comp[0], comp[1]
                    finished_games.append(f"▸ {away.get('team', {}).get('displayName', '')} {away.get('score', '0')} : {home.get('score', '0')} {home.get('team', {}).get('displayName', '')} [{status_detail}]")

        if finished_games:
            lines = ["🏀 **NBA 昨日完賽焦點**"]
            lines.extend(finished_games[:5])
            return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ NBA 抓取錯誤: {e}")
    return ""

# 3. MLB 賽事昨日完賽結果（使用 MLB 官方 API，精準過濾 Final）
def fetch_mlb_scores() -> str:
    print("⚾ 正在抓取 MLB 昨日完賽戰績...")
    try:
        # 計算「昨天」的日期（因為早上看的是昨天的美國職棒完賽結果）
        yesterday_date = (datetime.now(TW_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={yesterday_date}&hydrate=linescore"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        
        dates = data.get("dates", [])
        if not dates or not dates[0].get("games"):
            return ""

        finished_games = []
        games = dates[0].get("games", [])
        for game in games:
            status = game.get("status", {}).get("abstractGameState", "")
            
            # 關鍵過濾：只抓取狀態為 Final（已完賽）的場次，徹底排除 Preview 與 In Progress
            if status == "Final":
                teams = game.get("teams", {})
                away = teams.get("away", {})
                home = teams.get("home", {})
                
                away_name = away.get("team", {}).get("name", "")
                away_score = away.get("score", 0)
                home_name = home.get("team", {}).get("name", "")
                home_score = home.get("score", 0)
                
                finished_games.append(f"▸ {away_name} {away_score} vs {home_score} {home_name} [已完賽]")

        if finished_games:
            lines = [f"⚾ **MLB 美職棒昨日完賽戰績 ({yesterday_date})**"]
            lines.extend(finished_games[:6])
            return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ MLB API 錯誤: {e}")
    return ""

def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code != 200:
        payload.pop('parse_mode')
        requests.post(url, data=payload, timeout=15)

def main():
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    
    # 收集各項有效完賽戰報
    reports = []
    
    mlb_report = fetch_mlb_scores()
    if mlb_report:
        reports.append(mlb_report)
        
    nba_report = fetch_nba_scores()
    if nba_report:
        reports.append(nba_report)
        
    asian_report = fetch_asian_baseball()
    if asian_report:
        reports.append(asian_report)
        
    # 如果昨天完全沒有任何已完賽的賽事，則保持靜默或發送休兵通知，避免空包彈
    if not reports:
        print("ℹ️ 昨日無完賽賽事，今日略過體育戰報推播。")
        return
        
    full_report = f"🏆 **【全球重點體育昨日完賽速報】({today_str})**\n\n" + "\n\n".join(reports)
    send_telegram_message(full_report)

if __name__ == "__main__":
    main()