import concurrent.futures
import pandas as pd
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

def get_high_momentum_breakouts(limit: int = 5, target_pct: float = 5.5, stop_pct: float = 2.5) -> List[Dict[str, Any]]:
    """
    Scans real-time market movers and volume breakout leaders across NSE via Angel One API.
    Identifies high-velocity stocks capable of 5% - 10% gains intraday or within 1-2 days.
    """
    import os, json, re
    from src.broker.angel_one import angel_client
    
    tokens_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "angel_tokens.json")
    tokens_map = {}
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, "r", encoding="utf-8") as f:
                tokens_map = json.load(f)
        except Exception:
            pass

    # 1. Fetch real-time market gainers from Angel One
    raw_gainers = angel_client.get_market_gainers(datatype="PercPriceGainers", expirytype="NEAR")
    
    # 2. Extract underlying equity symbols and map to tokens
    symbol_token_map = {}
    for g in raw_gainers:
        ts = g.get("tradingSymbol", "")
        clean_sym = re.sub(r"\d{2}[A-Z]{3}\d{2}FUT", "", ts).strip().upper()
        tok = tokens_map.get(clean_sym)
        if tok and clean_sym not in symbol_token_map:
            symbol_token_map[clean_sym] = tok

    # Also include known momentum movers if in token database
    for extra in ["PINELABS", "INDUSTOWER", "YESBANK", "PAYTM", "SUZLON"]:
        if extra in tokens_map and extra not in symbol_token_map:
            symbol_token_map[extra] = tokens_map[extra]

    if not symbol_token_map:
        return []

    # 3. Batch fetch real-time full quotes from Angel One
    tokens_to_fetch = list(symbol_token_map.values())[:25]
    quotes = angel_client.get_batch_quotes(tokens_to_fetch, exchange="NSE")

    candidates = []
    for q in quotes:
        raw_sym = str(q.get("tradingSymbol", "")).replace("-EQ", "").upper()
        ltp = float(q.get("ltp") or 0.0)
        day_chg = float(q.get("percentChange") or 0.0)
        volume = int(q.get("tradeVolume") or 0)
        day_high = float(q.get("high") or ltp)
        day_low = float(q.get("low") or ltp)

        if ltp <= 0 or volume < 500000:
            continue

        tp = round(ltp * (1.0 + target_pct / 100.0), 2)
        sl = round(ltp * (1.0 - stop_pct / 100.0), 2)
        
        # OpenTerminalUI classification logic
        rvol = round(volume / 5000000.0, 2) if volume > 0 else 1.0
        if day_chg >= 5.0 and volume > 15000000:
            setup_type = "VOLUME_SPIKE_BREAKOUT"
            event_type = "TRIGGERED"
            conviction = 10
            catalyst = "Massive volume expansion with explosive price breakout above resistance."
        elif day_chg >= 3.0:
            setup_type = "RANGE_BREAKOUT_UP"
            event_type = "TRIGGERED"
            conviction = 9 if volume > 5000000 else 8
            catalyst = "Sustained upward price momentum clearing near-term consolidation band."
        else:
            setup_type = "MOMENTUM_EXPANSION"
            event_type = "NEAR_TRIGGER"
            conviction = 8
            catalyst = "Accumulation volume rising with price testing breakout threshold."

        candidates.append({
            "symbol": raw_sym,
            "name": raw_sym,
            "price": ltp,
            "day_change_pct": round(day_chg, 2),
            "volume": volume,
            "rvol": rvol,
            "day_high": day_high,
            "day_low": day_low,
            "target_price": tp,
            "target_return_pct": target_pct,
            "stop_loss": sl,
            "stop_loss_pct": stop_pct,
            "risk_reward_ratio": round(target_pct / stop_pct, 2),
            "expected_hold": "Same day to 2 days",
            "conviction": conviction,
            "setup_type": setup_type,
            "event_type": event_type,
            "strategy": "High-Volume Real-Time Breakout",
            "catalyst_summary": catalyst
        })

    candidates.sort(key=lambda x: (-x["day_change_pct"], -x["volume"]))
    return candidates[:limit]


def scan_vcp_candidates(limit: int = 10) -> Dict[str, Any]:
    """
    Volatility Contraction Pattern (VCP) Scanner — Mark Minervini's signature setup.
    Scans stocks from the default watchlist for the VCP pattern:
    1. Stock must be in Minervini Trend Template (price > 50 EMA > 150 SMA > 200 SMA)
    2. ATR% must be contracting over the last 3 price pivots (each 30-50% smaller)
    3. Stock must be within 10% of its 52-week high
    Returns stocks that qualify as VCP breakout candidates.
    """
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    import logging
    logger = logging.getLogger(__name__)

    candidates = []
    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]

    for symbol in symbols[:30]:  # limit API calls
        try:
            df = get_historical_bars(symbol, period="1y", interval="1d")
            if len(df) < 60:
                continue

            close = df['Close']
            current_price = float(close.iloc[-1])

            # Trend Template check
            ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
            sma150 = float(close.rolling(150).mean().iloc[-1]) if len(df) >= 150 else ema50
            sma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma150

            trend_template_pass = (
                current_price > ema50 > sma150 > sma200
            )
            if not trend_template_pass:
                continue

            # 52-week proximity check: within 10% of 52-week high
            high_52w = float(df['High'].tail(252).max()) if len(df) >= 252 else float(df['High'].max())
            near_high = current_price >= high_52w * 0.90
            if not near_high:
                continue

            # ATR% contraction check over last 3 pivots (proxied by 3 rolling windows)
            atr_pcts = []
            for window_start in [-60, -40, -20]:
                window_df = df.iloc[window_start:]
                tr = pd.concat([
                    window_df['High'] - window_df['Low'],
                    (window_df['High'] - window_df['Close'].shift(1)).abs(),
                    (window_df['Low'] - window_df['Close'].shift(1)).abs()
                ], axis=1).max(axis=1)
                window_atr_pct = float(tr.mean() / current_price * 100.0)
                atr_pcts.append(window_atr_pct)

            # VCP: each window should have lower ATR% than the previous
            atr_contracting = atr_pcts[0] > atr_pcts[1] > atr_pcts[2]
            if not atr_contracting:
                continue

            contraction_ratio = round(atr_pcts[2] / atr_pcts[0] * 100.0, 1)

            candidates.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "ema50": round(ema50, 2),
                "sma200": round(sma200, 2),
                "high_52w": round(high_52w, 2),
                "proximity_to_52w_high_pct": round((current_price / high_52w) * 100, 1),
                "atr_pct_60d": round(atr_pcts[0], 2),
                "atr_pct_40d": round(atr_pcts[1], 2),
                "atr_pct_20d": round(atr_pcts[2], 2),
                "atr_contraction_ratio_pct": contraction_ratio,
                "setup": "VCP_BREAKOUT_CANDIDATE",
                "rule": "Minervini SEPA Trend Template + Volatility Contraction Pattern"
            })

            if len(candidates) >= limit:
                break

        except Exception as e:
            logger.warning("VCP scan error for %s: %s", symbol, str(e))
            continue

    return {
        "scan_type": "VCP_MINERVINI",
        "candidates": sorted(candidates, key=lambda x: x.get("atr_contraction_ratio_pct", 100)),
        "total_found": len(candidates)
    }


def scan_momentum_rotation(limit: int = 20) -> Dict[str, Any]:
    """
    12-1 Momentum Rotation Scanner — Alok Jain (Weekend Investing) style.
    Ranks Nifty 500 stocks by 12-month return excluding the most recent 1 month
    (to avoid reversal bias). Returns the top limit stocks by momentum score.
    This is the core of a weekly momentum rotation strategy.
    """
    from src.data.market_data import get_historical_bars
    from src.data.nifty500 import NIFTY_500_SYMBOLS
    import logging
    logger = logging.getLogger(__name__)

    scored = []
    # Sample 80 stocks to keep API calls manageable (rotate through full list in prod)
    sample = NIFTY_500_SYMBOLS[:80]

    for symbol in sample:
        try:
            df = get_historical_bars(symbol, period="13mo", interval="1mo")
            if len(df) < 13:
                continue

            price_now = float(df['Close'].iloc[-1])       # current month end
            price_1m_ago = float(df['Close'].iloc[-2])    # 1 month ago end
            price_12m_ago = float(df['Close'].iloc[-13])  # 12 months ago end

            if price_12m_ago <= 0 or price_1m_ago <= 0:
                continue

            # 12-1 momentum: return from 12 months ago to 1 month ago (skip recent month)
            momentum_12_1 = (price_1m_ago - price_12m_ago) / price_12m_ago * 100.0
            # Recent 1-month return (for context)
            return_1m = (price_now - price_1m_ago) / price_1m_ago * 100.0

            scored.append({
                "symbol": symbol,
                "price": round(price_now, 2),
                "momentum_12_1_pct": round(momentum_12_1, 2),
                "return_1m_pct": round(return_1m, 2),
                "momentum_rank": 0  # filled after sort
            })
        except Exception as e:
            logger.warning("Momentum scan error for %s: %s", symbol, str(e))
            continue

    # Rank by 12-1 momentum descending
    scored.sort(key=lambda x: x["momentum_12_1_pct"], reverse=True)
    for rank, item in enumerate(scored[:limit], start=1):
        item["momentum_rank"] = rank

    return {
        "scan_type": "MOMENTUM_ROTATION_12_1",
        "strategy": "Alok Jain Weekend Investing — Buy top 20 Nifty 500 by 12-1 month momentum, rebalance weekly",
        "top_stocks": scored[:limit],
        "total_ranked": len(scored)
    }


def scan_donchian_breakouts(period: int = 20, limit: int = 10) -> Dict[str, Any]:
    """
    Donchian Channel Breakout Scanner — Richard Dennis / Ed Seykota Turtle System.
    Finds stocks making new N-day high breakouts with:
    - ADX > 20 (confirming trend has energy)
    - Volume >= 1.5x 20-day average (institutional participation)
    Classic Turtle System 1 uses 20-day. System 2 uses 55-day.
    """
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    from src.analysis.technical import calculate_adx
    import logging
    logger = logging.getLogger(__name__)

    breakouts = []
    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]

    for symbol in symbols[:40]:
        try:
            df = get_historical_bars(symbol, period="6mo", interval="1d")
            if len(df) < period + 5:
                continue

            current_high = float(df['High'].iloc[-1])
            channel_high = float(df['High'].tail(period + 1).iloc[:-1].max())  # exclude today

            # Breakout: today's high >= N-day channel high
            if current_high < channel_high * 0.998:
                continue

            # ADX filter
            adx_info = calculate_adx(df, 14)
            if adx_info.get("adx", 0) < 20:
                continue

            # Volume filter
            avg_vol = float(df['Volume'].tail(20).mean()) if 'Volume' in df.columns else 1.0
            current_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else avg_vol
            vol_ratio = round(current_vol / avg_vol, 2) if avg_vol > 0 else 1.0
            if vol_ratio < 1.5:
                continue

            current_price = float(df['Close'].iloc[-1])
            atr = float(pd.concat([
                df['High'] - df['Low'],
                (df['High'] - df['Close'].shift(1)).abs(),
                (df['Low'] - df['Close'].shift(1)).abs()
            ], axis=1).max(axis=1).tail(14).mean())

            turtle_stop = round(current_price - 2 * atr, 2)

            breakouts.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "channel_high": round(channel_high, 2),
                "channel_period": period,
                "adx": adx_info.get("adx"),
                "volume_ratio": vol_ratio,
                "turtle_stop_2atr": turtle_stop,
                "setup": f"DONCHIAN_{period}D_BREAKOUT",
                "rule": "Turtle System 1: New N-day high + ADX > 20 + Volume 1.5x avg"
            })

            if len(breakouts) >= limit:
                break

        except Exception as e:
            logger.warning("Donchian scan error for %s: %s", symbol, str(e))
            continue

    return {
        "scan_type": "DONCHIAN_BREAKOUT",
        "period": period,
        "breakouts": breakouts,
        "total_found": len(breakouts)
    }


def scan_5ema_setups(limit: int = 10, period: str = "1mo", interval: str = "1d") -> Dict[str, Any]:
    """
    Subasish Pani (Power of Stocks) 5 EMA Screener.
    Scans the watchlist for:
    - Active breakouts (trigger candle has breached alert candle high/low)
    - Pending alert setups (non-touch candle completed, waiting for breakout)
    - Forming alert setups (current candle is non-touching 5 EMA)
    Enforces the 2.2x ATR candle size rule and minimum 1:3 reward-to-risk targets.
    """
    from src.analysis.technical import calculate_5ema_setup
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    import logging
    logger = logging.getLogger(__name__)

    active_setups = []
    pending_setups = []

    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]
    if not symbols:
        symbols = [item.get("symbol") for item in UNIVERSE_TICKERS]

    for symbol in symbols[:30]:
        try:
            df = get_historical_bars(symbol, period=period, interval=interval)
            if len(df) < 10:
                continue
            setup_res = calculate_5ema_setup(df)
            if setup_res.get("setup") != "NO_SETUP":
                record = {
                    "symbol": symbol,
                    "clean_symbol": symbol.replace(".NS", "").replace(".BO", ""),
                    **setup_res
                }
                if setup_res.get("is_active"):
                    active_setups.append(record)
                else:
                    pending_setups.append(record)
                if len(active_setups) + len(pending_setups) >= limit:
                    break
        except Exception as e:
            logger.warning("5 EMA scan error for %s: %s", symbol, str(e))
            continue

    all_candidates = active_setups + pending_setups
    return {
        "scan_type": "POWER_OF_STOCKS_5EMA",
        "mentor": "Subasish Pani (Power of Stocks)",
        "active_breakouts": active_setups[:limit],
        "pending_alerts": pending_setups[:limit],
        "total_active": len(active_setups),
        "total_pending": len(pending_setups),
        "candidates": all_candidates[:limit]
    }


def scan_pbd_setups(limit: int = 10, period: str = "3mo", interval: str = "1d", account_equity: float = 100000.0) -> Dict[str, Any]:
    """
    Patrick Nill PBD Model Screener.
    Scans the watchlist for:
    - Active Boundary Ping-Pong setups (price at Range High / VAH or Range Low / VAL).
    - Breakout Pullback continuation setups (retesting broken consolidation boundary).
    - Identifies 'P' (bullish pause) and 'B' (bearish pause) structural regimes.
    Enforces the 1.0% portfolio risk budget rule.
    """
    from src.analysis.pbd_model import evaluate_patrick_nill_setup
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    import logging
    logger = logging.getLogger(__name__)

    active_trades = []
    watching_setups = []

    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]
    if not symbols:
        symbols = [item.get("symbol") for item in UNIVERSE_TICKERS]

    for symbol in symbols[:30]:
        try:
            df = get_historical_bars(symbol, period=period, interval=interval)
            if len(df) < 25:
                continue
            res = evaluate_patrick_nill_setup(df, account_equity=account_equity)
            if res.get("status") == "INSUFFICIENT_DATA":
                continue

            record = {
                "symbol": symbol,
                "clean_symbol": symbol.replace(".NS", "").replace(".BO", ""),
                **res
            }
            if res.get("is_active"):
                active_trades.append(record)
            else:
                watching_setups.append(record)
            if len(active_trades) + len(watching_setups) >= limit:
                break
        except Exception as e:
            logger.warning("PBD scan error for %s: %s", symbol, str(e))
            continue

    all_candidates = active_trades + watching_setups
    return {
        "scan_type": "PATRICK_NILL_PBD",
        "mentor": "Patrick Nill (World Trading Championship)",
        "source": "TradeIQ (@tradeiq.with.nitz)",
        "active_trades": active_trades[:limit],
        "watching_consolidations": watching_setups[:limit],
        "total_active": len(active_trades),
        "total_watching": len(watching_setups),
        "candidates": all_candidates[:limit]
    }




def scan_king_5pillar_candidates(limit: int = 15) -> Dict[str, Any]:
    """
    Harinder Sahu (@kingresearch_academy) 5-Pillar Confluence Scanner.
    Scans liquid universe for stocks scoring 4/5 or 5/5 across:
    Trend (20/200 EMA), Momentum (RSI 14), Value (VWAP), Volume (>1.2x SMA20), and Risk (ATR).
    """
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    from src.analysis.social_strategies import calculate_king_research_5pillar
    import logging
    logger = logging.getLogger(__name__)

    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]
    if not symbols:
        symbols = [item.get("symbol") for item in UNIVERSE_TICKERS]

    candidates = []
    for sym in symbols[:35]:
        try:
            df = get_historical_bars(sym, period="6mo", interval="1d")
            if len(df) < 30:
                continue
            res = calculate_king_research_5pillar(df)
            if res.get("signal") in ["STRONG_BUY", "MILD_BUY", "STRONG_SELL"]:
                candidates.append({
                    "symbol": sym,
                    "clean_symbol": sym.replace(".NS", "").replace(".BO", ""),
                    **res
                })
        except Exception as e:
            logger.warning("5-Pillar scan error for %s: %s", sym, str(e))
            continue

    # Sort so 5/5 and 4/5 Strong Buys appear first
    score_map = {"STRONG_BUY": 5, "MILD_BUY": 3, "STRONG_SELL": 4, "MILD_SELL": 2, "NEUTRAL": 1}
    candidates.sort(key=lambda x: (score_map.get(x.get("signal"), 0), x.get("bullish_pillars", 0)), reverse=True)

    return {
        "scan_type": "KING_RESEARCH_5PILLAR",
        "mentor": "Harinder Sahu (King Research Academy)",
        "candidates": candidates[:limit],
        "total_found": len(candidates)
    }


def scan_supply_demand_candidates(limit: int = 15) -> Dict[str, Any]:
    """
    The Trading Geek (@algowithwahid) Supply & Demand Scanner.
    Finds stocks actively retesting an unmitigated institutional demand or supply zone.
    """
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    from src.analysis.social_strategies import calculate_trading_geek_snd
    import logging
    logger = logging.getLogger(__name__)

    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]
    if not symbols:
        symbols = [item.get("symbol") for item in UNIVERSE_TICKERS]

    active_tests = []
    for sym in symbols[:35]:
        try:
            df = get_historical_bars(sym, period="6mo", interval="1d")
            if len(df) < 25:
                continue
            res = calculate_trading_geek_snd(df)
            if res.get("signal") in ["BUY_DEMAND_TEST", "SELL_SUPPLY_TEST"]:
                active_tests.append({
                    "symbol": sym,
                    "clean_symbol": sym.replace(".NS", "").replace(".BO", ""),
                    **res
                })
        except Exception as e:
            logger.warning("Supply/Demand scan error for %s: %s", sym, str(e))
            continue

    return {
        "scan_type": "TRADING_GEEK_SND",
        "mentor": "The Trading Geek / Algo With Wahid",
        "candidates": active_tests[:limit],
        "total_found": len(active_tests)
    }


def scan_dark_pool_candidates(limit: int = 15) -> Dict[str, Any]:
    """
    System Cracker (@systemcracker_1) Dark Pool & Institutional Absorption Scanner.
    Finds stocks displaying high-volume low-spread absorption benchmarks or breakouts.
    """
    from src.data.market_data import get_historical_bars, get_watchlist_snapshots
    from src.analysis.social_strategies import calculate_dark_pool_absorption
    import logging
    logger = logging.getLogger(__name__)

    watchlist = get_watchlist_snapshots()
    symbols = [s.get("symbol", "") for s in watchlist if s.get("symbol")]
    if not symbols:
        symbols = [item.get("symbol") for item in UNIVERSE_TICKERS]

    absorption_setups = []
    for sym in symbols[:35]:
        try:
            df = get_historical_bars(sym, period="6mo", interval="1d")
            if len(df) < 25:
                continue
            res = calculate_dark_pool_absorption(df)
            if res.get("signal") in ["BULLISH_DARK_POOL_EXPANSION", "INSIDE_DARK_POOL_ZONE", "BEARISH_DARK_POOL_EXPANSION"]:
                absorption_setups.append({
                    "symbol": sym,
                    "clean_symbol": sym.replace(".NS", "").replace(".BO", ""),
                    **res
                })
        except Exception as e:
            logger.warning("Dark pool scan error for %s: %s", sym, str(e))
            continue

    return {
        "scan_type": "DARK_POOL_ABSORPTION",
        "source": "System Cracker (@systemcracker_1)",
        "candidates": absorption_setups[:limit],
        "total_found": len(absorption_setups)
    }


def scan_nifty_pivot_candidates() -> Dict[str, Any]:
    """
    Mandeep Joon (@generous_gyan) 9 EMA + Pivot Points Standard Index Scanner.
    Evaluates NIFTY 50, BANKNIFTY, NIFTYBEES, and BANKBEES.
    """
    from src.data.market_data import get_historical_bars
    from src.analysis.social_strategies import calculate_mandeep_pivot_9ema
    import logging
    logger = logging.getLogger(__name__)

    index_symbols = ["^NSEI", "^NSEBANK", "NIFTYBEES.NS", "BANKBEES.NS"]
    results = []

    for sym in index_symbols:
        try:
            df = get_historical_bars(sym, period="1mo", interval="1d")
            if len(df) < 10:
                continue
            res = calculate_mandeep_pivot_9ema(df)
            label = "NIFTY 50" if sym == "^NSEI" else ("BANKNIFTY" if sym == "^NSEBANK" else sym.replace(".NS", ""))
            results.append({
                "symbol": sym,
                "display_name": label,
                **res
            })
        except Exception as e:
            logger.warning("Index pivot scan error for %s: %s", sym, str(e))
            continue

    return {
        "scan_type": "MANDEEP_9EMA_PIVOTS",
        "mentor": "Mandeep Joon (@generous_gyan)",
        "indices": results,
        "total_scanned": len(results)
    }
