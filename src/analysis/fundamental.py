from typing import Dict, Any, List, Optional

def evaluate_fundamentals(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates corporate fundamentals specifically for breakout trading candidates.
    Assesses Market Cap, ROE, ROCE, Operating Profit Margin (OPM),
    Debt-to-Equity, and Institutional Sponsorship.
    """
    strengths: List[str] = []
    risks: List[str] = []
    
    pe = fundamentals.get("pe_ratio")
    forward_pe = fundamentals.get("forward_pe")
    peg = fundamentals.get("peg_ratio")
    pb = fundamentals.get("price_to_book")
    debt_equity = fundamentals.get("debt_to_equity")
    roe = fundamentals.get("roe")
    roce = fundamentals.get("roce_pct")
    opm = fundamentals.get("opm_pct")
    profit_margins = fundamentals.get("profit_margins")
    rev_growth = fundamentals.get("revenue_growth")
    mcap_cr = fundamentals.get("market_cap_crores")
    inst_holding = fundamentals.get("institutional_holding_pct")
    sector = str(fundamentals.get("sector", "")).lower()
    industry = str(fundamentals.get("industry", "")).lower()
    is_financial = "financial" in sector or "bank" in industry or "nbfc" in industry

    # 1. Market Cap Categorization (SEBI Indian Market definitions)
    if mcap_cr is not None and mcap_cr > 0:
        if mcap_cr >= 20000.0:
            mcap_category = "LARGE_CAP"
            strengths.append(f"High liquidity Large-Cap institutional profile (Market Cap: Rs {mcap_cr:,.1f} Cr)")
        elif mcap_cr >= 5000.0:
            mcap_category = "MID_CAP"
            strengths.append(f"High growth Mid-Cap sweet spot (Market Cap: Rs {mcap_cr:,.1f} Cr)")
        else:
            mcap_category = "SMALL_CAP"
            risks.append(f"Small-Cap liquidity risk (Market Cap: Rs {mcap_cr:,.1f} Cr)")
    else:
        mcap_category = "UNKNOWN"

    # 2. ROCE (Return on Capital Employed) — Crucial for manufacturing, engineering, Capex
    roce_score = 15
    if roce is not None and roce > 0:
        if roce >= 25.0:
            strengths.append(f"Superb capital productivity: ROCE of {roce:.1f}%")
            roce_score = 25
        elif roce >= 15.0:
            strengths.append(f"Solid capital return: ROCE of {roce:.1f}%")
            roce_score = 20
        elif roce < 8.0 and not is_financial:
            risks.append(f"Poor capital productivity: ROCE is low at {roce:.1f}%")
            roce_score = 5

    # 3. ROE (Return on Equity)
    roe_score = 10
    if roe is not None:
        roe_pct = roe * 100.0 if roe < 1.0 else roe
        if roe_pct >= 20.0:
            strengths.append(f"Exceptional compounder: ROE of {roe_pct:.1f}%")
            roe_score = 20
        elif roe_pct >= 14.0:
            strengths.append(f"Healthy return on equity: ROE of {roe_pct:.1f}%")
            roe_score = 15
        elif roe_pct < 8.0:
            risks.append(f"Weak capital return: ROE of {roe_pct:.1f}%")
            roe_score = 5
    else:
        roe_pct = None

    # 4. OPM (Operating Profit Margin / EBITDA Margin)
    opm_score = 10
    if opm is not None and opm > 0:
        if opm >= 18.0:
            strengths.append(f"Strong pricing power & moat: Operating Profit Margin (OPM) of {opm:.1f}%")
            opm_score = 20
        elif opm >= 10.0:
            strengths.append(f"Decent operational profitability: OPM of {opm:.1f}%")
            opm_score = 15
        elif opm < 6.0:
            risks.append(f"Thin operational cushion: OPM is low at {opm:.1f}%")
            opm_score = 5

    # 5. Balance Sheet & Solvency (Debt-to-Equity)
    de_score = 15
    d_e_ratio = None
    if debt_equity is not None:
        d_e_ratio = debt_equity / 100.0 if debt_equity > 5 else debt_equity
        if is_financial:
            strengths.append(f"Financial institution model: leverage of {d_e_ratio:.2f}x supported by customer deposits")
            de_score = 18
        else:
            if d_e_ratio <= 0.05:
                strengths.append(f"Virtually debt-free balance sheet: D/E of {d_e_ratio:.2f}")
                de_score = 20
            elif d_e_ratio <= 0.5:
                strengths.append(f"Prudent low leverage: D/E of {d_e_ratio:.2f}")
                de_score = 18
            elif d_e_ratio > 1.2:
                risks.append(f"High balance sheet leverage: D/E is elevated at {d_e_ratio:.2f}")
                de_score = 5

    # 6. Institutional Ownership (FII / DII Sponsorship)
    inst_score = 10
    if inst_holding is not None and inst_holding > 0:
        if inst_holding >= 20.0:
            strengths.append(f"Strong institutional sponsorship: {inst_holding:.1f}% held by FIIs/DIIs")
            inst_score = 15
        elif inst_holding >= 10.0:
            strengths.append(f"Solid institutional presence: {inst_holding:.1f}% held by institutions")
            inst_score = 12
        elif inst_holding < 5.0:
            risks.append(f"Low institutional interest: only {inst_holding:.1f}% institutional holding")
            inst_score = 5

    # 7. Valuation & Growth Checks
    if pe is not None:
        if pe < 20:
            strengths.append(f"Moderate valuation: P/E of {pe:.1f}")
        elif pe > 65:
            risks.append(f"High valuation premium: P/E of {pe:.1f}")
            
    if peg is not None:
        if 0 < peg <= 1.5:
            strengths.append(f"Attractive PEG ratio of {peg:.2f}")
        elif peg > 2.5:
            risks.append(f"Elevated PEG ratio of {peg:.2f}")

    if rev_growth is not None:
        growth_pct = rev_growth * 100.0 if rev_growth < 1.0 else rev_growth
        if growth_pct > 12.0:
            strengths.append(f"Solid top-line expansion: Revenue growth of {growth_pct:.1f}%")
        elif growth_pct < 0.0:
            risks.append(f"Negative revenue contraction of {growth_pct:.1f}%")

    # Composite Breakout Fundamental Quality Score (0 to 100)
    composite_score = min(100, roce_score + roe_score + opm_score + de_score + inst_score)

    if composite_score >= 80:
        suitability = "ELITE_QUALITY_BREAKOUT"
        verdict = "STRONG_FUNDAMENTALS"
    elif composite_score >= 60:
        suitability = "SOLID_CANDIDATE"
        verdict = "BALANCED_FUNDAMENTALS"
    elif composite_score >= 45:
        suitability = "AVERAGE_SPECULATIVE"
        verdict = "BALANCED_FUNDAMENTALS"
    else:
        suitability = "WEAK_AVOID"
        verdict = "WEAK_FUNDAMENTALS"

    return {
        "verdict": verdict,
        "suitability": suitability,
        "breakout_fundamental_score": composite_score,
        "market_cap_category": mcap_category,
        "score": len(strengths) - len(risks),
        "metrics": {
            "market_cap_crores": round(mcap_cr, 2) if mcap_cr else "N/A",
            "roe_pct": round(roe_pct, 2) if roe_pct is not None else "N/A",
            "roce_pct": round(roce, 2) if roce is not None else "N/A",
            "opm_pct": round(opm, 2) if opm is not None else "N/A",
            "debt_to_equity": round(d_e_ratio, 2) if d_e_ratio is not None else "N/A",
            "institutional_holding_pct": round(inst_holding, 2) if inst_holding is not None else "N/A",
            "pe_ratio": round(pe, 2) if pe else "N/A",
            "forward_pe": round(forward_pe, 2) if forward_pe else "N/A",
            "peg_ratio": round(peg, 2) if peg else "N/A",
            "price_to_book": round(pb, 2) if pb else "N/A",
            "profit_margin_pct": round(profit_margins * 100, 2) if profit_margins else "N/A",
            "dividend_yield_pct": round(fundamentals.get("dividend_yield", 0) * 100, 2) if fundamentals.get("dividend_yield") else "N/A"
        },
        "strengths": strengths,
        "risks": risks
    }
