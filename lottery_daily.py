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

def fetch_lottery_results() -> str:
    print("🎰 1/2 正在抓取最新彩券開獎數據...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    url = "https://lotto.auzo.com.tw/"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        today_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        report = [f"🎫 **【台灣彩券最新開獎結果】({today_str})**", "─" * 28]

        # 建立去重集合，每種彩券僅擷取最前面最新的一組
        found_games = set()

        tables = soup.find_all('table')
        for table in tables:
            text = table.text
            
            # 威力彩
            if "威力彩" in text and "第一區" in text and "super_lotto" not in found_games:
                nums = re.findall(r'\b\d{2}\b', text)
                if len(nums) >= 7:
                    zone1 = " ".join(nums[:6])
                    zone2 = nums[6]
                    report.append(f"🎯 **威力彩**\n▸ 第一區：{zone1}\n▸ 第二區：[{zone2}]\n")
                    found_games.add("super_lotto")

            # 大樂透
            elif "大樂透" in text and "特別號" in text and "lotto649" not in found_games:
                nums = re.findall(r'\b\d{2}\b', text)
                if len(nums) >= 7:
                    zone1 = " ".join(nums[:6])
                    special = nums[6]
                    report.append(f"🎰 **大樂透**\n▸ 開出號碼：{zone1}\n▸ 特別號：[{special}]\n")
                    found_games.add("lotto649")

            # 今彩539
            elif "今彩539" in text and "daily539" not in found_games:
                nums = re.findall(r'\b\d{2}\b', text)
                if len(nums) >= 5:
                    zone1 = " ".join(nums[:5])
                    report.append(f"🎱 **今彩539**\n▸ 開出號碼：{zone1}\n")
                    found_games.add("daily539")

        if len(report) > 2:
            report.append("─" * 28)
            report.append("祝您幸運中大獎！🎉")
            return "\n".join(report)

        return f"🎫 **【台灣彩券開獎通知】({today_str})**\n\n今日號碼預計於今晚 20:30~21:00 開出！"

    except Exception as e:
        print(f"⚠️ 彩券抓取錯誤：{e}")
        return "⚠️ 彩券數據更新中，請於今晚開獎後再次查看。"

def send_telegram_message(text: str):
    print("📲 2/2 發送彩券開獎至 Telegram...")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ 錯誤：Telegram 設定缺失！")
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code != 200:
        payload.pop('parse_mode')
        requests.post(url, data=payload, timeout=15)

def main():
    report = fetch_lottery_results()
    send_telegram_message(report)

if __name__ == "__main__":
    main()