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

def fetch_rss_titles(query: str, max_items: int = 10) -> list:
    """依關鍵字抓取 Google RSS 新聞標題清單"""
    try:
        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            titles = []
            for entry in feed.entries[:max_items]:
                titles.append(entry.title)
            return titles
    except Exception as e:
        print(f"⚠️ 抓取新聞錯誤 ({query}): {e}")
    return []

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
    """使用 edge-tts 生成高品質微軟語音"""
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(output_path)

def main():
    now = datetime.now(TW_TZ)
    week_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
    ch_weekday = week_map.get(now.strftime("%A"), now.strftime("%A"))
    date_str = now.strftime('%Y-%m-%d')
    today_str = f"{date_str} ({ch_weekday})"
    
    # 抓取各類新聞與天氣（嘉義市天氣、台灣新聞、國際新聞）
    chiayi_weather_news = fetch_rss_titles("嘉義市 天氣", max_items=8)
    taiwan_news = fetch_rss_titles("台灣 要聞", max_items=11)
    intl_news = fetch_rss_titles("國際 新聞", max_items=11)

    # 組合 Telegram 文字看板報告
    report_lines = [
        f"🌅 **【DNA 4.0 每日市場與地方速報】**",
        f"📅 日期：{today_str}",
        "─" * 28,
        get_gold_price(),
        "─" * 28,
        get_crypto_prices(),
        "─" * 28,
        "🌤️ **嘉義市氣象與在地動態**"
    ]
    for t in chiayi_weather_news:
        report_lines.append(f"▸ {t}")

    report_lines.append("─" * 28)
    report_lines.append("🇹🇼 **台灣要聞焦點**")
    for t in taiwan_news:
        report_lines.append(f"▸ {t}")

    report_lines.append("─" * 28)
    report_lines.append("🌍 **國際新聞動態**")
    for t in intl_news:
        report_lines.append(f"▸ {t}")

    report_lines.extend([
        "─" * 28,
        "💡 **交易提醒**：盤勢瞬息萬變，嚴守紀律、控管風險！🚀"
    ])

    full_report = "\n".join(report_lines)
    send_telegram_message(full_report)

    # 建構高品質的語音包內容（精選約 10 則重點新聞連貫播報）
    try:
        print("🔊 正在透過 edge-tts 生成專屬語音廣播包...")
        voice_intro = f"您好，今天是 {date_str}。歡迎收聽 D.N.A. 四點零每日晨間廣播包。"
        
        # 挑選精華組合成大約 10 則的語音播報稿
        v_weather = "。".join(chiayi_weather_news[:2]) if chiayi_weather_news else "暫無在地氣象資訊"
        v_taiwan = "。".join(taiwan_news[:4]) if taiwan_news else ""
        v_intl = "。".join(intl_news[:4]) if intl_news else ""
        
        voice_text = f"{voice_intro}。首先是嘉義市氣象與在地動態：{v_weather}。接著是台灣要聞：{v_taiwan}。國際焦點新聞：{v_intl}。以上是今天的重點播報，祝您操作順利，交易長紅！"
        
        audio_file = "morning_voice.mp3"
        asyncio.run(generate_edge_tts(voice_text, audio_file))
        send_telegram_voice(audio_file)
        
        if os.path.exists(audio_file):
            os.remove(audio_file)
        print("✅ 語音廣播包發送成功！")
    except Exception as e:
        print(f"⚠️ 語音生成或發送失敗：{e}")

if __name__ == "__main__":
    main()