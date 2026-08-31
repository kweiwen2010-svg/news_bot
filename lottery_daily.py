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

def clean_text(text: str) -> str:
    """清理多餘換行與連續空白，確保號碼單行橫向排列"""
    return " ".join(text.split())

def fetch_lottery_results() -> str:
    print("🎰 正在抓取最新彩券開獎數據...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    url = "https://lotto.auzo.com.tw/"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 淨化整頁文字，將換行符號全部轉為單一空格
        raw_text = clean_text(soup.get_text())

        today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        report = [f"🎫 **【台灣彩券最新開獎結果】({today_str})**", "─" * 28]

        # 1. 大樂透
        lotto_match = re.search(r'大樂透.*?(\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}).*?特別號[^\d]*(\d{2})', raw_text)
        if lotto_match:
            nums = clean_text(lotto_match.group(1))
            special = lotto_match.group(2)
            report.append(f"🎰 **大樂透**\n▸ 開出號碼：{nums}\n▸ 特別號：[{special}]\n")

        # 2. 今彩539
        c539_match = re.search(r'今彩539.*?(\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2})', raw_text)
        if c539_match:
            nums = clean_text(c539_match.group(1))
            report.append(f"🎱 **今彩539**\n▸ 開出號碼：{nums}\n")

        # 3. 威力彩
        super_match = re.search(r'威力彩.*?(\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}).*?第二區[^\d]*(\d{2})', raw_text)
        if super_match:
            nums = clean_text(super_match.group(1))
            zone2 = super_match.group(2)
            report.append(f"🎯 **威力彩**\n▸ 第一區：{nums}\n▸ 第二區：[{zone2}]\n")

        if len(report) > 2:
            report.append("─" * 28)
            report.append("祝您幸運中大獎！🎉")
            return "\n".join(report)

        return f"🎫 **【台灣彩券開獎通知】({today_str})**\n\n今日號碼預計於今晚 20:30~21:00 開出！"

    except Exception as e:
        print(f"⚠️ 彩券抓取錯誤：{e}")
        return "⚠️ 彩券數據更新中，請於今晚開獎後再次查看。"

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
    report = fetch_lottery_results()
    send_telegram_message(report)

if __name__ == "__main__":
    main()