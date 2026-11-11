import os
import json
import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "telegram_config.json")

def load_telegram_config():
    env_token = os.environ.get("BOT_TOKEN")
    env_chat = os.environ.get("CHAT_ID")
    if env_token:
        return {"bot_token": env_token.strip(), "chat_id": (env_chat or "201441653").strip()}
        
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {
            "bot_token": "",
            "chat_id": ""
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=4)
        return default_cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"bot_token": "", "chat_id": ""}

def save_telegram_config(bot_token, chat_id):
    cfg = {"bot_token": bot_token.strip(), "chat_id": str(chat_id).strip()}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
    print("Telegram config saved successfully!")

def send_telegram_message(message_text, bot_token=None, chat_id=None):
    """Send text message to Telegram chat via Bot API."""
    cfg = load_telegram_config()
    token = bot_token or cfg.get("bot_token")
    cid = chat_id or cfg.get("chat_id")
    
    if not token or not cid:
        print("[Telegram] Bot Token or Chat ID not configured yet.")
        return False, "Bot Token or Chat ID is missing."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        if res_json.get("ok"):
            print("[Telegram] Message sent successfully to Telegram!")
            return True, "Message sent successfully!"
        else:
            err = res_json.get("description", "Unknown error")
            print(f"[Telegram Error] {err}")
            return False, err
    except Exception as e:
        print(f"[Telegram Network Error] {e}")
        return False, str(e)

if __name__ == "__main__":
    cfg = load_telegram_config()
    print("Current Telegram Config:", cfg)
