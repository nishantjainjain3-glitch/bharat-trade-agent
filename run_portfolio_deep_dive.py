import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, '.')

from src.broker.angel_one import angel_client
from src.data.market_data import get_historical_bars, normalize_indian_symbol
from src.analysis.technical import analyze_technical_indicators
from src.analysis.order_flow import analyze_order_flow
from src.analysis.fundamental import evaluate_fundamentals

def run_deep_dive():
    summary = angel_client.get_portfolio_summary()
    holdings = summary.get("holdings", [])
    total_val = summary.get("total_portfolio_value", 50889.09)
    total_invested = summary.get("invested_amount", 50100.43)
    cash = summary.get("available_cash", 64.66)
    
    print(f"Portfolio Total Value: INR {total_val}")
    print(f"Total Invested: INR {total_invested}")
    print(f"Available Cash: INR {cash}")
    print(f"Total Holdings: {len(holdings)}\n")
    
    results = []
    
    for h in holdings:
        raw_sym = h.get("tradingsymbol", "")
        clean_sym = raw_sym.replace("-EQ", "").strip().upper()
        qty = int(h.get("quantity", 0))
        avg_price = float(h.get("averageprice", 0.0))
        ltp = float(h.get("ltp", 0.0))
        invested = round(avg_price * qty, 2)
        current_val = round(ltp * qty, 2)
        pnl = float(h.get("profitandloss", h.get("pnl", 0.0)))
        pnl_pct = float(h.get("pnlpercentage", h.get("pnl_pct", 0.0)))
        weight_pct = round((current_val / total_val) * 100.0, 2) if total_val > 0 else 0.0
        
        try:
            # 1 year data to get reliable 200 EMA
            df = get_historical_bars(clean_sym, period="1y", interval="1d")
            tech = analyze_technical_indicators(df)
            of = analyze_order_flow(df)
            
            # Fundamentals
            try:
                fund = evaluate_fundamentals(clean_sym)
            except Exception:
                fund = {"score": 50, "rating": "NEUTRAL"}
                
            ema_200 = tech["emas"]["ema_200"]
            ema_50 = tech["emas"]["ema_50"]
            ema_20 = tech["emas"]["ema_20"]
            rsi = tech["rsi"]
            adx = tech["adx"]["adx"]
            adx_bias = tech["adx"]["directional_bias"]
            supertrend_dir = tech["volatility_regime"]["supertrend"]["direction"]
            supertrend_stop = tech["volatility_regime"]["supertrend"]["supertrend_price"]
            cpr_pos = tech["cpr"]["price_position"]
            order_flow_verdict = of.get("verdict", "NEUTRAL")
            order_flow_score = of.get("order_flow_score", 50)
            
            # Keep vs Remove Logic:
            # Criteria for KEEP:
            # - Trading above 200 EMA AND Supertrend BULLISH
            # - Positive momentum / accumulation
            # Criteria for REMOVE / EXIT:
            # - Trading below 200 EMA AND Supertrend BEARISH
            # - Severe drawdown with broken structure / distribution
            # Criteria for HOLD / TIGHT STOP:
            # - Mixed signals (e.g. above 200 EMA but pullback, or high profit runner)
            
            above_200 = ltp >= ema_200
            above_50 = ltp >= ema_50
            bullish_st = (supertrend_dir == "BULLISH")
            
            if above_200 and bullish_st:
                verdict = "KEEP"
                action = "Hold & Ride Trend"
            elif (not above_200) and (not bullish_st):
                verdict = "REMOVE"
                action = "Exit / Reallocate"
            elif above_200 and not bullish_st:
                verdict = "HOLD"
                action = "Watch 200 EMA Support"
            elif (not above_200) and bullish_st:
                verdict = "TRIM"
                action = "Sell on Pullback / Relief Rally"
            else:
                verdict = "HOLD"
                action = "Review"

            # Special case for odd lots (quantity = 1)
            # If quantity == 1 and total position value < 300 INR, it's portfolio clutter unless it's a core conviction
            is_odd_lot = (qty == 1 and current_val < 500)
            
            item = {
                "symbol": clean_sym,
                "quantity": qty,
                "avg_price": avg_price,
                "ltp": ltp,
                "invested": invested,
                "current_value": current_val,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "portfolio_weight_pct": weight_pct,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "ema_200": ema_200,
                "above_200_ema": above_200,
                "above_50_ema": above_50,
                "rsi": rsi,
                "adx": adx,
                "adx_bias": adx_bias,
                "supertrend_dir": supertrend_dir,
                "supertrend_stop": supertrend_stop,
                "cpr_position": cpr_pos,
                "order_flow_verdict": order_flow_verdict,
                "order_flow_score": order_flow_score,
                "verdict": verdict,
                "action": action,
                "is_odd_lot": is_odd_lot,
                "support": tech["levels"]["support"],
                "resistance": tech["levels"]["resistance"],
                "bullish_factors": tech["bullish_factors"],
                "bearish_factors": tech["bearish_factors"]
            }
            results.append(item)
            print(f"Processed {clean_sym}: {verdict} ({action}) | LTP: {ltp} | 200 EMA: {ema_200} | ST: {supertrend_dir} | PnL: {pnl_pct}%")
        except Exception as ex:
            print(f"Error processing {clean_sym}: {ex}")
            
    with open("portfolio_analysis_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved deep dive results to portfolio_analysis_report.json")

if __name__ == "__main__":
    run_deep_dive()
