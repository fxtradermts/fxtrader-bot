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

BOT_CONFIG = load_telegram_config()
BOT_TOKEN = BOT_CONFIG.get("bot_token")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://fxtrader-bot.onrender.com")

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
        USER_STATE[chat_id] = {"symbol": "US100", "category": "technical", "step": "symbols"}

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

# HTTP Handler with Webhook & Health check
class CloudBotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"FX Trader MTS Bot is Running 24/7 on Cloud!")

    def do_POST(self):
        # Webhook handler
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            cfg = load_telegram_config()
            token = cfg.get("bot_token")
            # Handle update in worker thread
            threading.Thread(target=handle_update, args=(token, update), daemon=True).start()
        except Exception as ex:
            print(f"[Webhook Error] {ex}")

    def log_message(self, format, *args):
        pass

def keep_alive_pinger():
    """Pings the Render app every 9 minutes so it NEVER sleeps on the free tier."""
    time.sleep(30)
    url = f"{RENDER_URL}/"
    while True:
        try:
            r = requests.get(url, timeout=15)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Keep-alive self-ping: {r.status_code}")
        except Exception as e:
            print(f"[Keep-alive ping notice] {e}")
        time.sleep(540) # 9 minutes

def start_cloud_server():
    port = int(os.environ.get("PORT", 10000))
    
    # 1. Start Keep-alive pinger thread
    threading.Thread(target=keep_alive_pinger, daemon=True).start()
    
    # 2. Register Webhook with Telegram
    cfg = load_telegram_config()
    token = cfg.get("bot_token")
    if token:
        webhook_url = f"{RENDER_URL}/webhook"
        try:
            set_res = requests.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": webhook_url, "drop_pending_updates": False},
                timeout=15
            ).json()
            print(f"Telegram Webhook Registration: {set_res}")
        except Exception as e:
            print(f"Webhook setup notice: {e}")
            
    # 3. Start HTTP Server (Blocking)
    print("=" * 60)
    print(f"FX Trader MTS Cloud Server Running on port {port}!")
    print(f"Webhook Endpoint: {RENDER_URL}/webhook")
    print("=" * 60)
    server = HTTPServer(("0.0.0.0", port), CloudBotHandler)
    server.serve_forever()

if __name__ == "__main__":
    start_cloud_server()
