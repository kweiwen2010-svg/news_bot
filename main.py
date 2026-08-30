import os
import re
import asyncio
import feedparser
import google.generativeai as genai
from edge_tts import Communicate
import requests

# 初始化 Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def fetch_news():
    """抓取 RSS 新聞摘要"""
    # 請保持您原本的 RSS 抓取邏輯
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    news_items = []
    for entry in feed.entries[:5]:
        news_items.append(f"標題：{entry.title}\n摘要：{entry.summary}")
    
    return "\n\n".join(news_items)

def generate_radio_script(raw_news):
    """將新聞文字整理為廣播稿"""
    # 🟢 prompt 必須放在這個 function 裡面，才會讀得到傳進來的 raw_news
    prompt = f"""
請將以下新聞整理成一份自然的晨間廣播新聞稿：
{raw_news}

【嚴格格式要求】：
1. 請直接撰寫要朗讀的口語文案，絕對不要出現「主持人：」、「播音員：」等角色標籤。
2. 絕對不要包含任何音樂說明、音效標註或括號說明（例如：[開場音樂]、(配樂漸強) 等）。
3. 語氣自然口語，每則新聞流暢銜接即可。
"""
    response = model.generate_content(prompt)
    return response.text

async def generate_audio(text, output_file="news.mp3"):
    """使用 Edge-TTS 生成語音檔"""
    communicate = Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(output_file)

def send_to_telegram(audio_path="news.mp3"):
    """推播音訊至 Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    with open(audio_path, "rb") as audio:
        requests.post(url, data={"chat_id": chat_id}, files={"audio": audio})

async def main():
    print("🚀 開始執行新聞廣播流程...")
    raw_news = fetch_news()
    script = generate_radio_script(raw_news)
    
    # 🟢 雙重過濾：剔除括號音樂標註、主持人標籤與 Markdown 符號
    script = re.sub(r'[\(\[\（\【].*?[\)\]\）\】]', '', script)
    script = re.sub(r'主持人[：:]\s*', '', script)
    script = re.sub(r'[*#\_~`]', '', script)
    
    await generate_audio(script)
    send_to_telegram()
    print("✅ 廣播推播完成！")

if __name__ == "__main__":
    asyncio.run(main())