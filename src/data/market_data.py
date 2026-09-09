import yfinance as yf
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

NIFTY_50_POPULAR = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "INFY.NS", "name": "Infosys", "sector": "IT"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "ITC.NS", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "sector": "Capital Goods"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automobile"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki", "sector": "Automobile"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma", "sector": "Healthcare"},
]

def normalize_indian_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    if sym in ["NIFTY", "NIFTY50", "NIFTY 50", "^NSEI"]:
        return "^NSEI"
    if sym in ["BANKNIFTY", "BANK NIFTY", "^NSEBANK"]:
        return "^NSEBANK"
    if sym in ["SENSEX", "^BSESN"]:
        return "^BSESN"
    if not (sym.endswith(".NS") or sym.endswith(".BO")):
        return f"{sym}.NS"
    return sym

def get_stock_quote(symbol: str) -> Dict[str, Any]:
    norm_symbol = normalize_indian_symbol(symbol)
    ticker = yf.Ticker(norm_symbol)
    fast_info = getattr(ticker, "fast_info", None)
    
    current_price = None
    prev_close = None
    day_high = None
    day_low = None
    year_high = None
    year_low = None
    
    if fast_info:
        try:
            current_price = float(fast_info.last_price or 0.0)
            prev_close = float(fast_info.previous_close or current_price)
            day_high = float(fast_info.day_high or current_price)
            day_low = float(fast_info.day_low or current_price)
            year_high = float(fast_info.year_high or current_price)
            year_low = float(fast_info.year_low or current_price)
        except Exception:
            pass
            
    info = ticker.info or {}
    if not current_price:
        current_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
    if not prev_close:
        prev_close = float(info.get("regularMarketPreviousClose") or current_price)

    change = (current_price - prev_close) if (current_price and prev_close) else 0.0
    change_pct = ((change / prev_close) * 100.0) if prev_close else 0.0

    return {
        "symbol": norm_symbol,
        "clean_symbol": norm_symbol.replace(".NS", "").replace(".BO", ""),
        "name": info.get("shortName") or info.get("longName") or norm_symbol,
        "price": round(current_price, 2) if current_price else 0.0,
        "prev_close": round(prev_close, 2) if prev_close else 0.0,
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "day_high": round(day_high or info.get("dayHigh") or 0.0, 2),
        "day_low": round(day_low or info.get("dayLow") or 0.0, 2),
        "year_high": round(year_high or info.get("fiftyTwoWeekHigh") or 0.0, 2),
        "year_low": round(year_low or info.get("fiftyTwoWeekLow") or 0.0, 2),
        "volume": info.get("regularMarketVolume") or info.get("volume") or 0,
        "currency": "INR",
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "timestamp": datetime.now().isoformat()
    }

def get_historical_bars(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    norm_symbol = normalize_indian_symbol(symbol)
    ticker = yf.Ticker(norm_symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f"No price data found for symbol {norm_symbol}")
    df = df.reset_index()
    return df

def get_company_fundamentals(symbol: str) -> Dict[str, Any]:
    norm_symbol = normalize_indian_symbol(symbol)
    ticker = yf.Ticker(norm_symbol)
    info = ticker.info or {}
    
    return {
        "symbol": norm_symbol,
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "debt_to_equity": info.get("debtToEquity"),
        "roe": info.get("returnOnEquity"),
        "profit_margins": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "dividend_yield": info.get("dividendYield"),
        "free_cashflow": info.get("freeCashflow"),
        "description": info.get("longBusinessSummary", ""),
    }

def get_watchlist_snapshots() -> List[Dict[str, Any]]:
    snapshots = []
    for item in NIFTY_50_POPULAR:
        try:
            quote = get_stock_quote(item["symbol"])
            quote["custom_name"] = item["name"]
            snapshots.append(quote)
        except Exception:
            continue
    return snapshots
