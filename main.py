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

# 設定 Gemini API Key
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. 抓取新聞資料
def fetch_news():
    # 範例以 Google News RSS 為例，可自由更換 RSS 來源
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:5]:  # 抓取前 5 則焦點新聞
        articles.append(f"- {entry.title}")
    return "\n".join(articles)

# 3. 利用 Gemini 生成廣播稿並進行文字過濾
def generate_radio_script(raw_news):
    model = genai.GenerativeModel('gemini-1.5-flash')
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

    # 雙重過濾：剔除括號音效標註、主持人標記與 Markdown 符號 (*, #)
    script = re.sub(r'[\(\[\（\【].*?[\)\]\）\】]', '', script)
    script = re.sub(r'主持人[：:]\s*', '', script)
    script = re.sub(r'[*#]', '', script)
    
    return script.strip()

# 4. 使用 Edge-TTS 生成原始 MP3 音訊
async def generate_audio(text, output_file="news.mp3"):
    communicate = Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(output_file)

# 5. 轉換為 .ogg 格式並改用 sendVoice API 發送到 Telegram
def send_to_telegram(audio_path="news.mp3"):
    today_date = datetime.now().strftime("%m月%d日")

    # 利用 ffmpeg 將 MP3 轉為 Telegram 語音專用 .ogg 格式
    os.system(f"ffmpeg -y -i {audio_path} -c:a libopus news.ogg")

    # 使用 sendVoice API，確保 Telegram 以語音泡泡呈現且播完即停
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": f"🎙️ **【{today_date} 晨間新聞廣播】**",
        "parse_mode": "Markdown"
    }

    with open("news.ogg", "rb") as voice:
        requests.post(url, data=data, files={"voice": voice})

# 6. 主流程控制
async def main():
    print("🚀 開始執行新聞廣播流程...")
    
    # 步驟 1: 抓新聞
    raw_news = fetch_news()
    
    # 步驟 2: AI 生成並清理文案
    script = generate_radio_script(raw_news)
    
    # 步驟 3: 生成 MP3 語音檔
    await generate_audio(script)
    
    # 步驟 4: 轉碼並發送到 Telegram
    send_to_telegram("news.mp3")
    
    print("✅ 晨間新聞廣播推播完成！")

if __name__ == "__main__":
    asyncio.run(main())