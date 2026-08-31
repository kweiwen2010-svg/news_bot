import os
import re
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo  # 時區處理
from dotenv import load_dotenv  # 本地開發自動載入 .env
import feedparser
import requests
import edge_tts
from google import genai

# 載入 .env 檔（本地開發使用）
load_dotenv()

# 設定台灣時區
TW_TZ = ZoneInfo("Asia/Taipei")

# ==========================================
# 環境變數與設定區塊
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"DEBUG: GEMINI_API_KEY 長度為 -> {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")

VOICE_NAME = "zh-TW-HsiaoChenNeural"  # 微軟親切女聲
OUTPUT_MP3 = "morning_news.mp3"


# ==========================================
# 0. 抓取嘉義即時氣象 (免 API Key)
# ==========================================
def fetch_chiayi_weather() -> str:
    print("🌤️ 0/5 正在抓取嘉義氣象資訊...")
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=23.48&longitude=120.45&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FTaipei"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        daily = data.get("daily", {})
        max_temp = daily.get("temperature_2m_max", ["--"])[0]
        min_temp = daily.get("temperature_2m_min", ["--"])[0]
        rain_prob = daily.get("precipitation_probability_max", ["--"])[0]
        
        return f"嘉義市氣溫預測 {min_temp}~{max_temp}°C，最高降雨機率 {rain_prob}%。"
    except Exception as e:
        print(f"⚠️ 氣象抓取失敗，原因：{e}")
        return "嘉義市天氣資訊暫時無法取得。"


# ==========================================
# 1. 抓取台灣每日發燒話題 (Google Trends)
# ==========================================
def fetch_google_trends() -> str:
    print("🔥 1/5 正在抓取台灣熱搜話題...")
    try:
        rss_url = "https://trends.google.com.tw/trends/trendingsearches/daily/rss?geo=TW"
        feed = feedparser.parse(rss_url)
        
        trends = []
        for entry in feed.entries[:5]:
            trends.append(f"- {entry.title}")
            
        return "\n".join(trends) if trends else "暫無熱搜話題"
    except Exception as e:
        print(f"⚠️ 熱搜話題抓取失敗，原因：{e}")
        return "熱搜話題暫時無法取得。"


# ==========================================
# 2. 抓取嘉義市政在地新聞
# ==========================================
def fetch_chiayi_news() -> str:
    print("🏛️ 2/5 正在抓取嘉義市政新聞...")
    try:
        rss_url = "https://www.chiayi.gov.tw/News_RSS.aspx?n=4251&type=xml"
        feed = feedparser.parse(rss_url)
        
        chiayi_titles = []
        for entry in feed.entries[:5]:
            chiayi_titles.append(f"- {entry.title}")
            
        return "\n".join(chiayi_titles) if chiayi_titles else "暫無嘉義在地公告"
    except Exception as e:
        print(f"⚠️ 嘉義新聞抓取失敗，原因：{e}")
        return "嘉義在地新聞暫時無法取得。"


# ==========================================
# 3. 抓取最新國際世界新聞
# ==========================================
def fetch_world_news() -> str:
    print("🌐 3/5 正在抓取國際焦點新聞...")
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/WORLD?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        
        news_titles = []
        for entry in feed.entries[:20]:
            news_titles.append(f"- {entry.title}")
            
        return "\n".join(news_titles)
    except Exception as e:
        print(f"⚠️ 國際新聞抓取失敗，原因：{e}")
        return "國際新聞暫時無法取得。"


# ==========================================
# 4. 呼叫 Gemini 生成口語廣播稿
# ==========================================
def generate_radio_script(weather_info: str, trends_info: str, chiayi_info: str, world_news: str) -> str:
    print("🤖 4/5 正在呼叫 Gemini 生成口語廣播稿...")
    
    if not GEMINI_API_KEY:
        raise ValueError("❌ 錯誤：找不到 GEMINI_API_KEY，請確認環境變數或 GitHub Secrets 設定！")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_str = datetime.now(TW_TZ).strftime("%Y 年 %m 月 %d 日")
    
    prompt = f"""
你是一位專業且親切的新聞晨報主持人。
今天是 {today_str}，請根據以下提供的在地氣象、熱搜話題、在地新聞與國際新聞，撰寫一份順暢的晨間新聞廣播稿。

【廣播稿結構要求】
1. **親切開場與氣象**：簡短問候（如：「大家早安，歡迎收聽晨間新聞廣播...」），並結合【嘉義氣象】給予嘉義在地聽眾貼心的出門穿著與帶傘建議。
2. **台灣熱門話題**：用 1 至 2 句話快速帶出今天台灣網路社群最關注的【熱搜話題】，當作輕鬆的暖身話題。
3. **嘉義在地生活**：從【嘉義市政新聞】中精選 1 至 2 則與生活、道路或活動相關的重要公告進行播報。
4. **全球國際焦點**：從【國際新聞】中精選 6 至 8 則重要全球大事，進行口語化、順暢且富含資訊量的播報。
5. **溫馨結尾**：流暢結尾並祝福聽眾有美好的一天。

【語氣指示】
語氣自然順暢、適合語音合成輸出，避免使用過多的標點符號、星號、粗體或 Markdown 格式。

【參考資料庫】
[嘉義氣象]
{weather_info}

[台灣熱搜話題]
{trends_info}

[嘉義在地新聞]
{chiayi_info}

[國際焦點新聞]
{world_news}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ==========================================
# 5. 使用 edge-tts 合成語音檔
# ==========================================
async def generate_audio(text: str):
    print("🎙️ 5/5 正在合成語音檔...")
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(OUTPUT_MP3)


# ==========================================
# Telegram 發送與清理
# ==========================================
def send_to_telegram():
    print("📲 正在發送語音訊息至 Telegram...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：找不到 Telegram Bot Token 或 Chat ID！")
        
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f"🎧 您的每日全球與在地焦點晨報 ({today_str})"
    }
    
    try:
        with open(OUTPUT_MP3, 'rb') as audio_file:
            files = {'voice': audio_file}
            response = requests.post(url, data=payload, files=files, timeout=30)
            
        if response.status_code == 200:
            print("✅ 廣播推播發送成功！")
        else:
            print(f"❌ 發送失敗！HTTP 狀態碼: {response.status_code}, 回傳內容: {response.text}")
    finally:
        if os.path.exists(OUTPUT_MP3):
            os.remove(OUTPUT_MP3)


# ==========================================
# 主程式執行入口
# ==========================================
async def main():
    print("🚀 開始執行完整版晨報廣播流程...")
    weather_info = fetch_chiayi_weather()
    trends_info = fetch_google_trends()
    chiayi_info = fetch_chiayi_news()
    world_news = fetch_world_news()
    
    script = generate_radio_script(weather_info, trends_info, chiayi_info, world_news)
    
    # 清理 markdown 符號
    script = re.sub(r'[*#\_~`]', '', script)
    
    await generate_audio(script)
    send_to_telegram()

if __name__ == "__main__":
    asyncio.run(main())