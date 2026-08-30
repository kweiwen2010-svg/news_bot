import os
import re
import asyncio
import feedparser
import google.generativeai as genai
from edge_tts import Communicate
import requests
from datetime import datetime

# 初始化 Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def fetch_news():
    """抓取 RSS 新聞摘要"""
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    news_items = []
    for entry in feed.entries[:5]:
        news_items.append(f"標題：{entry.title}\n摘要：{entry.summary}")
    
    return "\n\n".join(news_items)

def generate_radio_script(raw_news):
    """將新聞文字整理為廣播稿"""
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

def send_to_telegram(script_text, audio_path="news.mp3"):
    """推播音訊至 Telegram（加入日期標題、演出者與文字摘要）"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # 取得今天日期（例如：08月30日）
    today_date = datetime.now().strftime("%m月%d日")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    
    # 🟢 補齊廣播卡片標題、播報員與下方文字摘要
    data = {
        "chat_id": chat_id,
        "title": f"晨間新聞廣播 ({today_date})",
        "performer": "AI 資訊鬧鐘",
        "caption": f"🎙️ **【{today_date} 晨間新聞摘要】**\n\n{script_text[:800]}..." # 隨附文字摘要（前 800 字）
    }
    
    with open(audio_path, "rb") as audio:
        requests.post(url, data=data, files={"audio": audio})

async def main():
    print("🚀 開始執行新聞廣播流程...")
    raw_news = fetch_news()
    script = generate_radio_script(raw_news)
    
    # 🟢 雙重過濾：剔除括號音樂標註、主持人標籤與 Markdown 符號
    script = re.sub(r'[\(\[\（\【].*?[\)\]\）\】]', '', script)
    script = re.sub(r'主持人[：:]\s*', '', script)
    script = re.sub(r'[*#\_~`]', '', script)
    
    await generate_audio(script)
    # 傳入 script 讓 Telegram 訊息同步帶上文字摘要
    send_to_telegram(script)
    print("✅ 廣播推播完成！")

if __name__ == "__main__":
    asyncio.run(main())