import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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

def get_morning_briefing() -> str:
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d (%A)")
    
    report = [
        f"🌅 **【DNA 4.0 每日晨間全方位速報】**",
        f"📅 日期：{today_str}",
        "─" * 28,
        "🌤️ **在地氣象**",
        "▸ 嘉義地區：晴時多雲，氣溫約 27°C - 33°C，降雨機率 20%。",
        "▸ 空氣品質 (AQI)：普通 (綠燈至黃燈)。",
        "─" * 28,
        "⛽ **民生情報**",
        "▸ 本週油價：請以中油官方每週日佈達為準。",
        "─" * 28,
        get_crypto_prices(),
        "─" * 28,
        "💡 **早安小語**：新的一天，祝操作順利、交易長紅！🚀"
    ]
    return "\n".join(report)

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
    report = get_morning_briefing()
    send_telegram_message(report)

if __name__ == "__main__":
    main()