import asyncio
from datetime import datetime
import feedparser
from google import genai
import edge_tts
import requests
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 雲端環境若未安裝 dotenv 會自動忽略，直接讀取 GitHub Secrets 變數

# ==========================================
# 填入你的個人 Key 與 ID
# ==========================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 語音與檔案設定
VOICE_NAME = "zh-TW-HsiaoChenNeural" # 微軟親切女聲
OUTPUT_MP3 = "morning_news.mp3"

# ==========================================
# 1. 抓取 RSS 新聞 (Google News 台灣焦點)
# ==========================================
def fetch_top_news() -> str:
    rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    news_titles = []
    # 抓取前 25 則最新新聞
    for entry in feed.entries[:25]:
        news_titles.append(f"- {entry.title}")
        
    return "\n".join(news_titles)

# ==========================================
# 2. 呼叫 Gemini 生成口語廣播稿
# ==========================================
def generate_radio_script(raw_news: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_str = datetime.now().strftime("%Y 年 %m 月 %d 日")
    
    prompt = f"""
    你是一位專業且親切的新聞晨報主持人。
請根據以下蒐集到的新聞標題，撰寫一份約 3 到 4 分鐘的「晨間焦點新聞廣播稿」。

最新新聞來源：
{raw_news}

寫作規範：
1. 涵蓋 5 至 7 則重點大事（梳理政治、財經、國際與社會消費等多元議題）。
2. 每則新聞講述核心重點即可，避免單一新聞佔用過多篇幅。
3. 全文必須完全「口語化」，文字流暢自然。
4. 嚴格禁止出現任何 Markdown 符號（如 **、#）、條列式標號與劇本標記。
5. 段落間使用口語連接詞順暢過渡。
6. 結尾附上一句簡短溫暖的晨間祝福。
"""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text.strip()
    

# ==========================================
# 3. 轉成 MP3 語音檔
# ==========================================
async def generate_audio(text: str, output_file: str):
    communicate = edge_tts.Communicate(text, VOICE_NAME)
    await communicate.save(output_file)

# ==========================================
# 4. 發送到 Telegram 聊天室
# ==========================================
def send_to_telegram(audio_file_path: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    today_str = datetime.now().strftime("%Y-%m-%d")
    caption = f"🎧 您的每日全球焦點晨報 ({today_str})"
    
    with open(audio_file_path, 'rb') as audio:
        files = {'audio': audio}
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'caption': caption,
            'title': f"{today_str} 晨間新聞"
        }
        response = requests.post(url, data=data, files=files)
        
    if response.status_code == 200:
        print("✅ 4/4 Telegram 語音推播成功！請查看手機。")
    else:
        print(f"❌ 推播失敗，錯誤訊息: {response.text}")

# ==========================================
# 主流程
# ==========================================
async def main():
    print("🚀 開始執行新聞廣播測試...")
    
    print("📡 1/4 正在抓取最新焦點新聞...")
    raw_news = fetch_top_news()
    
    print("🤖 2/4 正在呼叫 Gemini 生成口語廣播稿...")
    script = generate_radio_script(raw_news)
    
    print("\n" + "="*20 + " 廣播稿內容預覽 " + "="*20)
    print(script)
    print("="*52 + "\n")
    
    print("🎙️ 3/4 正在合成 MP3 語音檔...")
    await generate_audio(script, OUTPUT_MP3)
    
    print("📤 4/4 正在發送至 Telegram...")
    send_to_telegram(OUTPUT_MP3)

if __name__ == "__main__":
    asyncio.run(main())