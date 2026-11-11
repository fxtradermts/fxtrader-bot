import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

SYMBOL_MAP = {
    "US100": {"ticker": "^NDX", "fa_name": "شاخص نزدک ۱۰۰ (Nasdaq)", "digits": 2},
    "US100.cash": {"ticker": "^NDX", "fa_name": "شاخص نزدک ۱۰۰ (Nasdaq)", "digits": 2},
    "GOLD": {"ticker": "GC=F", "fa_name": "انس طلا (Gold)", "digits": 2},
    "XAUUSD": {"ticker": "GC=F", "fa_name": "انس طلا (Gold)", "digits": 2},
    "US30": {"ticker": "^DJI", "fa_name": "شاخص داوجونز ۳۰ (Dow Jones)", "digits": 2},
    "US30.cash": {"ticker": "^DJI", "fa_name": "شاخص داوجونز ۳۰ (Dow Jones)", "digits": 2},
    "US500": {"ticker": "^GSPC", "fa_name": "شاخص اس‌اندپی ۵۰۰ (S&P 500)", "digits": 2},
    "US500.cash": {"ticker": "^GSPC", "fa_name": "شاخص اس‌اندپی ۵۰۰ (S&P 500)", "digits": 2},
    "EURUSD": {"ticker": "EURUSD=X", "fa_name": "یورو به دلار (EUR/USD)", "digits": 5},
    "GBPUSD": {"ticker": "GBPUSD=X", "fa_name": "پوند به دلار (GBP/USD)", "digits": 5},
    "BTCUSD": {"ticker": "BTC-USD", "fa_name": "بیت‌کوین (BTC/USD)", "digits": 2}
}

def calculate_atr(df, period=14):
    if df is None or len(df) < period + 1:
        return 0.0
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])

def fetch_market_data(sym_key, horizon="daily"):
    cfg = SYMBOL_MAP.get(sym_key, SYMBOL_MAP["US100"])
    ticker_str = cfg["ticker"]
    digits = cfg["digits"]
    fa_name = cfg["fa_name"]
    
    t = yf.Ticker(ticker_str)
    
    if horizon == "daily":
        df_d1 = t.history(period="10d", interval="1d")
        df_h1 = t.history(period="5d", interval="1h")
        df_m15 = t.history(period="2d", interval="15m")
        df_m1 = t.history(period="1d", interval="1m")
        
        live_price = float(df_m1['Close'].iloc[-1]) if not df_m1.empty else float(df_d1['Close'].iloc[-1])
        
        curr_d = df_d1.iloc[-1]
        prev_d = df_d1.iloc[-2]
        adr_5d = calculate_atr(df_d1, period=5)
        day_range = float(curr_d['High'] - curr_d['Low'])
        
        # Sessions
        london_high = round(float(df_h1['High'].iloc[-6:].max()), digits) if not df_h1.empty else "-"
        london_low = round(float(df_h1['Low'].iloc[-6:].min()), digits) if not df_h1.empty else "-"
        asian_high = round(float(df_h1['High'].iloc[-12:-6].max()), digits) if len(df_h1) >= 12 else "-"
        asian_low = round(float(df_h1['Low'].iloc[-12:-6].min()), digits) if len(df_h1) >= 12 else "-"
        
        # M15
        m15_high = float(df_m15['High'].iloc[-20:].max()) if not df_m15.empty else 0
        m15_low = float(df_m15['Low'].iloc[-20:].min()) if not df_m15.empty else 0
        eq_m15 = (m15_high + m15_low) / 2.0 if m15_high and m15_low else 0
        zone = "PREMIUM (بالای میانه)" if live_price > eq_m15 else "DISCOUNT (زیر میانه)"
        
        # M1
        m1_atr = calculate_atr(df_m1, period=14) if not df_m1.empty else 0.0
        m1_ema9 = float(df_m1['Close'].ewm(span=9).mean().iloc[-1]) if not df_m1.empty else 0
        m1_ema21 = float(df_m1['Close'].ewm(span=21).mean().iloc[-1]) if not df_m1.empty else 0
        momentum = "صعودی (EMA9 > EMA21)" if m1_ema9 > m1_ema21 else "نزولی (EMA9 < EMA21)"
        
        d1_bullish = curr_d['Close'] > curr_d['Open']
        
        return {
            "sym_key": sym_key,
            "fa_name": fa_name,
            "horizon": "daily",
            "price": round(live_price, digits),
            "digits": digits,
            "pdh": round(float(prev_d['High']), digits),
            "pdl": round(float(prev_d['Low']), digits),
            "pdc": round(float(prev_d['Close']), digits),
            "today_open": round(float(curr_d['Open']), digits),
            "today_high": round(float(curr_d['High']), digits),
            "today_low": round(float(curr_d['Low']), digits),
            "today_range": round(day_range, digits),
            "adr_5d": round(adr_5d, digits),
            "adr_used_pct": round((day_range / adr_5d * 100), 1) if adr_5d > 0 else 0,
            "trend": "🟢 صعودی (Bullish)" if d1_bullish else "🔴 نزولی (Bearish)",
            "london_high": london_high,
            "london_low": london_low,
            "asian_high": asian_high,
            "asian_low": asian_low,
            "m15_equilibrium": round(eq_m15, digits),
            "m15_zone": zone,
            "m1_atr": round(m1_atr, digits),
            "m1_momentum": momentum
        }
        
    else: # weekly
        df_w = t.history(period="3mo", interval="1wk")
        df_d1 = t.history(period="1mo", interval="1d")
        
        curr_w = df_w.iloc[-1]
        prev_w = df_w.iloc[-2] if len(df_w) >= 2 else curr_w
        
        live_price = float(curr_w['Close'])
        
        # 4-week Average Weekly Range
        awr_4w = float((df_w['High'] - df_w['Low']).iloc[-5:-1].mean()) if len(df_w) >= 5 else float(curr_w['High'] - curr_w['Low'])
        week_range = float(curr_w['High'] - curr_w['Low'])
        
        # Weekly EMA20
        w_ema20 = float(df_w['Close'].ewm(span=20).mean().iloc[-1])
        w_trend = "🟢 روند هفتگی صعودی (بالای میانگین)" if live_price > w_ema20 else "🔴 روند هفتگی نزولی (زیر میانگین)"
        
        # Weekly Equilibrium
        w_eq = (float(curr_w['High']) + float(curr_w['Low'])) / 2.0
        
        return {
            "sym_key": sym_key,
            "fa_name": fa_name,
            "horizon": "weekly",
            "price": round(live_price, digits),
            "digits": digits,
            "pwh": round(float(prev_w['High']), digits),
            "pwl": round(float(prev_w['Low']), digits),
            "pwc": round(float(prev_w['Close']), digits),
            "week_open": round(float(curr_w['Open']), digits),
            "week_high": round(float(curr_w['High']), digits),
            "week_low": round(float(curr_w['Low']), digits),
            "week_range": round(week_range, digits),
            "awr_4w": round(awr_4w, digits),
            "awr_used_pct": round((week_range / awr_4w * 100), 1) if awr_4w > 0 else 0,
            "weekly_trend": w_trend,
            "weekly_equilibrium": round(w_eq, digits),
            "weekly_ema20": round(w_ema20, digits)
        }

if __name__ == "__main__":
    d = fetch_market_data("US100", "daily")
    w = fetch_market_data("US100", "weekly")
    print("Daily price:", d["price"], "PDH:", d["pdh"], "PDL:", d["pdl"])
    print("Weekly price:", w["price"], "PWH:", w["pwh"], "PWL:", w["pwl"])
