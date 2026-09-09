import yfinance as yf
from typing import Dict, Any

MACRO_TICKERS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "USDINR": "INR=X",
    "CRUDE_OIL": "BZ=F"
}

def get_indian_macro_indicators() -> Dict[str, Any]:
    """Fetches key macroeconomic drivers for Indian stock markets."""
    results = {}
    
    for key, symbol in MACRO_TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            fast_info = getattr(ticker, "fast_info", None)
            price = 0.0
            prev = 0.0
            
            if fast_info:
                price = float(fast_info.last_price or 0.0)
                prev = float(fast_info.previous_close or price)
            
            if price == 0.0:
                hist = ticker.history(period="2d")
                if len(hist) >= 2:
                    price = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2])
                elif len(hist) == 1:
                    price = float(hist['Close'].iloc[-1])
                    prev = price
                    
            change = price - prev if prev else 0.0
            change_pct = (change / prev) * 100.0 if prev else 0.0
            
            label_map = {
                "NIFTY": "Nifty 50",
                "BANKNIFTY": "Bank Nifty",
                "USDINR": "USD / INR",
                "CRUDE_OIL": "Brent Crude"
            }
            
            results[key] = {
                "name": label_map.get(key, key),
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "is_positive": change >= 0
            }
        except Exception:
            results[key] = {
                "name": key,
                "symbol": symbol,
                "price": 0.0,
                "change": 0.0,
                "change_pct": 0.0,
                "is_positive": True
            }
            
    return results

SECTOR_MAP = {
    "Banking": {
        "index_symbol": "^NSEBANK",
        "anchors": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]
    },
    "IT Services": {
        "index_symbol": "^CNXIT",
        "anchors": ["TCS.NS", "INFY.NS", "WIPRO.NS"]
    },
    "Pharma & Health": {
        "index_symbol": "^CNXPHARMA",
        "anchors": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS"]
    },
    "Automobile": {
        "index_symbol": None,
        "anchors": ["MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS"]
    },
    "Energy & Oil": {
        "index_symbol": None,
        "anchors": ["RELIANCE.NS", "NTPC.NS", "ONGC.NS"]
    },
    "FMCG": {
        "index_symbol": None,
        "anchors": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS"]
    },
    "Metals & Mining": {
        "index_symbol": None,
        "anchors": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"]
    }
}

def get_nse_sector_heatmap() -> Dict[str, Any]:
    """
    Computes performance across 7 major NSE sectors, identifying
    leading industry groups, market breadth, and top stock drivers.
    """
    sector_results = []
    
    for sector_name, info in SECTOR_MAP.items():
        anchors = info.get("anchors", [])
        leader = None
        laggard = None
        max_chg = -999.0
        min_chg = 999.0
        anchor_changes = []
        
        for sym in anchors:
            try:
                t = yf.Ticker(sym)
                fast_info = getattr(t, "fast_info", None)
                if fast_info and fast_info.last_price and fast_info.previous_close:
                    p = float(fast_info.last_price)
                    prev = float(fast_info.previous_close)
                    chg = round(((p - prev) / prev) * 100.0, 2)
                else:
                    h = t.history(period="2d")
                    if len(h) >= 2:
                        c0, c1 = float(h['Close'].iloc[-2]), float(h['Close'].iloc[-1])
                        chg = round(((c1 - c0) / c0) * 100.0, 2)
                    else:
                        chg = 0.0
                anchor_changes.append(chg)
                short_name = sym.replace(".NS", "")
                if chg > max_chg:
                    max_chg = chg
                    leader = f"{short_name} ({chg:+.1f}%)"
                if chg < min_chg:
                    min_chg = chg
                    laggard = f"{short_name} ({chg:+.1f}%)"
            except Exception:
                continue
                
        if anchor_changes:
            sector_chg = round(sum(anchor_changes) / len(anchor_changes), 2)
        else:
            sector_chg = 0.0
            
        sector_results.append({
            "sector": sector_name,
            "change_pct": sector_chg,
            "is_positive": sector_chg >= 0,
            "status": "BULLISH" if sector_chg > 0.5 else ("BEARISH" if sector_chg < -0.5 else "NEUTRAL"),
            "leader": leader or "N/A",
            "laggard": laggard or "N/A"
        })
        
    sector_results.sort(key=lambda x: x["change_pct"], reverse=True)
    top_gainer = sector_results[0] if sector_results else None
    top_loser = sector_results[-1] if sector_results else None
    
    return {
        "sectors": sector_results,
        "top_gaining_sector": top_gainer["sector"] if top_gainer else "N/A",
        "top_losing_sector": top_loser["sector"] if top_loser else "N/A",
        "market_breadth": f"{len([s for s in sector_results if s['is_positive']])} Advancing / {len([s for s in sector_results if not s['is_positive']])} Declining"
    }
