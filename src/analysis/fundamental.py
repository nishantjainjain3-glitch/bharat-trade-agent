from typing import Dict, Any, List

def evaluate_fundamentals(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    strengths: List[str] = []
    risks: List[str] = []
    
    pe = fundamentals.get("pe_ratio")
    forward_pe = fundamentals.get("forward_pe")
    peg = fundamentals.get("peg_ratio")
    pb = fundamentals.get("price_to_book")
    debt_equity = fundamentals.get("debt_to_equity")
    roe = fundamentals.get("roe")
    profit_margins = fundamentals.get("profit_margins")
    rev_growth = fundamentals.get("revenue_growth")
    
    # Valuation checks
    if pe is not None:
        if pe < 20:
            strengths.append(f"Moderate/Attractive valuation with P/E of {pe:.1f}")
        elif pe > 60:
            risks.append(f"High valuation premium with P/E of {pe:.1f}")
            
    if peg is not None:
        if 0 < peg <= 1.5:
            strengths.append(f"Attractive PEG ratio of {peg:.2f} relative to growth")
        elif peg > 2.5:
            risks.append(f"Elevated PEG ratio of {peg:.2f}")

    # Balance Sheet / Solvency
    if debt_equity is not None:
        # yfinance debtToEquity is usually in percentage (e.g. 50 = 0.5 D/E)
        d_e_ratio = debt_equity / 100.0 if debt_equity > 5 else debt_equity
        if d_e_ratio < 0.5:
            strengths.append(f"Low leverage: Debt-to-Equity is comfortable at {d_e_ratio:.2f}")
        elif d_e_ratio > 1.5:
            risks.append(f"High leverage: Debt-to-Equity is elevated at {d_e_ratio:.2f}")

    # Profitability / Quality
    if roe is not None:
        roe_pct = roe * 100.0 if roe < 1.0 else roe
        if roe_pct >= 15.0:
            strengths.append(f"Strong capital efficiency: ROE of {roe_pct:.1f}%")
        elif roe_pct < 8.0:
            risks.append(f"Weak capital return: ROE of {roe_pct:.1f}%")

    if profit_margins is not None:
        pm_pct = profit_margins * 100.0 if profit_margins < 1.0 else profit_margins
        if pm_pct >= 15.0:
            strengths.append(f"Healthy net margin of {pm_pct:.1f}%")
        elif pm_pct < 5.0:
            risks.append(f"Thin profit margins of {pm_pct:.1f}%")

    if rev_growth is not None:
        growth_pct = rev_growth * 100.0 if rev_growth < 1.0 else rev_growth
        if growth_pct > 12.0:
            strengths.append(f"Solid top-line expansion: Revenue growth of {growth_pct:.1f}%")
        elif growth_pct < 0.0:
            risks.append(f"Negative revenue growth of {growth_pct:.1f}%")

    score = len(strengths) - len(risks)
    if score >= 2:
        verdict = "STRONG_FUNDAMENTALS"
    elif score <= -2:
        verdict = "WEAK_FUNDAMENTALS"
    else:
        verdict = "BALANCED_FUNDAMENTALS"

    return {
        "verdict": verdict,
        "score": score,
        "metrics": {
            "pe_ratio": round(pe, 2) if pe else "N/A",
            "forward_pe": round(forward_pe, 2) if forward_pe else "N/A",
            "peg_ratio": round(peg, 2) if peg else "N/A",
            "price_to_book": round(pb, 2) if pb else "N/A",
            "roe_pct": round(roe * 100, 2) if roe else "N/A",
            "profit_margin_pct": round(profit_margins * 100, 2) if profit_margins else "N/A",
            "dividend_yield_pct": round(fundamentals.get("dividend_yield", 0) * 100, 2) if fundamentals.get("dividend_yield") else "N/A"
        },
        "strengths": strengths,
        "risks": risks
    }
