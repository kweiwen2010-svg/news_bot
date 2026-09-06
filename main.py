import os
import asyncio
import urllib.parse
import requests
import feedparser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import edge_tts

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_weather() -> str:
    """簡單抓取當天台灣主要地區天氣（以台北為例）"""
    try:
        url = "https://wttr.in/Taipei?format=1&lang=zh-tw"
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return f"🌤️ **當天氣象預報**\n▸ 台北地區: {resp.text.strip()}"
    except Exception:
        pass
    return "🌤️ **當天氣象**：暫時無法取得"

def get_gold_price() -> str:
    """抓取國際金價 (XAU)"""
    try:
        url = "https://api.gold-api.com/price/XAU"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        price = data.get("price", 0)
        return f"🟡 **國際黃金市場**\n▸ 黃金現貨 (XAU): ${price:,.2f} USD / 盎司"
    except Exception:
        return "🟡 **國際黃金**：數據暫時無法取得"

def get_crypto_prices() -> str:
    """抓取比特幣與乙太幣最新行情"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        btc = data.get("bitcoin", {})
        eth = data.get("ethereum", {})
        return (
            f"💰 **加密貨幣市場**\n"
            f"▸ Bitcoin (BTC): ${btc.get('usd', 0):,.0f} ({btc.get('usd_24h_change', 0):+.2f}%)\n"
            f"▸ Ethereum (ETH): ${eth.get('usd', 0):,.0f} ({eth.get('usd_24h_change', 0):+.2f}%)"
        )
    except Exception:
        return "💰 **加密貨幣**：數據暫時無法取得"

def get_market_news() -> str:
    """抓取前天整天的財經焦點新聞"""
    try:
        now = datetime.now(TW_TZ)
        # 計算前天的日期
        day_before_yesterday = now - timedelta(days=2)
        yesterday = now - timedelta(days=1)
        
        dby_str = day_before_yesterday.strftime('%Y-%m-%d')
        y_str = yesterday.strftime('%Y-%m-%d')
        
        # 利用 Google 搜尋語法指定 after 與 before 鎖定前天
        query_str = f"財經 股市 after:{dby_str} before:{y_str}"
        query = urllib.parse.quote(query_str)
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            news_titles = []
            for entry in feed.entries[:3]:
                news_titles.append(f"▸ {entry.title}")
            if news_titles:
                return f"📰 **前天 ({dby_str}) 財經焦點新聞**\n" + "\n".join(news_titles)
        return f"📰 **前天財經焦點新聞**：暫無相關新聞"
    except Exception as e:
        print(f"⚠️ 新聞抓取錯誤: {e}")
        return "📰 **財經焦點新聞**：暫時無法取得"

def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code != 200:
        payload.pop('parse_mode')
        requests.post(url, data=payload, timeout=15)

def send_telegram_voice(audio_path: str):
    """發送語音訊息至 Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    with open(audio_path, 'rb') as voice_file:
        files = {'voice': voice_file}
        data = {'chat_id': TELEGRAM_CHAT_ID}
        requests.post(url, data=data, files=files, timeout=30)

async def generate_edge_tts(text: str, output_path: str):
    """使用 edge-tts 生成高品質語音"""
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(output_path)

def main():
    now = datetime.now(TW_TZ)
    week_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
    ch_weekday = week_map.get(now.strftime("%A"), now.strftime("%A"))
    date_str = now.strftime('%Y-%m-%d')
    today_str = f"{date_str} ({ch_weekday})"
    
    # 組合文字晨報（含氣象、金價、加密貨幣、前天新聞）
    report = [
        f"🌅 **【DNA 4.0 每日市場總經速報】**",
        f"📅 日期：{today_str}",
        "─" * 28,
        get_weather(),
        "─" * 28,
        get_gold_price(),
        "─" * 28,
        get_crypto_prices(),
        "─" * 28,
        get_market_news(),
        "─" * 28,
        "💡 **交易提醒**：盤勢瞬息萬變，嚴守紀律、控管風險！🚀"
    ]
    
    full_report = "\n".join(report)
    send_telegram_message(full_report)

    # 語音播報
    try:
        print("🔊 正在透過 edge-tts 生成高品質語音...")
        voice_text = f"您好，今天是 {date_str}，您的 D.N.A. 四點零，每日市場總經速報已送達。祝您操作順利，交易長紅！"
        audio_file = "morning_voice.mp3"
        
        asyncio.run(generate_edge_tts(voice_text, audio_file))
        send_telegram_voice(audio_file)
        
        if os.path.exists(audio_file):
            os.remove(audio_file)
        print("✅ 語音晨報發送成功！")
    except Exception as e:
        print(f"⚠️ 語音生成或發送失敗：{e}")

if __name__ == "__main__":
    main()