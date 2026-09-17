import os
import requests
import feedparser
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from google import genai

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_twse_hot_stocks():
    print("📊 正在抓取證交所法人與成交量資料...")
    try:
        t86_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        t86_resp = requests.get(t86_url, timeout=15)
        t86_data = t86_resp.json() if t86_resp.status_code == 200 else []

        hot_stocks = []
        for item in t86_data:
            code = item.get("Code", "")
            name = item.get("Name", "").strip()
            
            if len(code) != 4 or not code.isdigit():
                continue
                
            try:
                foreign_buy = int(item.get("ForeignInvestorsDifference", "0").replace(",", ""))
                trust_buy = int(item.get("InvestmentTrustDifference", "0").replace(",", ""))
                
                total_diff = foreign_buy + trust_buy
                # 放寬條件：只要合計法人買超 > 0 就納入觀察
                if total_diff > 0:
                    hot_stocks.append({
                        "code": code,
                        "name": name,
                        "foreign": foreign_buy // 1000,
                        "trust": trust_buy // 1000,
                        "total_chip": total_diff // 1000
                    })
            except ValueError:
                continue

        hot_stocks = sorted(hot_stocks, key=lambda x: x["total_chip"], reverse=True)[:4]
        return hot_stocks
    except Exception as e:
        print(f"⚠️ 抓取 TWSE 資料失敗：{e}")
        return []

def fetch_stock_news(stock_name: str) -> str:
    try:
        rss_url = f"https://news.google.com/rss/search?q={stock_name}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        news_titles = [f"- {entry.title}" for entry in feed.entries[:3]]
        return "\n".join(news_titles) if news_titles else "暫無相關即時新聞"
    except Exception:
        return "新聞抓取失敗"

def generate_stock_report(hot_stocks):
    if not GEMINI_API_KEY:
        raise ValueError("❌ 錯誤：找不到 GEMINI_API_KEY！")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    
    context_text = ""
    for stock in hot_stocks:
        news = fetch_stock_news(stock['name'])
        context_text += f"""
【股票名稱】: {stock['name']} ({stock['code']})
【籌碼數據】: 外資買超 {stock['foreign']} 張 | 投信買超 {stock['trust']} 張
【相關熱門新聞】:
{news}
----------------------------------------
"""

    prompt = f"""
你是一位專業的台股籌碼分析師。今天是 {today_str}。
請根據以下提供的「熱門籌碼股」數據與相關新聞，撰寫一份簡明扼要的盤後 Telegram 觀察推播報告。

【排版要求】
1. 開頭加上標題：「📊 【今日盤後熱門籌碼與新聞焦點】 ({today_str})」
2. 逐一列出各檔股票的籌碼概況與 1~2 句核心新聞重點。
3. 結尾加上一句警語。
4. 使用適當 Emoji，保持簡潔。

【資料庫】
{context_text}
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text

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
    hot_stocks = fetch_twse_hot_stocks()
    if not hot_stocks:
        today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        send_telegram_message(f"📊 【今日盤後熱門籌碼】 ({today_str})\n\n⚠️ 今日無符合條件之標的或逢休市日。")
        return
    report = generate_stock_report(hot_stocks)
    send_telegram_message(report)

if __name__ == "__main__":
    main()