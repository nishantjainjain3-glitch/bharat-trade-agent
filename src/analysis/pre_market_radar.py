"""
Pre-Market Global Radar & Opening Bias Engine.
Synthesizes overnight US markets (S&P 500, Nasdaq), Asian indices (Nikkei),
macro drivers (Brent Crude, USD/INR), and domestic market indicators
to formulate an actionable Opening Bias before NSE 09:15 IST market open.
"""
import yfinance as yf
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

GLOBAL_RADAR_TICKERS = {
    "SP500": {"symbol": "^GSPC", "name": "S&P 500 (US)", "weight": 0.30},
    "NASDAQ": {"symbol": "^IXIC", "name": "Nasdaq 100 (US)", "weight": 0.25},
    "NIKKEI": {"symbol": "^N225", "name": "Nikkei 225 (Asia)", "weight": 0.15},
    "BRENT_CRUDE": {"symbol": "BZ=F", "name": "Brent Crude Oil", "weight": -0.15}, # Higher crude is headwind for India
    "USDINR": {"symbol": "INR=X", "name": "USD / INR", "weight": -0.15} # Weaker rupee is headwind
}


def get_pre_market_radar() -> Dict[str, Any]:
    """
    Evaluates global cues and calculates an Opening Bias Score (-100 to +100).
    Bias categories:
    - BULLISH_EXPANSION (Score >= +25): Favor long breakouts, momentum continuation, aggressive sizing.
    - BEARISH_DEFENSIVE (Score <= -25): Favor cash preservation, tighten trailing stops, pause long entries.
    - NEUTRAL_RANGEBOUND (-25 < Score < +25): Favor range trading, mean reversion, Value Area bounce setups.
    """
    tickers_data = {}
    weighted_score = 0.0

    for key, cfg in GLOBAL_RADAR_TICKERS.items():
        sym = cfg["symbol"]
        weight = cfg["weight"]
        try:
            t = yf.Ticker(sym)
            fi = getattr(t, "fast_info", None)
            price = 0.0
            prev = 0.0
            if fi:
                price = float(fi.last_price or 0.0)
                prev = float(fi.previous_close or price)
            
            if price == 0.0:
                h = t.history(period="2d")
                if len(h) >= 2:
                    price = float(h['Close'].iloc[-1])
                    prev = float(h['Close'].iloc[-2])
                elif len(h) == 1:
                    price = float(h['Close'].iloc[-1])
                    prev = price

            chg_pct = round(((price - prev) / prev) * 100.0, 2) if prev > 0 else 0.0
            # Normalize impact (-3% to +3% maps to -100 to +100)
            clamped_pct = max(-3.0, min(3.0, chg_pct))
            sub_score = (clamped_pct / 3.0) * 100.0
            weighted_score += sub_score * weight

            tickers_data[key] = {
                "name": cfg["name"],
                "symbol": sym,
                "price": round(price, 2),
                "change_pct": chg_pct,
                "sentiment": "BULLISH" if (chg_pct * (1 if weight > 0 else -1)) > 0 else "BEARISH"
            }
        except Exception as e:
            logger.warning("Radar ticker %s fetch error: %s", sym, str(e))
            tickers_data[key] = {
                "name": cfg["name"],
                "symbol": sym,
                "price": 0.0,
                "change_pct": 0.0,
                "sentiment": "NEUTRAL"
            }

    # Institutional flows synthesis
    try:
        from src.data.fii_dii import get_fii_dii_activity
        fii_dii = get_fii_dii_activity()
        fii_net = fii_dii.get("fii_net_crores", 0.0)
        # Factor FII net into score (each 500 cr net buy is +5 points, capped at +/- 25)
        fii_flow_impact = max(-25.0, min(25.0, (fii_net / 500.0) * 5.0))
        weighted_score += fii_flow_impact
    except Exception:
        fii_dii = None

    bias_score = round(weighted_score, 1)

    if bias_score >= 25.0:
        opening_bias = "BULLISH_EXPANSION"
        action_directive = "Favor momentum breakouts (VCP & 20D Donchian). Deploy up to 1.0x risk allocation."
        badge_color = "#10b981"
    elif bias_score <= -25.0:
        opening_bias = "BEARISH_DEFENSIVE"
        action_directive = "Elevate cash defenses. Tighten trailing stops. Cut allocation multiplier to 0.5x."
        badge_color = "#ef4444"
    else:
        opening_bias = "NEUTRAL_RANGEBOUND"
        action_directive = "Selective stock-picking. Favor Value Area discount bounces (FRVP) and mean-reversion."
        badge_color = "#f59e0b"

    now_ist = datetime.now(IST)

    return {
        "timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "opening_bias": opening_bias,
        "bias_score": bias_score,
        "action_directive": action_directive,
        "badge_color": badge_color,
        "global_cues": tickers_data,
        "institutional_flows": fii_dii
    }
