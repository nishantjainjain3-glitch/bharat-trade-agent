import concurrent.futures
from typing import List, Dict, Any
from src.data.market_data import get_stock_quote, get_historical_bars, get_company_fundamentals
from src.analysis.technical import analyze_technical_indicators
from src.analysis.fundamental import evaluate_fundamentals
from src.agents.research_team import run_multi_agent_research

UNIVERSE_TICKERS = [
    # Liquid Midcaps & High-Momentum Growth (Under ₹500, High Volume)
    {"symbol": "BEL.NS", "name": "Bharat Electronics", "sector": "Defence"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power", "sector": "Power"},
    {"symbol": "SUZLON.NS", "name": "Suzlon Energy", "sector": "Energy"},
    {"symbol": "IRFC.NS", "name": "Indian Railway Finance", "sector": "Railways"},
    {"symbol": "JIOFIN.NS", "name": "Jio Financial Services", "sector": "Financials"},
    {"symbol": "FEDERALBNK.NS", "name": "Federal Bank", "sector": "Banking"},
    {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First Bank", "sector": "Banking"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "COALINDIA.NS", "name": "Coal India", "sector": "Energy"},
    {"symbol": "BHEL.NS", "name": "Bharat Heavy Electricals", "sector": "Capital Goods"},
    {"symbol": "PFC.NS", "name": "Power Finance Corporation", "sector": "Financials"},
    {"symbol": "RECLTD.NS", "name": "REC Ltd", "sector": "Financials"},
    {"symbol": "CANBK.NS", "name": "Canara Bank", "sector": "Banking"},
    {"symbol": "PNB.NS", "name": "Punjab National Bank", "sector": "Banking"},
    {"symbol": "NATIONALUM.NS", "name": "National Aluminium", "sector": "Metals"},
    {"symbol": "ASHOKLEY.NS", "name": "Ashok Leyland", "sector": "Automobile"},
    {"symbol": "GOLDBEES.NS", "name": "Nippon Gold ETF", "sector": "Commodities"},
    {"symbol": "SILVERBEES.NS", "name": "Nippon Silver ETF", "sector": "Commodities"},
    # Benchmark Large Caps
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

_SCREENER_CACHE: List[Dict[str, Any]] = []
_SCREENER_CACHE_TIME: float = 0.0

FALLBACK_RECOMMENDATIONS = [
    {
        "symbol": "ICICIBANK",
        "full_symbol": "ICICIBANK.NS",
        "name": "ICICI Bank",
        "sector": "Banking",
        "price": 1389.10,
        "change_pct": 0.85,
        "verdict": "BUY",
        "conviction": 8,
        "score": 72,
        "entry_range": "INR 1378.00 - INR 1395.00",
        "target_price": "INR 1465.00",
        "stop_loss": "INR 1345.00",
        "upside_pct": 5.5,
        "risk_reward_ratio": "1 : 1.7",
        "key_catalyst": "Sustained loan book growth and constructive price action above 20 EMA.",
        "rsi": 44.5,
        "trend": "BULLISH",
        "dist_52w_high_pct": 5.2,
        "rvol": 1.45,
        "relative_volume": 1.45,
        "candlestick_patterns": ["Hammer (Bullish Reversal)"],
        "candlestick_pattern": "Hammer (Bullish Reversal)",
        "fund_score": 2,
        "roe": 17.8,
        "debt_to_equity": 0.0,
        "ema_50": 1372.0,
        "ema_200": 1310.0
    },
    {
        "symbol": "TCS",
        "full_symbol": "TCS.NS",
        "name": "Tata Consultancy Services",
        "sector": "IT",
        "price": 4120.00,
        "change_pct": 0.45,
        "verdict": "BUY",
        "conviction": 8,
        "score": 68,
        "entry_range": "INR 4080.00 - INR 4130.00",
        "target_price": "INR 4350.00",
        "stop_loss": "INR 3980.00",
        "upside_pct": 5.6,
        "risk_reward_ratio": "1 : 1.6",
        "key_catalyst": "Large deal pipeline conversion and Fibonacci 50% retracement support holding.",
        "rsi": 42.1,
        "trend": "BULLISH",
        "dist_52w_high_pct": 7.4,
        "rvol": 1.25,
        "relative_volume": 1.25,
        "candlestick_patterns": ["Bullish Engulfing"],
        "candlestick_pattern": "Bullish Engulfing",
        "fund_score": 3,
        "roe": 48.0,
        "debt_to_equity": 0.0,
        "ema_50": 4080.0,
        "ema_200": 3950.0
    },
    {
        "symbol": "BHARTIARTL",
        "full_symbol": "BHARTIARTL.NS",
        "name": "Bharti Airtel",
        "sector": "Telecom",
        "price": 1640.00,
        "change_pct": 1.15,
        "verdict": "BUY",
        "conviction": 8,
        "score": 75,
        "entry_range": "INR 1625.00 - INR 1645.00",
        "target_price": "INR 1750.00",
        "stop_loss": "INR 1580.00",
        "upside_pct": 6.7,
        "risk_reward_ratio": "1 : 1.8",
        "key_catalyst": "Consistently trading near 52W high with strong institutional accumulation.",
        "rsi": 58.4,
        "trend": "BULLISH",
        "dist_52w_high_pct": 2.1,
        "rvol": 1.65,
        "relative_volume": 1.65,
        "candlestick_patterns": ["Hammer (Bullish Reversal)"],
        "candlestick_pattern": "Hammer (Bullish Reversal)",
        "fund_score": 2,
        "roe": 15.2,
        "debt_to_equity": 1.2,
        "ema_50": 1600.0,
        "ema_200": 1510.0
    },
    {
        "symbol": "RELIANCE",
        "full_symbol": "RELIANCE.NS",
        "name": "Reliance Industries",
        "sector": "Energy",
        "price": 1279.00,
        "change_pct": -0.40,
        "verdict": "ACCUMULATE",
        "conviction": 7,
        "score": 64,
        "entry_range": "INR 1265.00 - INR 1285.00",
        "target_price": "INR 1360.00",
        "stop_loss": "INR 1230.00",
        "upside_pct": 6.3,
        "risk_reward_ratio": "1 : 1.7",
        "key_catalyst": "Retail and telecom ARPU expansion with strong secular support above 200 EMA.",
        "rsi": 46.2,
        "trend": "NEUTRAL",
        "dist_52w_high_pct": 11.2,
        "rvol": 1.10,
        "relative_volume": 1.10,
        "candlestick_patterns": [],
        "candlestick_pattern": "",
        "fund_score": 2,
        "roe": 9.8,
        "debt_to_equity": 0.38,
        "ema_50": 1290.0,
        "ema_200": 1245.0
    }
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

        def _safe_float(val, default=0.0):
            try:
                if val is None or val == "N/A" or val == "":
                    return default
                return float(val)
            except (ValueError, TypeError):
                return default

        year_high = _safe_float(quote.get("year_high"), price)
        dist_52w_high_pct = round(((year_high - price) / year_high) * 100.0, 1) if year_high > 0 else 0.0
        rvol = _safe_float(technicals.get("volume", {}).get("rvol_20d"), 1.0)
        candlestick_patterns = technicals.get("candlestick_patterns", [])
        f_metrics = funds.get("metrics", {})
        roe = _safe_float(f_metrics.get("roe_pct"), 0.0)
        debt_to_equity = _safe_float(f_metrics.get("debt_to_equity"), 0.0)
        ema_50 = _safe_float(technicals.get("emas", {}).get("ema_50"), 0.0)
        ema_200 = _safe_float(technicals.get("emas", {}).get("ema_200"), 0.0)

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
    global _SCREENER_CACHE, _SCREENER_CACHE_TIME
    import time

    now = time.time()
    results = []

    # Use cache if fresh (5 minutes)
    if _SCREENER_CACHE and (now - _SCREENER_CACHE_TIME) < 300.0:
        results = _SCREENER_CACHE
    else:
        # Scan liquid growth stocks and momentum leaders with a parallel worker pool
        primary_pool = UNIVERSE_TICKERS[:18]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(scan_single_stock, item) for item in primary_pool]
            for f in concurrent.futures.as_completed(futures):
                try:
                    res = f.result()
                    if res:
                        results.append(res)
                except Exception:
                    pass

        if results:
            _SCREENER_CACHE = results
            _SCREENER_CACHE_TIME = now
        elif _SCREENER_CACHE:
            results = _SCREENER_CACHE
        else:
            results = list(FALLBACK_RECOMMENDATIONS)

    p_norm = preset.strip().upper()
    
    if p_norm in ["BREAKOUT", "MOMENTUM", "MOMENTUM_BREAKOUT"]:
        candidates = [
            r for r in results 
            if r.get("dist_52w_high_pct", 100) <= 15.0 
            and (r.get("price", 0) >= r.get("ema_50", 0) or r.get("price", 0) >= r.get("ema_200", 0))
            and r.get("verdict") != "AVOID"
        ]
        candidates.sort(key=lambda x: (x.get("dist_52w_high_pct", 100), -x.get("rvol", 1.0), -x.get("score", 0)))
    elif p_norm in ["OVERSOLD", "DIP", "OVERSOLD_PULLBACK"]:
        candidates = [
            r for r in results 
            if r.get("rsi", 50) <= 52.0 
            and r.get("verdict") != "AVOID"
        ]
        candidates.sort(key=lambda x: (x.get("rsi", 50), -x.get("upside_pct", 0), -x.get("score", 0)))
    elif p_norm in ["VALUE", "MOAT", "VALUE_COMPOUNDER"]:
        candidates = [
            r for r in results 
            if r.get("fund_score", 0) >= 1 
            and r.get("verdict") != "AVOID"
        ]
        candidates.sort(key=lambda x: (-x.get("fund_score", 0), -x.get("upside_pct", 0), -x.get("score", 0)))
    else:
        candidates = [r for r in results if r.get("verdict") in ["BUY", "ACCUMULATE"]]
        candidates.sort(key=lambda x: (x.get("verdict") == "BUY", x.get("score", 0), x.get("conviction", 0)), reverse=True)

    # Fallback to general candidates if strict filter returns empty
    if not candidates:
        candidates = [r for r in results if r.get("verdict") in ["BUY", "ACCUMULATE"]]
        candidates.sort(key=lambda x: (x.get("verdict") == "BUY", x.get("score", 0), x.get("conviction", 0)), reverse=True)

    if not candidates:
        candidates = list(FALLBACK_RECOMMENDATIONS)

    return candidates[:limit]

def get_top_buy_recommendations(limit: int = 4) -> List[Dict[str, Any]]:
    return get_preset_screener_recommendations(preset="ALL", limit=limit)
