from datetime import datetime
from news_fetcher import get_red_news_for_asset, get_event_direction_projection

def generate_technical_report(metrics, horizon="daily"):
    sym = metrics.get('sym_key', 'US100')
    fa_name = metrics.get('fa_name', sym)
    price = metrics.get('price', 0.0)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if horizon == "daily":
        pdh = metrics.get('pdh', '-')
        pdl = metrics.get('pdl', '-')
        today_h = metrics.get('today_high', '-')
        today_l = metrics.get('today_low', '-')
        trend = metrics.get('trend', '-')
        adr = metrics.get('adr_5d', '-')
        adr_pct = metrics.get('adr_used_pct', 0)
        lon_h = metrics.get('london_high', '-')
        lon_l = metrics.get('london_low', '-')
        asia_h = metrics.get('asian_high', '-')
        asia_l = metrics.get('asian_low', '-')
        eq = metrics.get('m15_equilibrium', '-')
        zone = metrics.get('m15_zone', '-')
        atr_1m = metrics.get('m1_atr', 0.0)
        mom = metrics.get('m1_momentum', '-')
        
        # Bias projection
        if "صعودی" in trend and "DISCOUNT" in zone:
            proj = "🎯 **پیش‌بینی تکنیکال روز:** اولویت با موج صعودی به سمت استخر نقدینگی سقف روز قبل (PDH)؛ واکنش مثبت در ناحیه دیسکانت تعادل."
        elif "نزولی" in trend and "PREMIUM" in zone:
            proj = "🎯 **پیش‌بینی تکنیکال روز:** مستعد اصلاح نزولی به سمت کف روز قبل (PDL) پس از هانت سقف سشن‌ها در محدوده پریمیوم."
        else:
            proj = "🎯 **پیش‌بینی تکنیکال روز:** بازار در فاز تعادل و تکمیل نوسان روزانه؛ زیر نظر داشتن هانت سقف/کف سشن لندن برای جهت‌گیری حرکتی."

        return f"""📊 *تحلیل تکنیکال روزانه: {fa_name}*
🏷 نماد: `{sym}` | ⏰ بروزرسانی: `{now_str}`

━━━━━━━━━━━━━━━━━━━
📍 *سطوح کلیدی و استخرهای نقدینگی روزانه:*
• قیمت لحظه‌ای: `{price}`
• سقف روز قبل (PDH): `{pdh}`
• کف روز قبل (PDL): `{pdl}`
• سقف / کف سشن لندن: `{lon_h}` / `{lon_l}`
• سقف / کف سشن آسیا: `{asia_h}` / `{asia_l}`
• میانه محدوده (Equilibrium M15): `{eq}` ⬅️ *{zone}*

🌊 *نوسان‌پذیری و مومنتوم دی‌تریدینگ:*
• نوسان انجام‌شده امروز: `{metrics.get('today_range')}` (`{adr_pct}%` از ADR `{adr}` پوینت)
• میانگین نوسان هر کندل ۱ دقیقه (ATR): `{atr_1m}`
• مومنتوم لحظه‌ای تایم ۱ دقیقه: *{mom}*

━━━━━━━━━━━━━━━━━━━
{proj}
"""

    else: # Weekly technical
        pwh = metrics.get('pwh', '-')
        pwl = metrics.get('pwl', '-')
        pwc = metrics.get('pwc', '-')
        w_open = metrics.get('week_open', '-')
        w_high = metrics.get('week_high', '-')
        w_low = metrics.get('week_low', '-')
        w_range = metrics.get('week_range', '-')
        awr = metrics.get('awr_4w', '-')
        awr_pct = metrics.get('awr_used_pct', 0)
        w_trend = metrics.get('weekly_trend', '-')
        w_eq = metrics.get('weekly_equilibrium', '-')
        
        # Weekly projection
        if price > w_eq:
            w_proj = "🎯 **پیش‌بینی ساختار هفتگی:** تثبیت قیمت در نیمه بالایی دامنه هفتگی؛ هدف نقدینگی بعدی سقف هفته گذشته (PWH) و انبساط صعودی است."
        else:
            w_proj = "🎯 **پیش‌بینی ساختار هفتگی:** فشار قیمت در نیمه پایینی دامنه هفتگی؛ پتانسیل حمله به کف هفته گذشته (PWL) و تست حمایت‌های ماکرو."

        return f"""📆 *تحلیل تکنیکال هفتگی: {fa_name}*
🏷 نماد: `{sym}` | ⏰ بروزرسانی: `{now_str}`

━━━━━━━━━━━━━━━━━━━
📐 *ساختار کندل و دامنه هفتگی (Weekly Range):*
• قیمت فعلی: `{price}`
• وضعیت روند ماکرو: {w_trend}
• سقف هفته گذشته (PWH): `{pwh}`
• کف هفته گذشته (PWL): `{pwl}`
• کلوز هفته گذشته (PWC): `{pwc}`
• بازگشایی هفته جاری: `{w_open}`
• سقف و کف هفته جاری تا الان: `{w_high}` / `{w_low}`
• نوسان این هفته: `{w_range}` (`{awr_pct}%` از میانگین ۴ هفته اخیر `{awr}`)
• سطح میانه هفته (Weekly Equilibrium): `{w_eq}`

━━━━━━━━━━━━━━━━━━━
{w_proj}
"""

def generate_fundamental_report(sym_key, horizon="daily"):
    intel = get_red_news_for_asset(sym_key, horizon)
    fa_name = intel.get("fa_name", sym_key)
    clean_sym = intel.get("sym_key", sym_key)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if horizon == "daily":
        events = intel.get("events", [])
        
        events_text = ""
        if events:
            for ev in events:
                proj = get_event_direction_projection(ev['title'], ev['currency'], clean_sym)
                events_text += (
                    f"🔴 *{ev['title']}* [{ev['currency']}]\n"
                    f"⏰ ساعت انتشار: `{ev['time_rome']}`\n"
                    f"📊 پیش‌بینی: `{ev['forecast']}` | قبلی: `{ev['previous']}`\n"
                    f"{proj}\n"
                    "───────────────────\n"
                )
        else:
            events_text = "✅ امروز خبر قرمز (Red Folder) مستقیمی برای این نماد در تقویم وجود ندارد؛ بازار از جریان سفارشات تکنیکال تبعیت می‌کند.\n"

        return f"""🌐 *تحلیل فاندامنتال و اخبار قرمز روز: {fa_name}*
⏰ زمان: `{now_str}` (ساعت‌ها بر اساس وقت محلی رم/ایتالیا)
🚨 *فقط رویدادهای بحرانی و پرنوسان (Red Folder)*

━━━━━━━━━━━━━━━━━━━
{events_text}
💡 *جمع‌بندی روزانه:* در ساعات اعلام خبر ردفولدر، تغییرات ناگهانی در بازدهی دلار جهت نماد را مشخص خواهد کرد؛ پس از فروکش کردن هیجان اولیه با موج اصلی همراه شوید.
"""

    else: # Weekly Fundamental
        this_w = intel.get("this_week", [])
        next_w = intel.get("next_week", [])
        
        # 1. Past/Current week review
        this_w_text = ""
        if this_w:
            for ev in this_w:
                proj = get_event_direction_projection(ev['title'], ev['currency'], clean_sym)
                this_w_text += (
                    f"• 🔴 *{ev['date']} | {ev['time_rome']}* ⬅️ *{ev['title']}* [{ev['currency']}]\n"
                    f"  پیش‌بینی: `{ev['forecast']}` | قبلی: `{ev['previous']}`\n"
                    f"  {proj}\n"
                )
        else:
            this_w_text = "• رویداد قرمز شاخصی در این هفته ثبت نشده است.\n"

        # 2. Upcoming next week preview
        next_w_text = ""
        if next_w:
            for ev in next_w:
                next_w_text += (
                    f"• ⚠️ *{ev['date']} | {ev['time_rome']}* ⬅️ *{ev['title']}* [{ev['currency']}]\n"
                    f"  پیش‌بینی اولیه: `{ev['forecast']}` | قبلی: `{ev['previous']}`\n"
                )
        else:
            next_w_text = "• تقویم هفته آینده به زودی نهایی و به‌روزرسانی می‌شود.\n"

        return f"""📆 *تحلیل فاندامنتال جامع هفتگی: {fa_name}*
⏰ زمان: `{now_str}` (تمام ساعت‌ها به وقت محلی رم/ایتالیا)
🚨 *بررسی زنجیره اخبار قرمز هفته جاری و پیش‌رو در هفته بعد*

━━━━━━━━━━━━━━━━━━━
📅 *۱. اخبار مهم قرمز هفته جاری و اثرات روزبه‌روز:*
{this_w_text}
━━━━━━━━━━━━━━━━━━━
🔮 *۲. کاتالیزورهای مهم قرمز هفته آینده:*
{next_w_text}
━━━━━━━━━━━━━━━━━━━
🎯 *جمع‌بندی انتظارات و پیش‌بینی هفتگی:*
هنگام بسته شدن و بازگشایی هفتگی، هضم تجمعی اخبار هفته (به‌ویژه داده‌های تورم و نرخ بهره) بایاس نماد {fa_name} را تعیین می‌کند. 
در صورت عدم شگفتی افزایشی در تورم، گرایش کلان به سمت ریسک‌پذیری و رشد ارزش دارایی ادامه خواهد داشت.
"""
