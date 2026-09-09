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
            "trend": technicals["trend"]
        }
    except Exception as e:
        return None

def get_top_buy_recommendations(limit: int = 4) -> List[Dict[str, Any]]:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(scan_single_stock, item) for item in UNIVERSE_TICKERS]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    # Filter out AVOID / SELL
    candidates = [r for r in results if r["verdict"] in ["BUY", "ACCUMULATE"]]
    
    # Sort descending by score & conviction
    candidates.sort(key=lambda x: (x["verdict"] == "BUY", x["score"], x["conviction"]), reverse=True)
    return candidates[:limit]
