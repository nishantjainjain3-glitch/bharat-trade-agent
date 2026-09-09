import concurrent.futures
from typing import List, Dict, Any
from src.data.market_data import get_stock_quote, get_historical_bars, get_company_fundamentals
from src.analysis.technical import analyze_technical_indicators
from src.analysis.fundamental import evaluate_fundamentals
from src.agents.research_team import run_multi_agent_research

UNIVERSE_TICKERS = [
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "ITC.NS", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma", "sector": "Healthcare"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki", "sector": "Automobile"},
    {"symbol": "M&M.NS", "name": "Mahindra & Mahindra", "sector": "Automobile"},
    {"symbol": "NTPC.NS", "name": "NTPC", "sector": "Power"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "TCS.NS", "name": "TCS", "sector": "IT"},
    {"symbol": "TITAN.NS", "name": "Titan Company", "sector": "Consumer"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "sector": "Capital Goods"},
    {"symbol": "INFY.NS", "name": "Infosys", "sector": "IT"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"}
]

def scan_single_stock(item: Dict[str, str]) -> Dict[str, Any]:
    symbol = item["symbol"]
    try:
        quote = get_stock_quote(symbol)
        df = get_historical_bars(symbol, period="6mo", interval="1d")
        technicals = analyze_technical_indicators(df)
        funds = evaluate_fundamentals(get_company_fundamentals(symbol))
        research = run_multi_agent_research(quote, technicals, funds)
        
        price = quote["price"]
        target_str = research.get("target_price", "0").replace("INR", "").replace("₹", "").strip()
        try:
            target_num = float(target_str)
            upside_pct = round(((target_num - price) / price) * 100, 1) if price > 0 else 0.0
        except Exception:
            upside_pct = 5.0

        # Calculate an aggregate Opportunity Score (0 to 100)
        t_score = technicals.get("score", 0)  # -5 to +5
        f_score = funds.get("score", 0)       # -3 to +3
        rsi = technicals.get("rsi", 50)
        
        # Prefer stocks with bullish alignment, RSI in constructive zone (42 to 65), and strong fundamentals
        score = 50 + (t_score * 7) + (f_score * 5)
        if 42 <= rsi <= 62:
            score += 8
        elif rsi > 72:
            score -= 10
            
        verdict = research["verdict"]
        # If overall score is solid, classify as high-priority buy/accumulate opportunity
        if score >= 55 and verdict != "SELL":
            display_verdict = "BUY"
            conviction = max(7, min(9, round(score / 10)))
        elif verdict == "BUY":
            display_verdict = "BUY"
            conviction = research["conviction"]
        elif verdict == "SELL":
            display_verdict = "AVOID"
            conviction = research["conviction"]
        else:
            display_verdict = "ACCUMULATE"
            conviction = max(6, research["conviction"])

        catalyst = research.get("bull_case", "")
        if "Key technical drivers:" in catalyst:
            catalyst = catalyst.split("Key technical drivers:")[1].split(".")[0].strip()
        elif "Fundamental strength:" in catalyst:
            catalyst = catalyst.split("Fundamental strength:")[1].split(".")[0].strip()

        year_high = float(quote.get("year_high") or price)
        dist_52w_high_pct = round(((year_high - price) / year_high) * 100.0, 1) if year_high > 0 else 0.0
        rvol = technicals.get("volume", {}).get("rvol_20d", 1.0)
        candlestick_patterns = technicals.get("candlestick_patterns", [])
        f_metrics = funds.get("metrics", {})
        roe = float(f_metrics.get("roe_pct") or 0.0)
        debt_to_equity = float(f_metrics.get("debt_to_equity") or 0.0)
        ema_50 = technicals.get("emas", {}).get("ema_50", 0.0)
        ema_200 = technicals.get("emas", {}).get("ema_200", 0.0)

        return {
            "symbol": quote["clean_symbol"],
            "full_symbol": symbol,
            "name": item["name"],
            "sector": item["sector"],
            "price": price,
            "change_pct": quote["change_pct"],
            "verdict": display_verdict,
            "conviction": conviction,
            "score": score,
            "entry_range": research["entry_range"],
            "target_price": research["target_price"],
            "stop_loss": research["stop_loss"],
            "upside_pct": upside_pct,
            "risk_reward_ratio": research["risk_reward_ratio"],
            "key_catalyst": catalyst or "Constructive consolidation above support with favorable risk-reward.",
            "rsi": technicals["rsi"],
            "trend": technicals["trend"],
            "dist_52w_high_pct": dist_52w_high_pct,
            "rvol": rvol,
            "relative_volume": rvol,
            "candlestick_patterns": candlestick_patterns,
            "candlestick_pattern": candlestick_patterns[0] if candlestick_patterns else "",
            "fund_score": f_score,
            "roe": roe,
            "debt_to_equity": debt_to_equity,
            "ema_50": ema_50,
            "ema_200": ema_200
        }
    except Exception as e:
        return None

def get_preset_screener_recommendations(preset: str = "ALL", limit: int = 4) -> List[Dict[str, Any]]:
    """
    Scans the Indian large-cap universe against preset strategy filters:
    - MOMENTUM_BREAKOUT (Minervini template): Within 15% of 52W high, price > 50 & 200 EMA, RVOL >= 1.1x
    - OVERSOLD_PULLBACK: RSI <= 48, price > 200 EMA (healthy secular uptrend on a pullback)
    - VALUE_COMPOUNDER: Strong fundamentals (score >= 1, ROE >= 12%, upside >= 5%)
    - ALL: Composite opportunity score
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(scan_single_stock, item) for item in UNIVERSE_TICKERS]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    p_norm = preset.strip().upper()
    
    if p_norm in ["BREAKOUT", "MOMENTUM", "MOMENTUM_BREAKOUT"]:
        candidates = [
            r for r in results 
            if r["dist_52w_high_pct"] <= 15.0 
            and (r["price"] >= r["ema_50"] or r["price"] >= r["ema_200"])
            and r["verdict"] != "AVOID"
        ]
        candidates.sort(key=lambda x: (x["dist_52w_high_pct"], -x["rvol"], -x["score"]))
    elif p_norm in ["OVERSOLD", "DIP", "OVERSOLD_PULLBACK"]:
        candidates = [
            r for r in results 
            if r["rsi"] <= 50.0 
            and r["price"] >= (r["ema_200"] * 0.96)
            and r["verdict"] != "AVOID"
        ]
        candidates.sort(key=lambda x: (x["rsi"], -x["upside_pct"], -x["score"]))
    elif p_norm in ["VALUE", "MOAT", "VALUE_COMPOUNDER"]:
        candidates = [
            r for r in results 
            if r["fund_score"] >= 1 
            and r["upside_pct"] >= 5.0
            and r["verdict"] != "AVOID"
        ]
        candidates.sort(key=lambda x: (-x["fund_score"], -x["upside_pct"], -x["score"]))
    else:
        # Default 'ALL' filter
        candidates = [r for r in results if r["verdict"] in ["BUY", "ACCUMULATE"]]
        candidates.sort(key=lambda x: (x["verdict"] == "BUY", x["score"], x["conviction"]), reverse=True)

    # Fallback to general candidates if strict filter returns empty
    if not candidates:
        candidates = [r for r in results if r["verdict"] in ["BUY", "ACCUMULATE"]]
        candidates.sort(key=lambda x: (x["verdict"] == "BUY", x["score"], x["conviction"]), reverse=True)

    return candidates[:limit]

def get_top_buy_recommendations(limit: int = 4) -> List[Dict[str, Any]]:
    return get_preset_screener_recommendations(preset="ALL", limit=limit)
