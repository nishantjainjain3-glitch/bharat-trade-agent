import pytest
from src.analysis.fundamental import evaluate_fundamentals

def test_breakout_fundamentals_elite():
    data = {
        "market_cap_crores": 15000.0,
        "roce_pct": 28.5,
        "roe": 0.22,
        "opm_pct": 19.5,
        "debt_to_equity": 0.05,
        "institutional_holding_pct": 22.5,
        "pe_ratio": 18.5,
        "sector": "Industrials"
    }
    res = evaluate_fundamentals(data)
    assert res["suitability"] == "ELITE_QUALITY_BREAKOUT"
    assert res["breakout_fundamental_score"] >= 80
    assert res["market_cap_category"] == "MID_CAP"

def test_breakout_fundamentals_banking_exemption():
    """Banks should not be penalized for customer deposits showing up as debt."""
    data = {
        "market_cap_crores": 22000.0,
        "roe": 0.14,
        "opm_pct": 45.0,
        "debt_to_equity": 7.5, # Normal for bank deposits
        "institutional_holding_pct": 45.0,
        "sector": "Financial Services",
        "industry": "Banks"
    }
    res = evaluate_fundamentals(data)
    assert res["market_cap_category"] == "LARGE_CAP"
    assert res["breakout_fundamental_score"] >= 60
    assert not any("elevated" in r.lower() for r in res["risks"])
