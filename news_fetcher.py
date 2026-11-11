import os
import time
import json
from datetime import datetime
from curl_cffi import requests
from bs4 import BeautifulSoup

CACHE_FILE = os.path.join(os.path.dirname(__file__), "ff_red_news_cache.json")
CACHE_DURATION_SEC = 1800  # 30 mins

# Asset to relevant currency
ASSET_CURRENCY = {
    "US100": ["USD"],
    "US100.cash": ["USD"],
    "GOLD": ["USD"],
    "XAUUSD": ["USD"],
    "US30": ["USD"],
    "US30.cash": ["USD"],
    "US500": ["USD"],
    "US500.cash": ["USD"],
    "EURUSD": ["USD", "EUR"],
    "GBPUSD": ["USD", "GBP"],
    "BTCUSD": ["USD"]
}

ASSET_FA_NAMES = {
    "US100": "شاخص نزدک ۱۰۰ (Nasdaq)",
    "US100.cash": "شاخص نزدک ۱۰۰ (Nasdaq)",
    "GOLD": "انس طلا (Gold)",
    "XAUUSD": "انس طلا (Gold)",
    "US30": "شاخص داوجونز ۳۰ (Dow Jones)",
    "US30.cash": "شاخص داوجونز ۳۰ (Dow Jones)",
    "US500": "شاخص اس‌اندپی ۵۰۰ (S&P 500)",
    "US500.cash": "شاخص اس‌اندپی ۵۰۰ (S&P 500)",
    "EURUSD": "یورو به دلار (EUR/USD)",
    "GBPUSD": "پوند به دلار (GBP/USD)",
    "BTCUSD": "بیت‌کوین (Bitcoin)"
}

# Directional impact logic generator
def get_event_direction_projection(event_title, currency, asset_key):
    asset_base = asset_key.upper().replace(".CASH", "")
    t = event_title.upper()
    
    if "CPI" in t or "INFLATION" in t:
        if asset_base in ["US100", "US30", "US500", "GOLD", "BTCUSD", "EURUSD", "GBPUSD"]:
            return (
                "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
                "• **اگر داده بالاتر از انتظار بیاید:** بازدهی دلار جهش می‌کند ⬅️ **جهت نزولی شدید (Sell-off)** برای " + asset_base + ".\n"
                "• **اگر داده پایین‌تر یا مطابق انتظار بیاید:** امید به کاهش بهره قوت می‌گیرد ⬅️ **جهت صعودی قدرتمند (Bullish Rally)** برای " + asset_base + "."
            )
    elif "FOMC" in t or "FED" in t or "POWELL" in t:
        return (
            "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
            "• **لحن هاوکیش (نگه‌داشتن نرخ بالا):** تقویت دلار ⬅️ **فشار فروش و افت** در " + asset_base + ".\n"
            "• **لحن داویش (سیگنال کاهش نرخ بهره):** ⬅️ **جهش صعودی پرسرعت** در " + asset_base + "."
        )
    elif "UNEMPLOYMENT" in t or "JOBLESS" in t or "CLAIMS" in t:
        return (
            "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
            "• **افزایش مطالبات بیکاری:** خنک شدن اقتصاد و ضعف دلار ⬅️ محرک **صعودی کوتاه‌مدت** برای " + asset_base + ".\n"
            "• **کاهش مطالبات (بازار کار داغ):** ⬅️ **اصلاح نزولی** در نماد."
        )
    elif "PPI" in t:
        return (
            "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
            "• PPI به عنوان پیش‌درآمد تورم مصرف‌کننده عمل می‌کند؛ عدد بالاتر = **فشار نزولی**، عدد پایین‌تر = **رشد قیمتی** در " + asset_base + "."
        )
    elif "GDP" in t:
        if currency in ["GBP", "EUR"]:
            return (
                "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
                "• رشد بالاتر GDP ⬅️ تقویت مستقیم " + currency + " و **جهت صعودی** در جفت‌ارز.\n"
                "• افت GDP یا رکود ⬅️ **ریزش قیمتی** در جفت‌ارز."
            )
        else:
            return "📌 *تحلیل اثر:* رشد قوی اقتصادی آمریکا به نفع سهام سنتی و در کوتاه‌مدت باعث استحکام دلار می‌شود."
    elif "RETAIL SALES" in t:
        return (
            "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
            "• خرده‌فروشی قوی = پایداری اقتصاد مصرف‌کننده آمریکا؛ واکنش اولیه معمولاً صعودی برای سهام و تقویت دلار است."
        )
    else:
        return (
            "📌 *تحلیل اثر و پیش‌بینی جهت:*\n"
            "• این خبر جزو رویدادهای ردفولدر با پتانسیل نوسان بالا است. قبل از انتشار از ورود در تایم‌های پایین بپرهیزید و جهت نهایی را پس از اولین شکست ساختار (BOS) دنبال کنید."
        )

def scrape_forex_factory_red_news():
    """Scrapes Forex Factory calendar for this week and next week, returning ONLY RED / HIGH-IMPACT events."""
    now = time.time()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if now - data.get("timestamp", 0) < CACHE_DURATION_SEC:
                    return data.get("events", [])
        except Exception:
            pass

    all_red_events = []
    urls = [
        ("this_week", "https://www.forexfactory.com/calendar?week=this"),
        ("next_week", "https://www.forexfactory.com/calendar?week=next")
    ]
    
    for period_tag, url in urls:
        try:
            r = requests.get(url, impersonate="chrome", timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.find_all("tr", class_="calendar__row")
                current_date = ""
                for row in rows:
                    d_td = row.find("td", class_="calendar__date")
                    if d_td and d_td.text.strip():
                        current_date = d_td.text.strip()
                    
                    curr_td = row.find("td", class_="calendar__currency")
                    impact_td = row.find("td", class_="calendar__impact")
                    event_td = row.find("td", class_="calendar__event")
                    time_td = row.find("td", class_="calendar__time")
                    fc_td = row.find("td", class_="calendar__forecast")
                    prev_td = row.find("td", class_="calendar__previous")
                    
                    if curr_td and impact_td and event_td:
                        span = impact_td.find("span")
                        classes = span["class"] if span and "class" in span.attrs else []
                        # STRICT RED / HIGH IMPACT ONLY
                        is_red = any("red" in cls or "high" in cls for cls in classes)
                        if is_red:
                            raw_time = time_td.text.strip() if time_td else ""
                            # Format time to 24h Rome format
                            rome_time = raw_time
                            if "pm" in raw_time.lower():
                                parts = raw_time.lower().replace("pm", "").strip().split(":")
                                h = int(parts[0])
                                m = parts[1] if len(parts) > 1 else "00"
                                if h < 12: h += 12
                                rome_time = f"{h}:{m}"
                            elif "am" in raw_time.lower():
                                parts = raw_time.lower().replace("am", "").strip().split(":")
                                h = int(parts[0])
                                m = parts[1] if len(parts) > 1 else "00"
                                if h == 12: h = 0
                                rome_time = f"{h:02d}:{m}"
                                
                            all_red_events.append({
                                "period": period_tag,
                                "date": current_date,
                                "time_rome": f"{rome_time} (به وقت رم)" if rome_time else "طول روز",
                                "currency": curr_td.text.strip(),
                                "title": event_td.text.strip(),
                                "forecast": fc_td.text.strip() if fc_td else "-",
                                "previous": prev_td.text.strip() if prev_td else "-"
                            })
        except Exception as e:
            print(f"Error scraping FF {period_tag}: {e}")

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now, "events": all_red_events}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return all_red_events

def get_red_news_for_asset(sym_key, horizon="daily"):
    """
    Returns filtered, pure red-folder economic intelligence tailored to the selected asset.
    horizon: 'daily' or 'weekly'
    """
    clean_sym = sym_key.upper().replace(".CASH", "")
    target_currencies = ASSET_CURRENCY.get(sym_key, ["USD"])
    fa_name = ASSET_FA_NAMES.get(sym_key, clean_sym)
    
    events = scrape_forex_factory_red_news()
    # Filter ONLY relevant currencies
    filtered = [e for e in events if e.get("currency") in target_currencies]
    
    if horizon == "daily":
        # Today's events (take first 3 events of this week)
        today_events = [e for e in filtered if e.get("period") == "this_week"][:3]
        return {
            "fa_name": fa_name,
            "sym_key": clean_sym,
            "horizon": "daily",
            "events": today_events
        }
    else: # weekly
        this_week_events = [e for e in filtered if e.get("period") == "this_week"]
        next_week_events = [e for e in filtered if e.get("period") == "next_week"]
        return {
            "fa_name": fa_name,
            "sym_key": clean_sym,
            "horizon": "weekly",
            "this_week": this_week_events,
            "next_week": next_week_events
        }

if __name__ == "__main__":
    w_intel = get_red_news_for_asset("US100", "weekly")
    print(f"Weekly Red events for US100: This Week: {len(w_intel['this_week'])}, Next Week: {len(w_intel['next_week'])}")
    for ev in w_intel['this_week'][:3]:
        print(ev['date'], ev['time_rome'], ev['title'])
