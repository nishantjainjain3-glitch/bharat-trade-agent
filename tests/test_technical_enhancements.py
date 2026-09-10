import pytest
import pandas as pd
import numpy as np
from src.analysis.technical import (
    calculate_adx,
    calculate_cpr,
    calculate_stoch_rsi,
    detect_candlestick_patterns,
    analyze_technical_indicators
)

def create_synthetic_bars(n=40, trend="up"):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    base = 100.0
    data = []
    for i in range(n):
        if trend == "up":
            base += 1.5 + (i * 0.1)
        elif trend == "down":
            base -= 1.5 + (i * 0.1)
        else:
            base += np.sin(i) * 0.5
        o = base - 0.5
        c = base + 0.8
        h = max(o, c) + 1.0
        l = min(o, c) - 0.8
        data.append({"Date": dates[i], "Open": o, "High": h, "Low": l, "Close": c, "Volume": 10000 + i * 200})
    return pd.DataFrame(data)

def test_calculate_adx():
    df = create_synthetic_bars(n=50, trend="up")
    adx_res = calculate_adx(df, 14)
    assert "adx" in adx_res
    assert "plus_di" in adx_res
    assert "minus_di" in adx_res
    assert "trend_strength" in adx_res
    assert "is_trending" in adx_res
    assert adx_res["directional_bias"] in ["BULLISH", "BEARISH", "NEUTRAL"]

def test_calculate_cpr():
    df = create_synthetic_bars(n=10)
    cpr_res = calculate_cpr(df)
    assert "pivot" in cpr_res
    assert "tc" in cpr_res
    assert "bc" in cpr_res
    assert "width_pct" in cpr_res
    assert "regime" in cpr_res
    assert "price_position" in cpr_res
    assert cpr_res["pivot"] > 0

def test_calculate_stoch_rsi():
    close = pd.Series(np.linspace(100, 150, 40))
    stoch = calculate_stoch_rsi(close, 14, 14, 3, 3)
    assert "k" in stoch
    assert "d" in stoch
    assert "status" in stoch

def test_expanded_candlestick_patterns():
    # Shooting star: small lower body, high upper shadow
    data = [
        {"Open": 100.0, "High": 102.0, "Low": 99.0, "Close": 101.0},
        {"Open": 101.0, "High": 110.0, "Low": 100.5, "Close": 101.2}  # long upper shadow
    ]
    df_star = pd.DataFrame(data)
    patterns = detect_candlestick_patterns(df_star)
    assert any("Shooting Star" in p for p in patterns)

    # Bearish Engulfing: prior green, current red and engulfs
    data2 = [
        {"Open": 100.0, "High": 103.0, "Low": 99.5, "Close": 102.5},  # green
        {"Open": 103.0, "High": 103.5, "Low": 98.0, "Close": 99.0}   # red engulfs
    ]
    df_engulf = pd.DataFrame(data2)
    patterns2 = detect_candlestick_patterns(df_engulf)
    assert any("Bearish Engulfing" in p for p in patterns2)

def test_analyze_technical_indicators_includes_new_measures():
    df = create_synthetic_bars(n=45, trend="up")
    res = analyze_technical_indicators(df)
    assert "adx" in res
    assert "cpr" in res
    assert "stoch_rsi" in res
    assert "candlestick_patterns" in res
    assert "trend" in res
    assert "score" in res
