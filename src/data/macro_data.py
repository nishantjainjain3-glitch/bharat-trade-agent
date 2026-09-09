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
