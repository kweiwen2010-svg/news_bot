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

# ==========================================
# 1. 抓取證交所籌碼與熱門股 (TWSE API)
# ==========================================
def fetch_twse_hot_stocks():
    print("📊 1/4 正在抓取證交所三大法人與成交量資料...")
    try:
        # 三大法人買賣超 (T86)
        t86_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        t86_resp = requests.get(t86_url, timeout=15)
        t86_data = t86_resp.json() if t86_resp.status_code == 200 else []

        hot_stocks = []
        for item in t86_data:
            code = item.get("Code", "")
            name = item.get("Name", "").strip()
            
            # 過濾權證與 ETF (只看普通股 4 位數代碼)
            if len(code) != 4 or not code.isdigit():
                continue
                
            try:
                foreign_buy = int(item.get("ForeignInvestorsDifference", "0").replace(",", ""))
                trust_buy = int(item.get("InvestmentTrustDifference", "0").replace(",", ""))
                
                # 條件：外資與投信同步淨買超 (>0)
                if foreign_buy > 0 and trust_buy > 0:
                    hot_stocks.append({
                        "code": code,
                        "name": name,
                        "foreign": foreign_buy // 1000,  # 換算成張數
                        "trust": trust_buy // 1000,
                        "total_chip": (foreign_buy + trust_buy) // 1000
                    })
            except ValueError:
                continue

        # 依法人合計買超張數排序，取前 4 名
        hot_stocks = sorted(hot_stocks, key=lambda x: x["total_chip"], reverse=True)[:4]
        return hot_stocks
    except Exception as e:
        print(f"⚠️ 抓取 TWSE 資料失敗：{e}")
        return []

# ==========================================
# 2. 抓取指定個股的最新新聞
# ==========================================
def fetch_stock_news(stock_name: str) -> str:
    print(f"📰 正在搜尋 [{stock_name}] 的相關新聞...")
    try:
        rss_url = f"https://news.google.com/rss/search?q={stock_name}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        
        news_titles = []
        for entry in feed.entries[:3]:
            news_titles.append(f"- {entry.title}")
            
        return "\n".join(news_titles) if news_titles else "暫無相關即時新聞"
    except Exception as e:
        return "新聞抓取失敗"

# ==========================================
# 3. Gemini 整合籌碼與新聞分析
# ==========================================
def generate_stock_report(hot_stocks):
    print("🤖 3/4 正在呼叫 Gemini 分析熱門股與新聞...")
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
2. 逐一列出各檔股票：
   - 標頭顯示：股票名稱 (代號)
   - 籌碼概況：外資與投信買超張數
   - 核心新聞重點：綜合新聞內容，用 1~2 句話說明該股今日熱門或發燒的原因。
3. 結尾加上一句警語（如：投資有風險，數據僅供參考）。
4. 請使用適當的 Emoji 增加易讀性，保持排版簡潔，適合手機快速瀏覽。

【資料庫】
{context_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text

# ==========================================
# 4. Telegram 文字推播
# ==========================================
def send_telegram_message(text: str):
    print("📲 4/4 發送盤後報告至 Telegram...")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code == 200:
        print("✅ 盤後股票推播發送成功！")
    else:
        # 若 Markdown 解析失敗，降級為純文字發送
        payload.pop('parse_mode')
        requests.post(url, data=payload, timeout=15)
        print("✅ 盤後股票推播（純文字模式）發送成功！")

def main():
    print("🚀 開始執行盤後股票籌碼與新聞推播...")
    hot_stocks = fetch_twse_hot_stocks()
    
    if not hot_stocks:
        today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        empty_msg = f"📊 【今日盤後熱門籌碼與新聞焦點】 ({today_str})\n\n⚠️ 今日無符合雙法人（外資+投信）同步買超條件之熱門標的，或逢台股休市日。"
        send_telegram_message(empty_msg)
        return
        
    report = generate_stock_report(hot_stocks)
    send_telegram_message(report)

if __name__ == "__main__":
    main()