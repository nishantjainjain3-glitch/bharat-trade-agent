import math
from typing import Dict, Any, Optional

def evaluate_buffett(quote: Dict[str, Any], fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Warren Buffett Framework:
    - High & consistent Return on Equity (ROE >= 15%)
    - Conservative leverage (Debt-to-Equity <= 0.8)
    - Healthy operating/net profit margin (>= 12%)
    - Durable competitive advantage (Moat)
    """
    metrics = fundamentals.get("metrics", {})
    roe = metrics.get("roe_pct")
    de = metrics.get("debt_to_equity")
    margin = metrics.get("profit_margin_pct")
    pe = metrics.get("pe_ratio")

    score = 50
    pros = []
    cons = []

    # Check ROE
    if isinstance(roe, (int, float)) and roe > 0:
        if roe >= 20:
            score += 25
            pros.append(f"Outstanding ROE of {roe}% reflects high capital reinvestment efficiency.")
        elif roe >= 15:
            score += 15
            pros.append(f"Solid ROE of {roe}% meets the Berkshire 15% threshold.")
        else:
            score -= 15
            cons.append(f"ROE of {roe}% is below the 15% minimum quality hurdle.")
    else:
        cons.append("ROE data unavailable or negative.")

    # Check Debt
    if isinstance(de, (int, float)):
        if de <= 0.3:
            score += 15
            pros.append(f"Virtually debt-free balance sheet (Debt/Equity: {de}).")
        elif de <= 0.8:
            score += 5
            pros.append(f"Conservative debt profile (Debt/Equity: {de}).")
        else:
            score -= 20
            cons.append(f"Elevated financial leverage (Debt/Equity: {de}) increases solvency risk.")

    # Check Profit Margins
    if isinstance(margin, (int, float)) and margin > 0:
        if margin >= 15:
            score += 10
            pros.append(f"Wide profit margin of {margin}% confirms pricing power and moat.")
        elif margin < 8:
            score -= 10
            cons.append(f"Thin net profit margin ({margin}%) suggests commoditized business.")

    score = max(10, min(95, score))

    if score >= 75:
        verdict = "WIDE_MOAT_BUY"
        badge = "Wide Moat"
    elif score >= 60:
        verdict = "NARROW_MOAT"
        badge = "Narrow Moat"
    else:
        verdict = "NO_MOAT_PASS"
        badge = "No Economic Moat"

    rationale = (
        f"Warren Buffett criteria score: {score}/100. "
        + (" ".join(pros[:2]) if pros else "")
        + (" " + cons[0] if cons else "")
    )

    return {
        "persona": "Warren Buffett",
        "title": "Moat & Quality",
        "score": score,
        "verdict": verdict,
        "badge": badge,
        "rationale": rationale,
        "key_metric": f"ROE: {roe}% | D/E: {de}"
    }

def evaluate_graham(quote: Dict[str, Any], fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Benjamin Graham Framework (Intelligent Investor):
    - Price-to-Earnings <= 15
    - Price-to-Book <= 1.5 (or P/E * P/B <= 22.5)
    - Graham Number = sqrt(22.5 * EPS * BookValuePerShare)
    - Margin of Safety
    """
    price = quote.get("price", 0.0)
    metrics = fundamentals.get("metrics", {})
    pe = metrics.get("pe_ratio")
    pb = metrics.get("price_to_book")
    bv = metrics.get("book_value")
    eps = metrics.get("eps")

    score = 50
    graham_number = None
    margin_of_safety_pct = None
    pros = []
    cons = []

    # Calculate Graham Number if EPS & BV are positive
    if isinstance(eps, (int, float)) and isinstance(bv, (int, float)) and eps > 0 and bv > 0:
        graham_val = math.sqrt(22.5 * eps * bv)
        graham_number = round(graham_val, 2)
        if price > 0:
            mos = ((graham_number - price) / price) * 100.0
            margin_of_safety_pct = round(mos, 1)
            if mos > 20:
                score += 30
                pros.append(f"Graham Number of ₹{graham_number:,.2f} offers a +{margin_of_safety_pct}% margin of safety.")
            elif mos > 0:
                score += 15
                pros.append(f"Trading below Graham Number (₹{graham_number:,.2f}) with a +{margin_of_safety_pct}% discount.")
            else:
                score -= 20
                cons.append(f"Trading at a {abs(margin_of_safety_pct)}% premium above intrinsic Graham Number (₹{graham_number:,.2f}).")

    # Check P/E and P/B combination (Graham Rule: P/E * P/B <= 22.5)
    if isinstance(pe, (int, float)) and isinstance(pb, (int, float)) and pe > 0 and pb > 0:
        combo = pe * pb
        if combo <= 22.5:
            score += 15
            pros.append(f"P/E ({pe}) × P/B ({pb}) = {combo:.1f} strictly adheres to the 22.5 Graham product law.")
        else:
            score -= 15
            cons.append(f"P/E × P/B multiplier ({combo:.1f}) exceeds the conservative 22.5 threshold.")

    score = max(10, min(95, score))

    if score >= 75:
        verdict = "DEEP_VALUE"
        badge = "Margin of Safety"
    elif score >= 55:
        verdict = "FAIR_VALUE"
        badge = "Fairly Valued"
    else:
        verdict = "OVERVALUED"
        badge = "Expensive / Low Margin"

    rationale = (
        f"Benjamin Graham criteria score: {score}/100. "
        + (" ".join(pros[:2]) if pros else "")
        + (" " + cons[0] if cons else "")
    )

    return {
        "persona": "Benjamin Graham",
        "title": "Deep Value & Safety",
        "score": score,
        "verdict": verdict,
        "badge": badge,
        "graham_number": graham_number,
        "margin_of_safety_pct": margin_of_safety_pct,
        "rationale": rationale,
        "key_metric": f"Graham Fair Value: ₹{graham_number or 'N/A'}"
    }

def evaluate_lynch(quote: Dict[str, Any], fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Peter Lynch Framework (One Up On Wall Street):
    - PEG Ratio < 1.0 (Growth at a Reasonable Price)
    - Categorization: Fast Grower, Stalwart, or Cyclical
    - Earnings acceleration vs stock price
    """
    metrics = fundamentals.get("metrics", {})
    peg = metrics.get("peg_ratio")
    pe = metrics.get("pe_ratio")
    roe = metrics.get("roe_pct")

    score = 50
    pros = []
    cons = []

    # Check PEG Ratio
    if isinstance(peg, (int, float)) and peg > 0:
        if peg <= 0.8:
            score += 35
            pros.append(f"Exceptional PEG ratio of {peg} (well below 1.0 benchmark) indicates mispriced growth.")
        elif peg <= 1.2:
            score += 20
            pros.append(f"Healthy PEG ratio of {peg} offers Growth At a Reasonable Price (GARP).")
        else:
            score -= 20
            cons.append(f"Elevated PEG ratio of {peg} indicates valuation has outrun earnings expansion.")
    else:
        # Fallback estimation using P/E & ROE
        if isinstance(pe, (int, float)) and pe > 0 and pe < 20:
            score += 10
            pros.append(f"Moderate P/E of {pe} provides a reasonable growth foundation.")

    # Classify company
    if isinstance(roe, (int, float)) and roe >= 22:
        category = "Fast Grower"
    elif isinstance(pe, (int, float)) and pe < 15:
        category = "Stalwart / Value"
    else:
        category = "Core Compounder"

    score = max(10, min(95, score))

    if score >= 75:
        verdict = "STRONG_BUY_GARP"
        badge = f"Lynch Pick ({category})"
    elif score >= 55:
        verdict = "ACCUMULATE"
        badge = f"Stalwart ({category})"
    else:
        verdict = "HOLD_OVERPRICED"
        badge = "Fully Priced"

    rationale = (
        f"Peter Lynch criteria score: {score}/100 ({category}). "
        + (" ".join(pros[:2]) if pros else "")
        + (" " + cons[0] if cons else "")
    )

    return {
        "persona": "Peter Lynch",
        "title": "Growth At Reasonable Price",
        "score": score,
        "verdict": verdict,
        "badge": badge,
        "category": category,
        "rationale": rationale,
        "key_metric": f"PEG: {peg if isinstance(peg, (int, float)) else 'N/A'} | Class: {category}"
    }

def evaluate_all_investor_personas(quote: Dict[str, Any], fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """Runs all 3 investor frameworks and synthesizes a master guru consensus."""
    buffett = evaluate_buffett(quote, fundamentals)
    graham = evaluate_graham(quote, fundamentals)
    lynch = evaluate_lynch(quote, fundamentals)

    avg_score = round((buffett["score"] + graham["score"] + lynch["score"]) / 3.0, 1)

    if avg_score >= 70:
        consensus = "STRONG_GURU_CONSENSUS_BUY"
        summary = "Multiple legendary frameworks agree: company possesses strong profitability, durable economic moats, and sensible valuation."
    elif avg_score >= 55:
        consensus = "SELECTIVE_ACCUMULATION"
        summary = "Favorable quality characteristics, though valuation or growth rate requires selective entry on dips."
    else:
        consensus = "CAUTION_LOW_GURU_SCORE"
        summary = "Company fails multiple value and quality screens (stretched multiples, elevated leverage, or low ROE)."

    return {
        "buffett": buffett,
        "graham": graham,
        "lynch": lynch,
        "composite_guru_score": avg_score,
        "consensus_verdict": consensus,
        "consensus_summary": summary
    }
