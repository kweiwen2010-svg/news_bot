import os
import re
import asyncio
import requests
import feedparser
from datetime import datetime
import google.generativeai as genai
from edge_tts import Communicate

# 1. 讀取環境變數
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. 抓取新聞資料
def fetch_news():
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    articles = [f"- {entry.title}" for entry in feed.entries[:5]]
    return "\n".join(articles)

# 3. 利用 Gemini 生成廣播稿並進行文字過濾
def generate_radio_script(raw_news):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
你是一位親切活潑的晨間廣播主播。請將以下新聞整理成約 300 字的晨間廣播逐字稿。

要求：
1. 口語化且自然流暢，適合播報。
2. 請直接輸出要朗讀的內容，嚴禁包含「主持人：」、「[開場音樂]」、「(配樂)」等非播報文字說明。
3. 包含晨間問候、生活提醒與重點新聞摘要。

新聞資料：
{raw_news}
"""
    response = model.generate_content(prompt)
    script = response.text

    # 過濾雜音標註與格式符號
    script = re.sub(r'[\(\[\（\【].*?[\)\]\）\】]', '', script)
    script = re.sub(r'主持人[：:]\s*', '', script)
    script = re.sub(r'[*#]', '', script)
    
    return script.strip()

# 4. 使用 Edge-TTS 生成 MP3
async def generate_audio(text, output_file="news.mp3"):
    communicate = Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(output_file)

# 5. 直接發送 MP3 到 Telegram (無需轉檔工具)
def send_to_telegram(audio_path="news.mp3"):
    today_date = datetime.now().strftime("%m月%d日")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": f"🎙️ **【{today_date} 晨間新聞廣播】**",
        "parse_mode": "Markdown",
        "title": f"晨間新聞廣播 ({today_date})",
        "performer": "AI 資訊鬧鐘"
    }

    with open(audio_path, "rb") as audio:
        requests.post(url, data=data, files={"audio": audio})

# 6. 主流程控制
async def main():
    print("🚀 開始執行新聞廣播流程...")
    raw_news = fetch_news()
    script = generate_radio_script(raw_news)
    await generate_audio(script)
    send_to_telegram("news.mp3")
    print("✅ 晨間新聞廣播推播完成！")

if __name__ == "__main__":
    asyncio.run(main())