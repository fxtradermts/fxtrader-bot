import os
import sys
import time
import json
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from market_data_engine import fetch_market_data, SYMBOL_MAP
from news_fetcher import ASSET_FA_NAMES
from bias_synthesizer import (
    generate_technical_report,
    generate_fundamental_report
)
from telegram_sender import load_telegram_config

# Minimal Health Server for Render Free Web Service
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"FX Trader MTS Bot is Running 24/7 on Cloud!")

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"Render Cloud Health check listening on port {port}...")
        server.serve_forever()
    except Exception as e:
        print(f"Health server notice: {e}")

BUTTON_TO_SYMBOL = {
    "📊 نزدک (US100)": "US100",
    "🥇 انس طلا (Gold)": "GOLD",
    "📈 داوجونز (US30)": "US30",
    "📉 اس‌اندپی (US500)": "US500",
    "💶 یورو/دلار (EURUSD)": "EURUSD",
    "💷 پوند/دلار (GBPUSD)": "GBPUSD",
    "⚡ بیت‌کوین (BTCUSD)": "BTCUSD"
}

USER_STATE = {}

def get_symbols_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 نزدک (US100)"}, {"text": "🥇 انس طلا (Gold)"}],
            [{"text": "📈 داوجونز (US30)"}, {"text": "📉 اس‌اندپی (US500)"}],
            [{"text": "💶 یورو/دلار (EURUSD)"}, {"text": "💷 پوند/دلار (GBPUSD)"}],
            [{"text": "⚡ بیت‌کوین (BTCUSD)"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }

def get_category_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 تحلیل تکنیکال چارت"}, {"text": "🌐 تحلیل فاندامنتال و اخبار"}],
            [{"text": "🔙 بازگشت به لیست نمادها"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }

def get_horizon_keyboard():
    return {
        "keyboard": [
            [{"text": "📅 تحلیل روزانه"}, {"text": "📆 تحلیل هفتگی"}],
            [{"text": "🔙 مرحله قبل"}, {"text": "🔙 لیست نمادها"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }

def send_telegram_msg(token, chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=25)
        return r.json()
    except Exception as e:
        print(f"[Error sending msg] {e}")
        return None

def handle_update(token, update):
    message = update.get("message")
    if not message:
        return
    
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    user_name = message.get("from", {}).get("first_name", "کاربر")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received '{text}' from {user_name} ({chat_id})")
    
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {"symbol": "US100", "category": "tech", "step": "symbols"}

    # 1. Reset / Start / Symbols Menu
    if text in ["/start", "/menu", "🔙 بازگشت به لیست نمادها", "🔙 لیست نمادها"]:
        USER_STATE[chat_id]["step"] = "symbols"
        welcome = (
            f"سلام {user_name} عزیز! به ربات تحلیلی FX Trader MTS خوش آمدید. 💎\n\n"
            "مستقل از متاتریدر و متصل به دیتای زنده وب و تقویم فارکس فکتوری (به وقت محلی رم).\n\n"
            "👇 لطفاً نماد مورد نظر خود را انتخاب کنید:"
        )
        send_telegram_msg(token, chat_id, welcome, reply_markup=get_symbols_keyboard())
        return

    # 2. Check if a symbol button was clicked
    matched_sym = None
    for btn, s in BUTTON_TO_SYMBOL.items():
        if btn == text or s.lower() in text.lower():
            matched_sym = s
            break
            
    if matched_sym:
        USER_STATE[chat_id]["symbol"] = matched_sym
        USER_STATE[chat_id]["step"] = "category"
        fa_name = ASSET_FA_NAMES.get(matched_sym, matched_sym)
        msg = (
            f"🎯 *نماد انتخابی:* {fa_name}\n\n"
            "کدام نوع تحلیل را می‌خواهید بررسی کنید؟"
        )
        send_telegram_msg(token, chat_id, msg, reply_markup=get_category_keyboard())
        return

    # 3. Check if Category was chosen (Technical vs Fundamental)
    current_sym = USER_STATE[chat_id].get("symbol", "US100")
    fa_name = ASSET_FA_NAMES.get(current_sym, current_sym)
    
    if text == "📊 تحلیل تکنیکال چارت":
        USER_STATE[chat_id]["category"] = "technical"
        USER_STATE[chat_id]["step"] = "horizon"
        msg = f"📊 *تحلیل تکنیکال چارت: {fa_name}*\n\nافق زمانی مورد نظرتان را انتخاب کنید:"
        send_telegram_msg(token, chat_id, msg, reply_markup=get_horizon_keyboard())
        return

    elif text == "🌐 تحلیل فاندامنتال و اخبار":
        USER_STATE[chat_id]["category"] = "fundamental"
        USER_STATE[chat_id]["step"] = "horizon"
        msg = f"🌐 *تحلیل فاندامنتال و اخبار قرمز: {fa_name}*\n(بر اساس ساعت محلی رم/ایتالیا)\n\nافق زمانی را انتخاب کنید:"
        send_telegram_msg(token, chat_id, msg, reply_markup=get_horizon_keyboard())
        return

    # 4. Check Back button to previous step
    if text == "🔙 مرحله قبل":
        USER_STATE[chat_id]["step"] = "category"
        msg = f"🎯 *نماد انتخابی:* {fa_name}\n\nنوع تحلیل را انتخاب کنید:"
        send_telegram_msg(token, chat_id, msg, reply_markup=get_category_keyboard())
        return

    # 5. Check Horizon selection (Daily vs Weekly)
    if text in ["📅 تحلیل روزانه", "📆 تحلیل هفتگی"]:
        horizon = "daily" if text == "📅 تحلیل روزانه" else "weekly"
        cat = USER_STATE[chat_id].get("category", "technical")
        
        horizon_fa = "روزانه" if horizon == "daily" else "هفتگی"
        cat_fa = "تکنیکال" if cat == "technical" else "فاندامنتال"
        
        send_telegram_msg(token, chat_id, f"⏳ در حال واکشی و آماده‌سازی تحلیل {cat_fa} {horizon_fa} برای *{fa_name}*...")
        
        try:
            if cat == "technical":
                metrics = fetch_market_data(current_sym, horizon=horizon)
                report = generate_technical_report(metrics, horizon=horizon)
            else:
                report = generate_fundamental_report(current_sym, horizon=horizon)
                
            send_telegram_msg(token, chat_id, report, reply_markup=get_horizon_keyboard())
        except Exception as e:
            send_telegram_msg(token, chat_id, f"❌ خطا در پردازش اطلاعات:\n`{str(e)}`", reply_markup=get_horizon_keyboard())
        return

    # Fallback
    fallback = "لطفاً یکی از گزینه‌های منو را انتخاب نمایید 👇"
    send_telegram_msg(token, chat_id, fallback, reply_markup=get_symbols_keyboard())

def run_bot_listener():
    # Start health server thread for Render Web Service
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    
    cfg = load_telegram_config()
    token = cfg.get("bot_token")
    if not token:
        print("Bot token not found in config!")
        return

    print("=" * 60)
    print("FX Trader MTS Bot Server Running (Ready for Cloud & Local)!")
    print("Supports: Technical/Fundamental x Daily/Weekly x Rome Time")
    print("=" * 60)

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": offset, "timeout": 25}
            res = requests.get(url, params=params, timeout=30)
            
            if res.status_code == 200:
                data = res.json()
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    handle_update(token, upd)
            time.sleep(1)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    run_bot_listener()
