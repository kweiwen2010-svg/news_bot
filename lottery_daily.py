import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
TW_TZ = ZoneInfo("Asia/Taipei")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# 抓取台彩最新開獎號碼 (威力彩、大樂透、今彩539)
# ==========================================
def fetch_lottery_results() -> str:
    print("🎰 1/2 正在抓取台灣彩券最新開獎數據...")
    try:
        url = "https://www.taiwanlottery.com.tw/index_new.aspx"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []

        # 1. 威力彩 (Super Lotto)
        super_box = soup.find('div', class_='contents_box02')
        if super_box:
            title = "🎯 威力彩"
            draw_period = super_box.find('span', class_='font_black15')
            period_str = draw_period.text.strip() if draw_period else ""
            
            # 開出順序與大小順序號碼
            balls = [b.text.strip() for b in super_box.find_all('div', class_=re.compile(r'ball_green|ball_yellow'))]
            if len(balls) >= 6:
                seq_nums = " ".join(balls[:6])
                second_num = super_box.find('div', class_='ball_red')
                second_str = second_num.text.strip() if second_num else "-"
                results.append(f"{title} ({period_str})\n▸ 第一區：{seq_nums}\n▸ 第二區：[{second_str}]")

        # 2. 大樂透 (Lotto 649)
        lotto_box = soup.find('div', class_='contents_box04')
        if lotto_box:
            title = "🎰 大樂透"
            draw_period = lotto_box.find('span', class_='font_black15')
            period_str = draw_period.text.strip() if draw_period else ""
            
            balls = [b.text.strip() for b in lotto_box.find_all('div', class_=re.compile(r'ball_green|ball_yellow'))]
            special_num = lotto_box.find('div', class_='ball_red')
            special_str = special_num.text.strip() if special_num else "-"
            if len(balls) >= 6:
                seq_nums = " ".join(balls[:6])
                results.append(f"{title} ({period_str})\n▸ 開出號碼：{seq_nums}\n▸ 特別號：[{special_str}]")

        # 3. 今彩539 (Daily 539)
        d539_box = soup.find('div', class_='contents_box03')
        if d539_box:
            title = "🎱 今彩539"
            draw_period = d539_box.find('span', class_='font_black15')
            period_str = draw_period.text.strip() if draw_period else ""
            
            balls = [b.text.strip() for b in d539_box.find_all('div', class_=re.compile(r'ball_green|ball_yellow'))]
            if len(balls) >= 5:
                seq_nums = " ".join(balls[:5])
                results.append(f"{title} ({period_str})\n▸ 開出號碼：{seq_nums}")

        today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        header = f"🎫 【台灣彩券今晚最新開獎結果】({today_str})\n" + "─" * 28 + "\n"
        footer = "\n" + "─" * 28 + "\n祝您幸運中大獎！🎉"
        
        return header + "\n\n".join(results) + footer if results else "今日無開獎資料或抓取失敗。"

    except Exception as e:
        print(f"⚠️ 彩券資料抓取失敗：{e}")
        return "⚠️ 今日彩券開獎號碼暫時無法取得。"

# ==========================================
# Telegram 發送
# ==========================================
def send_telegram_message(text: str):
    print("📲 2/2 發送彩券開獎至 Telegram...")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text
    }
    
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code == 200:
        print("✅ 夜間彩券開獎推播成功！")
    else:
        print(f"❌ 推播失敗，狀態碼：{resp.status_code}")

def main():
    print("🚀 開始執行夜間彩券開獎推播...")
    report = fetch_lottery_results()
    send_telegram_message(report)

if __name__ == "__main__":
    main()