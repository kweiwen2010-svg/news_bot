import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
import requests
import edge_tts
from google import genai

# ==========================================
# 環境變數與設定區塊
# ==========================================
load_dotenv_path = os.getenv("DOTENV_PATH")
if load_dotenv_path:
    from dotenv import load_dotenv
    load_dotenv(load_dotenv_path)

TW_TZ = ZoneInfo("Asia/Taipei")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
VOICE_NAME = "zh-TW-HsiaoChenNeural"  # 微軟親切女聲
OUTPUT_MP3 = "morning_news.mp3"


# ==========================================
# 1. 市場數據與氣象抓取區塊
# ==========================================
def get_weather() -> str:
    """簡單抓取當天台灣主要地區天氣（以台北為例）"""
    try:
        url = "https://wttr.in/Taipei?format=1&lang=zh-tw"
        resp = requests.get(url, headers=HEADERS, timeout=10)
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

def fetch_news() -> str:
    print("🚀 正在抓取最新焦點新聞...")
    try:
        rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        
        news_titles = []
        exclude_keywords = ["2026年5月", "2026年6月", "2026年7月", "2026年8月"]
        
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:40]:
                title = entry.title
                if any(k in title for k in exclude_keywords):
                    continue
                news_titles.append(f"- {title}")
                if len(news_titles) >= 25:
                    break
                    
        print(f"DEBUG: 過濾後實際採用新聞數量為 -> {len(news_titles)}")
        return "\n".join(news_titles)
    except Exception as e:
        print(f"⚠️ 新聞抓取發生例外: {e}")
        return "- 暫時無法取得即時新聞"


# ==========================================
# 2. 呼叫 Gemini 生成口語廣播稿
# ==========================================
def generate_radio_script(raw_news: str) -> str:
    print("🤖 正在呼叫 Gemini 生成口語廣播稿...")
    
    if not GEMINI_API_KEY:
        raise ValueError("❌ 錯誤：找不到 GEMINI_API_KEY，請確認 GitHub Secrets 設定！")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_str = datetime.now(TW_TZ).strftime("%Y 年 %m 月 %d 日")
    
    prompt = f"""
你是一位專業且親切的新聞播報員。
今天是 {today_str}，請根據以下提供的最新新聞標題，撰寫一份內容豐富、結構流暢的晨間新聞廣播稿。

【極重要格式與數量要求】
1. 絕對不要使用任何星號 (*)、井字號 (#)、粗體語法或 Markdown 符號。因為這段文字會直接轉成語音，任何符號被唸出來都會破壞體驗。
2. 請直接以口語化、順暢的純文字敘述，包含簡單的開場與結尾。
3. 請從下方列表中精選 12 至 15 則重要焦點新聞進行播報，讓內容更豐富充實。

【新聞原始資料】
{raw_news}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ==========================================
# 3. 使用 edge-tts 合成語音檔
# ==========================================
async def generate_audio(text: str):
    print("🎙️ 正在合成語音檔...")
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(OUTPUT_MP3)


# ==========================================
# 4. 發送 Telegram 文字看板與語音訊息（具備防斷線保護）
# ==========================================
def send_telegram_notifications(script_text: str):
    print("📲 正在發送 Telegram 推播...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：找不到 Telegram Bot Token 或 Chat ID！")
        
    now = datetime.now(TW_TZ)
    week_map = {"Monday": "週一", "Tuesday": "週二", "Wednesday": "週三", "Thursday": "週四", "Friday": "週五", "Saturday": "週六", "Sunday": "週日"}
    ch_weekday = week_map.get(now.strftime("%A"), now.strftime("%A"))
    date_str = now.strftime('%Y-%m-%d')
    today_str = f"{date_str} ({ch_weekday})"
    
    # A. 發送文字看板
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
        "💡 **交易提醒**：盤勢瞬息萬變，嚴守紀律、控管風險！🚀"
    ]
    full_report = "\n".join(report)
    
    msg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': full_report, 'parse_mode': 'Markdown'}
    
    try:
        resp = requests.post(msg_url, data=payload, timeout=30)
        if resp.status_code != 200:
            payload.pop('parse_mode', None)
            requests.post(msg_url, data=payload, timeout=30)
        print("✅ 文字看板發送成功！")
    except Exception as e:
        print(f"⚠️ 發送文字看板發生例外（已忽略以防中斷流程）: {e}")

    # B. 發送語音訊息（Timeout 提高至 60 秒）
    voice_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    voice_payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f"🎧 您的每日全球焦點晨報語音 ({today_str})"
    }
    
    try:
        with open(OUTPUT_MP3, 'rb') as audio_file:
            files = {'voice': audio_file}
            voice_resp = requests.post(voice_url, data=voice_payload, files=files, timeout=60)
            
        if voice_resp.status_code == 200:
            print("✅ 語音廣播推播發送成功！")
        else:
            print(f"❌ 語音發送失敗！狀態碼: {voice_resp.status_code}, 內容: {voice_resp.text}")
    except Exception as e:
        print(f"⚠️ 發送語音發生例外（已忽略以防中斷流程）: {e}")


# ==========================================
# 主程式執行入口
# ==========================================
async def main():
    print("🚀 開始執行 DNA 4.0 總經與新聞廣播流程...")
    raw_news = fetch_news()
    script = generate_radio_script(raw_news)
    await generate_audio(script)
    send_telegram_notifications(script)
    
    # 清理暫存檔
    if os.path.exists(OUTPUT_MP3):
        os.remove(OUTPUT_MP3)

if __name__ == "__main__":
    asyncio.run(main())