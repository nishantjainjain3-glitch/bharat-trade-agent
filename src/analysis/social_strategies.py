"""
Social Media Trading Strategies Engine
Implements strategies discovered from top trading educators and creators:
1. Mamba FX (@algowithwahid) - 8/21 EMA Scalper & Breakout
2. Mandeep Joon (@generous_gyan) - 9 EMA + Pivot Points Standard
3. Harinder Sahu (@kingresearch_academy) - 5-Pillar Indicator Confluence (20/200 EMA, VWAP, RSI, Volume, ATR)
4. The Trading Geek (@algowithwahid) - Institutional Supply & Demand Zones
5. System Cracker (@systemcracker_1) - Dark Pool / Institutional Volume Absorption Detector
6. Nitya Tiwari (@tradeiq.with.nitz) - 9/21 EMA Dynamic Pullback System
7. Stock Burner (@daytradingguruji) - 9/20 EMA Crossover & 200 EMA Trend Filter
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


def calculate_mamba_fx_setup(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Mamba FX 8/21 EMA Scalper and Session Breakout setup.
    Fast EMA: 8, Slow EMA: 21.
    Breakout of recent 15-bar range confirmed by 8 > 21 EMA alignment.
    """
    if len(df) < 25:
        return {"strategy": "MAMBA_FX_SCALPER", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    high = df['High']
    low = df['Low']

    ema8 = close.ewm(span=8, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    curr_p = float(close.iloc[-1])
    curr_e8 = float(ema8.iloc[-1])
    curr_e21 = float(ema21.iloc[-1])
    prev_e8 = float(ema8.iloc[-2])
    prev_e21 = float(ema21.iloc[-2])

    range_high = float(high.iloc[-16:-1].max())
    range_low = float(low.iloc[-16:-1].min())

    is_bull_cross = prev_e8 <= prev_e21 and curr_e8 > curr_e21
    is_bear_cross = prev_e8 >= prev_e21 and curr_e8 < curr_e21
    is_range_breakout_up = curr_p > range_high and curr_e8 > curr_e21
    is_range_breakout_down = curr_p < range_low and curr_e8 < curr_e21

    if is_bull_cross or is_range_breakout_up:
        signal = "BUY"
        stop = round(curr_p - 1.5 * atr, 2)
        target = round(curr_p + 2.5 * atr, 2)
        reason = "8 EMA crossed above 21 EMA" if is_bull_cross else "Mamba 15-bar range breakout with 8 > 21 EMA"
    elif is_bear_cross or is_range_breakout_down:
        signal = "SELL"
        stop = round(curr_p + 1.5 * atr, 2)
        target = round(curr_p - 2.5 * atr, 2)
        reason = "8 EMA crossed below 21 EMA" if is_bear_cross else "Mamba 15-bar range breakdown with 8 < 21 EMA"
    else:
        signal = "HOLD"
        stop = target = None
        reason = "No active Mamba FX crossover or range breakout"

    return {
        "strategy": "MAMBA_FX_SCALPER",
        "signal": signal,
        "current_price": round(curr_p, 2),
        "ema8": round(curr_e8, 2),
        "ema21": round(curr_e21, 2),
        "range_high_15": round(range_high, 2),
        "range_low_15": round(range_low, 2),
        "stop_loss": stop,
        "target": target,
        "risk_reward": 1.67 if stop else 0.0,
        "reason": reason
    }


def calculate_mandeep_pivot_9ema(df: pd.DataFrame, prev_high: float = None,
                                 prev_low: float = None, prev_close: float = None) -> Dict[str, Any]:
    """
    Mandeep Joon (@generous_gyan) 9 EMA + Pivot Points Standard Strategy.
    P = (H + L + C) / 3
    R1 = 2P - L, S1 = 2P - H
    R2 = P + (H - L), S2 = P - (H - L)
    """
    if len(df) < 10:
        return {"strategy": "MANDEEP_9EMA_PIVOT", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    high = df['High']
    low = df['Low']
    open_p = df['Open']

    if prev_high is None or prev_low is None or prev_close is None:
        lookback = min(len(df) - 1, 75)
        ref_df = df.iloc[-lookback:-1]
        prev_high = float(ref_df['High'].max())
        prev_low = float(ref_df['Low'].min())
        prev_close = float(ref_df['Close'].iloc[-1])

    pp = (prev_high + prev_low + prev_close) / 3.0
    r1 = (2 * pp) - prev_low
    s1 = (2 * pp) - prev_high
    r2 = pp + (prev_high - prev_low)
    s2 = pp - (prev_high - prev_low)

    ema9 = close.ewm(span=9, adjust=False).mean()
    curr_c = float(close.iloc[-1])
    curr_o = float(open_p.iloc[-1])
    curr_e9 = float(ema9.iloc[-1])
    prev_c = float(close.iloc[-2])

    bullish_candle = curr_c > curr_o

    if prev_c <= pp and curr_c > pp and curr_c > curr_e9 and bullish_candle:
        signal = "BUY"
        entry = round(curr_c, 2)
        stop = round(min(pp * 0.998, curr_e9), 2)
        target = round(r1, 2)
        reason = "Candle closed above Pivot Point (P) and above 9 EMA"
    elif prev_c >= pp and curr_c < pp and curr_c < curr_e9 and not bullish_candle:
        signal = "SELL"
        entry = round(curr_c, 2)
        stop = round(max(pp * 1.002, curr_e9), 2)
        target = round(s1, 2)
        reason = "Candle closed below Pivot Point (P) and below 9 EMA"
    elif curr_c > s1 and float(low.iloc[-1]) <= s1 and curr_c > curr_e9 and bullish_candle:
        signal = "BUY"
        entry = round(curr_c, 2)
        stop = round(float(low.iloc[-1]) * 0.998, 2)
        target = round(pp, 2)
        reason = "S1 support bounce with close above 9 EMA"
    else:
        signal = "HOLD"
        entry = stop = target = None
        reason = "No clean 9 EMA + Pivot crossover"

    return {
        "strategy": "MANDEEP_9EMA_PIVOT",
        "signal": signal,
        "entry": entry,
        "stop_loss": stop,
        "target": target,
        "pivots": {
            "r2": round(r2, 2), "r1": round(r1, 2),
            "pp": round(pp, 2),
            "s1": round(s1, 2), "s2": round(s2, 2)
        },
        "ema9": round(curr_e9, 2),
        "current_price": round(curr_c, 2),
        "reason": reason
    }


def calculate_king_research_5pillar(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Harinder Sahu (@kingresearch_academy) 5-Pillar Confluence Framework.
    1. Trend: 20 & 200 EMA
    2. Momentum: RSI(14)
    3. Value: VWAP
    4. Volume: Volume > 1.2x SMA20
    5. Risk: Dynamic ATR
    """
    if len(df) < 30:
        return {"strategy": "KING_RESEARCH_5PILLAR", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume'] if 'Volume' in df.columns else pd.Series(1.0, index=df.index)

    curr_p = float(close.iloc[-1])

    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema_slow_span = 200 if len(df) >= 200 else 50
    ema_slow = float(close.ewm(span=ema_slow_span, adjust=False).mean().iloc[-1])
    trend_bullish = curr_p > ema20 > ema_slow
    trend_bearish = curr_p < ema20 < ema_slow

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi = float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0
    rsi_bullish = rsi >= 60.0
    rsi_bearish = rsi <= 40.0

    cum_vol = volume.cumsum()
    cum_vol_price = (volume * ((high + low + close) / 3.0)).cumsum()
    vwap = float((cum_vol_price / cum_vol.replace(0, 1)).iloc[-1])
    vwap_bullish = curr_p > vwap
    vwap_bearish = curr_p < vwap

    vol_ma = float(volume.tail(20).mean())
    curr_vol = float(volume.iloc[-1])
    vol_bullish = curr_vol >= vol_ma * 1.2

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    bull_score = sum([trend_bullish, rsi_bullish, vwap_bullish, vol_bullish, curr_p > ema20])
    bear_score = sum([trend_bearish, rsi_bearish, vwap_bearish, vol_bullish, curr_p < ema20])

    if bull_score >= 4:
        signal = "STRONG_BUY"
        stop = round(curr_p - 1.5 * atr, 2)
        target = round(curr_p + 3.0 * atr, 2)
    elif bear_score >= 4:
        signal = "STRONG_SELL"
        stop = round(curr_p + 1.5 * atr, 2)
        target = round(curr_p - 3.0 * atr, 2)
    elif bull_score >= 3:
        signal = "MILD_BUY"
        stop = round(curr_p - 1.5 * atr, 2)
        target = round(curr_p + 2.0 * atr, 2)
    elif bear_score >= 3:
        signal = "MILD_SELL"
        stop = round(curr_p + 1.5 * atr, 2)
        target = round(curr_p - 2.0 * atr, 2)
    else:
        signal = "NEUTRAL"
        stop = target = None

    return {
        "strategy": "KING_RESEARCH_5PILLAR",
        "signal": signal,
        "confluence_score": f"{max(bull_score, bear_score)}/5",
        "bullish_pillars": bull_score,
        "bearish_pillars": bear_score,
        "current_price": round(curr_p, 2),
        "ema20": round(ema20, 2),
        "ema200": round(ema_slow, 2),
        "vwap": round(vwap, 2),
        "rsi": round(rsi, 2),
        "atr": round(atr, 2),
        "volume_ratio": round(curr_vol / vol_ma, 2) if vol_ma > 0 else 1.0,
        "stop_loss": stop,
        "target": target
    }


def calculate_trading_geek_snd(df: pd.DataFrame) -> Dict[str, Any]:
    """
    The Trading Geek (@algowithwahid) Supply & Demand Zones.
    """
    if len(df) < 20:
        return {"strategy": "TRADING_GEEK_SND", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    demand_zones = []
    supply_zones = []

    for i in range(2, len(df) - 1):
        next_body = abs(close.iloc[i + 1] - open_p.iloc[i + 1])
        next_is_bull = close.iloc[i + 1] > open_p.iloc[i + 1]
        next_is_bear = close.iloc[i + 1] < open_p.iloc[i + 1]
        is_base = (high.iloc[i] - low.iloc[i]) <= (0.9 * atr)
        is_displacement = next_body >= (1.3 * atr)

        if is_base and is_displacement and next_is_bull:
            demand_zones.append({
                "bar_idx": i,
                "top": round(float(high.iloc[i]), 2),
                "bottom": round(float(low.iloc[i]), 2),
                "type": "DEMAND"
            })
        elif is_base and is_displacement and next_is_bear:
            supply_zones.append({
                "bar_idx": i,
                "top": round(float(high.iloc[i]), 2),
                "bottom": round(float(low.iloc[i]), 2),
                "type": "SUPPLY"
            })

    curr_p = float(close.iloc[-1])
    active_demand = [z for z in demand_zones if curr_p >= z['bottom']]
    active_supply = [z for z in supply_zones if curr_p <= z['top']]

    nearest_demand = active_demand[-1] if active_demand else None
    nearest_supply = active_supply[-1] if active_supply else None

    signal = "HOLD"
    stop = target = None
    if nearest_demand and (nearest_demand['bottom'] <= curr_p <= nearest_demand['top'] * 1.005):
        signal = "BUY_DEMAND_TEST"
        stop = round(nearest_demand['bottom'] - 0.5 * atr, 2)
        target = round(curr_p + 2.0 * atr, 2)
    elif nearest_supply and (nearest_supply['bottom'] * 0.995 <= curr_p <= nearest_supply['top']):
        signal = "SELL_SUPPLY_TEST"
        stop = round(nearest_supply['top'] + 0.5 * atr, 2)
        target = round(curr_p - 2.0 * atr, 2)

    return {
        "strategy": "TRADING_GEEK_SND",
        "signal": signal,
        "current_price": round(curr_p, 2),
        "nearest_demand": nearest_demand,
        "nearest_supply": nearest_supply,
        "total_demand_zones": len(demand_zones),
        "total_supply_zones": len(supply_zones),
        "stop_loss": stop,
        "target": target
    }


def calculate_dark_pool_absorption(df: pd.DataFrame) -> Dict[str, Any]:
    """
    System Cracker (@systemcracker_1) Dark Pool / Absorption Detector.
    """
    if len(df) < 25 or 'Volume' not in df.columns:
        return {"strategy": "DARK_POOL_ABSORPTION", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    vol_sma = volume.rolling(20).mean()
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    absorption_levels = []
    for i in range(len(df) - 20, len(df)):
        v_ratio = volume.iloc[i] / (vol_sma.iloc[i] + 1e-9)
        c_range = high.iloc[i] - low.iloc[i]
        curr_atr = atr.iloc[i]

        if v_ratio >= 2.2 and c_range <= (0.8 * curr_atr):
            bench_price = (high.iloc[i] + low.iloc[i]) / 2.0
            absorption_levels.append({
                "bar_idx": i,
                "price": round(float(bench_price), 2),
                "volume_ratio": round(float(v_ratio), 2),
                "high": round(float(high.iloc[i]), 2),
                "low": round(float(low.iloc[i]), 2)
            })

    curr_p = float(close.iloc[-1])
    recent_atr = float(atr.iloc[-1])

    if absorption_levels:
        latest = absorption_levels[-1]
        bench = latest['price']
        if curr_p > latest['high']:
            signal = "BULLISH_DARK_POOL_EXPANSION"
            stop = round(latest['low'] - 0.5 * recent_atr, 2)
            target = round(curr_p + 2.0 * recent_atr, 2)
        elif curr_p < latest['low']:
            signal = "BEARISH_DARK_POOL_EXPANSION"
            stop = round(latest['high'] + 0.5 * recent_atr, 2)
            target = round(curr_p - 2.0 * recent_atr, 2)
        else:
            signal = "INSIDE_DARK_POOL_ZONE"
            stop = target = None
    else:
        latest = None
        bench = None
        signal = "NO_RECENT_ABSORPTION"
        stop = target = None

    return {
        "strategy": "DARK_POOL_ABSORPTION",
        "signal": signal,
        "current_price": round(curr_p, 2),
        "dark_pool_benchmark": bench,
        "recent_absorption_event": latest,
        "total_absorption_events_found": len(absorption_levels),
        "stop_loss": stop,
        "target": target
    }


def calculate_tradeiq_9_21_ema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Nitya Tiwari (@tradeiq.with.nitz) 9/21 EMA Dynamic Pullback Strategy.
    """
    if len(df) < 25:
        return {"strategy": "TRADEIQ_9_21_EMA", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    curr_c = float(close.iloc[-1])
    curr_o = float(open_p.iloc[-1])
    curr_l = float(low.iloc[-1])
    curr_h = float(high.iloc[-1])
    curr_e9 = float(ema9.iloc[-1])
    curr_e21 = float(ema21.iloc[-1])

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    bull_trend = curr_e9 > curr_e21
    bear_trend = curr_e9 < curr_e21

    bull_pullback = curr_l <= curr_e9 and curr_c > curr_e9 and curr_c > curr_o and bull_trend
    bear_pullback = curr_h >= curr_e9 and curr_c < curr_e9 and curr_c < curr_o and bear_trend

    if bull_pullback:
        signal = "BUY_PULLBACK"
        stop = round(min(curr_l, curr_e21) - 0.2 * atr, 2)
        target = round(curr_c + 2.0 * (curr_c - stop), 2)
    elif bear_pullback:
        signal = "SELL_PULLBACK"
        stop = round(max(curr_h, curr_e21) + 0.2 * atr, 2)
        target = round(curr_c - 2.0 * (stop - curr_c), 2)
    elif bull_trend:
        signal = "BULLISH_TREND_WAITING_PULLBACK"
        stop = target = None
    elif bear_trend:
        signal = "BEARISH_TREND_WAITING_PULLBACK"
        stop = target = None
    else:
        signal = "CHOPPY"
        stop = target = None

    return {
        "strategy": "TRADEIQ_9_21_EMA",
        "signal": signal,
        "current_price": round(curr_c, 2),
        "ema9": round(curr_e9, 2),
        "ema21": round(curr_e21, 2),
        "stop_loss": stop,
        "target": target,
        "risk_reward": 2.0 if stop else 0.0
    }


def calculate_stock_burner_9_20(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Hardik Sharma (@daytradingguruji) Stock Burner 9/20 EMA Momentum & Retest.
    """
    if len(df) < 30:
        return {"strategy": "STOCK_BURNER_9_20", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    high = df['High']
    low = df['Low']

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    slow_span = 200 if len(df) >= 200 else 50
    ema_trend = close.ewm(span=slow_span, adjust=False).mean()

    curr_c = float(close.iloc[-1])
    curr_e9 = float(ema9.iloc[-1])
    curr_e20 = float(ema20.iloc[-1])
    curr_trend = float(ema_trend.iloc[-1])
    prev_e9 = float(ema9.iloc[-2])
    prev_e20 = float(ema20.iloc[-2])

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    bull_cross = prev_e9 <= prev_e20 and curr_e9 > curr_e20
    bear_cross = prev_e9 >= prev_e20 and curr_e9 < curr_e20
    above_trend = curr_c > curr_trend
    below_trend = curr_c < curr_trend

    if bull_cross and above_trend:
        signal = "BUY_CROSSOVER"
        stop = round(curr_e20 - 0.5 * atr, 2)
        target = round(curr_c + 1.8 * atr, 2)
        reason = f"9 EMA crossed above 20 EMA above {slow_span} EMA trend filter"
    elif bear_cross and below_trend:
        signal = "SELL_CROSSOVER"
        stop = round(curr_e20 + 0.5 * atr, 2)
        target = round(curr_c - 1.8 * atr, 2)
        reason = f"9 EMA crossed below 20 EMA below {slow_span} EMA trend filter"
    elif curr_e9 > curr_e20 and above_trend and float(low.iloc[-1]) <= curr_e20 and curr_c > curr_e9:
        signal = "BUY_RETEST"
        stop = round(curr_e20 - 0.5 * atr, 2)
        target = round(curr_c + 1.8 * atr, 2)
        reason = "20 EMA dynamic support retest with close above 9 EMA"
    else:
        signal = "HOLD"
        stop = target = None
        reason = "No active 9/20 EMA signal aligned with trend"

    return {
        "strategy": "STOCK_BURNER_9_20",
        "signal": signal,
        "current_price": round(curr_c, 2),
        "ema9": round(curr_e9, 2),
        "ema20": round(curr_e20, 2),
        "ema_trend": round(curr_trend, 2),
        "stop_loss": stop,
        "target": target,
        "reason": reason
    }
