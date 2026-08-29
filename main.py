import os
import asyncio
from datetime import datetime
import feedparser
import requests
import edge_tts
from google import genai

# ==========================================
# 環境變數與設定區塊
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 輸出除錯資訊
print(f"DEBUG: GEMINI_API_KEY 長度為 -> {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")

VOICE_NAME = "zh-TW-HsiaoChenNeural"  # 微軟親切女聲
OUTPUT_MP3 = "morning_news.mp3"


# ==========================================
# 1. 抓取最新新聞
# ==========================================
def fetch_news() -> str:
    print("🚀 1/4 正在抓取最新焦點新聞...")
    # 使用 Google News 台灣焦點 RSS 來源
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    news_titles = []
    # 預先抓取前 25 則標題
    for entry in feed.entries[:25]:
        news_titles.append(f"- {entry.title}")
        
    print(f"DEBUG: 實際抓取到的新聞數量為 -> {len(news_titles)}")
    return "\n".join(news_titles)


# ==========================================
# 2. 呼叫 Gemini 生成口語廣播稿
# ==========================================
def generate_radio_script(raw_news: str) -> str:
    print("🤖 2/4 正在呼叫 Gemini 生成口語廣播稿...")
    
    if not GEMINI_API_KEY:
        raise ValueError("❌ 錯誤：找不到 GEMINI_API_KEY，請確認 GitHub Secrets 設定！")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_str = datetime.now().strftime("%Y 年 %m 月 %d 日")
    
    prompt = f"""
你是一位專業且親切的新聞晨報主持人。
今天是 {today_str}，請根據以下提供的最新新聞標題，撰寫一份約 8 分鐘的晨間新聞廣播稿。

【廣播稿要求】
1. 請包含親切的開場白（例如：「大家早安，歡迎收聽今天的晨間新聞廣播...」）與適當的結尾。
2. 請務必從下方列表中精選至少 8 至 10 則重要焦點新聞，進行口語化、順暢且富含資訊量的播報。
3. 語氣自然且適合語音合成輸出，避免使用過多的符號、星號、粗體或無關標題層級。

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
    print("🎙️ 3/4 正在合成語音檔...")
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(OUTPUT_MP3)


# ==========================================
# 4. 發送語音訊息至 Telegram (使用 sendVoice 防止連播)
# ==========================================
def send_to_telegram():
    print("📲 4/4 正在發送語音訊息至 Telegram...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：找不到 Telegram Bot Token 或 Chat ID！")
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 使用 sendVoice 替代 sendAudio
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f"🎧 您的每日全球焦點晨報 ({today_str})"
    }
    
    with open(OUTPUT_MP3, 'rb') as audio_file:
        files = {
            'voice': audio_file  # Key 改為 'voice'
        }
        response = requests.post(url, data=payload, files=files)
        
    if response.status_code == 200:
        print("✅ 廣播推播發送成功！")
    else:
        print(f"❌ 發送失敗！HTTP 狀態碼: {response.status_code}, 回傳內容: {response.text}")


# ==========================================
# 主程式執行入口
# ==========================================
async def main():
    print("🚀 開始執行新聞廣播流程...")
    raw_news = fetch_news()
    script = generate_radio_script(raw_news)
    
    # 🟢 新增這行：自動將所有星號 (*)、井號 (#) 與 Markdown 符號清除
    script = re.sub(r'[*#\_~`]', '', script)
    
    await generate_audio(script)
    send_to_telegram()

if __name__ == "__main__":
    asyncio.run(main())