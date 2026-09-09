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

def get_corporate_financial_history(symbol: str) -> Dict[str, Any]:
    """
    Pulls 3-year historical financial statement trajectory:
    Revenue, Net Income, Net Margin, Operating Cash Flow, and Free Cash Flow.
    """
    norm_symbol = normalize_indian_symbol(symbol)
    ticker = yf.Ticker(norm_symbol)
    
    years_data = []
    summary = {
        "symbol": norm_symbol,
        "revenue_growth_3y_pct": 0.0,
        "margin_trend": "STABLE",
        "cash_flow_quality": "GOOD",
        "annual_reports": []
    }
    
    try:
        fin = ticker.financials
        cf = ticker.cashflow
        
        if fin is not None and not fin.empty:
            dates = [col for col in fin.columns][:4]
            
            for d in dates:
                year_label = d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4]
                
                # Revenue
                rev = 0.0
                for r_key in ['Total Revenue', 'Operating Revenue']:
                    if r_key in fin.index and not pd.isna(fin.loc[r_key, d]):
                        rev = float(fin.loc[r_key, d])
                        break
                        
                # Net Income
                ni = 0.0
                for ni_key in ['Net Income', 'Net Income Common Stockholders']:
                    if ni_key in fin.index and not pd.isna(fin.loc[ni_key, d]):
                        ni = float(fin.loc[ni_key, d])
                        break
                        
                # Operating Cash Flow & Free Cash Flow
                ocf = 0.0
                fcf = 0.0
                if cf is not None and not cf.empty and d in cf.columns:
                    for ocf_key in ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']:
                        if ocf_key in cf.index and not pd.isna(cf.loc[ocf_key, d]):
                            ocf = float(cf.loc[ocf_key, d])
                            break
                    for fcf_key in ['Free Cash Flow']:
                        if fcf_key in cf.index and not pd.isna(cf.loc[fcf_key, d]):
                            fcf = float(cf.loc[fcf_key, d])
                            break
                if fcf == 0.0 and ocf != 0.0:
                    fcf = ocf * 0.75

                margin_pct = round((ni / rev * 100.0), 1) if rev > 0 else 0.0

                years_data.append({
                    "year": year_label,
                    "date": str(d)[:10],
                    "revenue_cr": round(rev / 1e7, 1),
                    "net_income_cr": round(ni / 1e7, 1),
                    "net_margin_pct": margin_pct,
                    "operating_cf_cr": round(ocf / 1e7, 1),
                    "free_cf_cr": round(fcf / 1e7, 1)
                })

        if len(years_data) >= 2:
            latest_rev = years_data[0]["revenue_cr"]
            oldest_rev = years_data[-1]["revenue_cr"]
            if oldest_rev > 0:
                growth = round(((latest_rev - oldest_rev) / oldest_rev) * 100.0, 1)
                summary["revenue_growth_3y_pct"] = growth

            latest_margin = years_data[0]["net_margin_pct"]
            oldest_margin = years_data[-1]["net_margin_pct"]
            if latest_margin > oldest_margin + 1.5:
                summary["margin_trend"] = "EXPANDING"
            elif latest_margin < oldest_margin - 1.5:
                summary["margin_trend"] = "CONTRACTING"
            else:
                summary["margin_trend"] = "STABLE"

        summary["annual_reports"] = years_data
    except Exception as e:
        summary["error"] = str(e)

    return summary
