import pytest
import numpy as np
import pandas as pd
from src.analysis.institutional_quant import (
    calculate_fractional_kelly,
    calculate_volatility_parity_position,
    calculate_hurst_exponent,
    calculate_order_book_imbalance,
    check_portfolio_correlation_shield,
    calculate_twap_execution_schedule
)


def test_fractional_kelly_standard():
    # 55% win rate, 1:2 R:R (payoff = 2.0)
    # Edge = (0.55 * 2) - 0.45 = 1.10 - 0.45 = 0.65 > 0
    # Full Kelly = (0.55 * 3 - 1) / 2 = 0.65 / 2 = 0.325 (32.5%)
    # Quarter Kelly = 0.325 * 0.25 = 0.08125 -> 8.12% or 8.13%
    res = calculate_fractional_kelly(win_rate=0.55, win_loss_ratio=2.0, kelly_fraction=0.25, max_cap=0.10)
    assert res["is_positive_expectancy"] is True
    assert res["full_kelly"] == 32.5
    assert abs(res["fractional_kelly_pct"] - 8.125) < 0.02
    assert abs(res["recommended_allocation_pct"] - 8.125) < 0.02


def test_fractional_kelly_negative_expectancy():
    # 30% win rate, 1:1 R:R -> negative edge
    res = calculate_fractional_kelly(win_rate=0.30, win_loss_ratio=1.0)
    assert res["is_positive_expectancy"] is False
    assert res["recommended_allocation_pct"] == 0.0


def test_volatility_parity_position_sizing():
    # Capital: 50,000, Risk: 1.5% = 750 INR dollar risk budget
    # Current Price: 431.00, ATR: 12.45, Stop Multiplier: 1.5 -> Risk per share = round(1.5 * 12.45, 2) = 18.67
    # Shares = floor(750 / 18.67) = 40 shares
    res = calculate_volatility_parity_position(
        capital=50000.0,
        risk_pct=0.015,
        current_price=431.00,
        atr=12.45,
        stop_multiplier=1.5,
        target_multiplier=3.0
    )
    assert res["status"] == "CALCULATED"
    assert res["shares"] == 40
    assert res["dollar_risk_budget"] == 750.0
    assert res["actual_dollar_risk"] <= 750.0
    expected_risk_per_share = round(1.5 * 12.45, 2)
    assert res["stop_loss"] == round(431.00 - expected_risk_per_share, 2)
    assert res["target"] == round(431.00 + (3.0 * 12.45), 2)
    assert res["risk_reward_ratio"] == 2.0


def test_volatility_parity_invalid_inputs():
    res = calculate_volatility_parity_position(capital=0, risk_pct=0.01, current_price=100, atr=5)
    assert res["shares"] == 0
    assert res["status"] == "INVALID_INPUTS"


def test_hurst_exponent_trending_and_reverting():
    np.random.seed(42)
    trend_returns = 0.02 + np.random.normal(0, 0.005, 100)
    trend_prices = 100.0 * np.exp(np.cumsum(trend_returns))
    df_trend = pd.DataFrame({"Close": trend_prices})
    
    res_trend = calculate_hurst_exponent(df_trend)
    assert "hurst_exponent" in res_trend
    assert res_trend["sample_size"] == 99

    t = np.linspace(0, 20 * np.pi, 100)
    mr_prices = 100.0 + 10.0 * np.sin(t) + np.random.normal(0, 0.5, 100)
    df_mr = pd.DataFrame({"Close": mr_prices})
    res_mr = calculate_hurst_exponent(df_mr)
    assert res_mr["hurst_exponent"] < 0.55


def test_order_book_imbalance():
    bids = [{"price": 100.0, "quantity": 5000}, {"price": 99.5, "quantity": 3000}]
    asks = [{"price": 100.5, "quantity": 1000}, {"price": 101.0, "quantity": 1000}]
    # Total bid = 8000, Total ask = 2000, Total = 10000 -> OBI = 6000 / 10000 = +0.60
    res = calculate_order_book_imbalance(bids, asks)
    assert res["imbalance_ratio"] == 0.60
    assert res["signal"] == "BULLISH_LIQUIDITY_ACCUMULATION"
    assert res["spread"] == 0.50


def test_portfolio_correlation_shield():
    dates = pd.date_range("2026-01-01", periods=30)
    np.random.seed(42)
    base = np.random.normal(0, 0.02, 30)
    
    candidate = pd.Series(base + np.random.normal(0, 0.002, 30), index=dates)
    holding_a = pd.Series(base, index=dates)
    holding_b = pd.Series(np.random.normal(0, 0.02, 30), index=dates)
    
    holdings = {"HOLDING_A": holding_a, "HOLDING_B": holding_b}
    res = check_portfolio_correlation_shield(candidate, holdings, correlation_threshold=0.70)
    
    assert res["shield_pass"] is False
    assert res["highest_correlated_symbol"] == "HOLDING_A"
    assert res["highest_correlation"] > 0.85


def test_twap_execution_schedule():
    res = calculate_twap_execution_schedule(total_shares=100, num_slices=4, interval_minutes=15)
    assert res["total_shares"] == 100
    assert res["num_slices"] == 4
    assert len(res["slices"]) == 4
    total_sliced = sum(s["quantity"] for s in res["slices"])
    assert total_sliced == 100
