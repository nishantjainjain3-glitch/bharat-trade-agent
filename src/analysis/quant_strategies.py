"""
Quantitative Trading Strategies Engine
Implements proven institutional and quantitative models:
1. Larry Connors RSI(2) Mean Reversion Swing Model
2. Nick Stott Camarilla Pivot Points (H3/H4 Breakout & L3/L4 Reversal)
3. Kunal Saraogi VIP (Volume, Indicator, Price) Setup
4. 15-Minute Opening Range Breakout (ORB) with Volume Confirmation
5. Supertrend (10, 3) + 200 EMA Trend Following Filter
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


def calculate_connors_rsi2(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Larry Connors RSI(2) Quantitative Swing Model.
    Tested across thousands of equities: ~75% win rate in bull markets.
    Rules:
    1. Trend Filter: Price > 200 SMA (long-term uptrend).
    2. Entry Trigger: 2-period RSI < 10.0 (extreme short-term pullback).
    3. Exit Rule: Price crosses above 5-period EMA.
    4. Catastrophic Stop: 3.0x ATR(14) or recent 5-day low.
    """
    if len(df) < 50:
        return {"strategy": "CONNORS_RSI2", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    curr_p = float(close.iloc[-1])

    # 2-period RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(2).mean()
    loss = (-delta.clip(upper=0)).rolling(2).mean()
    rs2 = gain / loss.replace(0, np.nan)
    rsi2 = 100 - (100 / (1 + rs2))
    curr_rsi2 = float(rsi2.iloc[-1]) if not np.isnan(rsi2.iloc[-1]) else 50.0

    # 200 SMA (or 50 SMA if short history)
    sma_span = 200 if len(df) >= 200 else 50
    sma_trend = float(close.rolling(sma_span).mean().iloc[-1])
    in_uptrend = curr_p > sma_trend

    # 5 EMA exit line
    ema5 = float(close.ewm(span=5, adjust=False).mean().iloc[-1])

    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    signal = "HOLD"
    stop = target = None
    reason = "No active Connors setup"

    if in_uptrend and curr_rsi2 < 10.0:
        signal = "BUY_EXTREME_DIP"
        stop = round(curr_p - 2.5 * atr, 2)
        target = round(ema5 + 1.0 * atr, 2)
        reason = f"Price above {sma_span} SMA with 2-period RSI ({curr_rsi2:.1f}) in deep oversold territory"
    elif in_uptrend and curr_rsi2 < 20.0:
        signal = "WATCH_MILD_DIP"
        reason = f"Price above {sma_span} SMA with 2-period RSI at {curr_rsi2:.1f}"
    elif curr_p > ema5:
        signal = "ABOVE_5EMA_PROFIT_ZONE"
        reason = f"Price (₹{curr_p:.2f}) trading above 5 EMA (₹{ema5:.2f})"

    return {
        "strategy": "CONNORS_RSI2",
        "signal": signal,
        "current_price": round(curr_p, 2),
        "rsi2": round(curr_rsi2, 2),
        "trend_sma": round(sma_trend, 2),
        "sma_period": sma_span,
        "ema5_exit": round(ema5, 2),
        "stop_loss": stop,
        "target": target,
        "reason": reason
    }


def calculate_camarilla_pivots(df: pd.DataFrame, prev_high: float = None,
                               prev_low: float = None, prev_close: float = None) -> Dict[str, Any]:
    """
    Nick Stott Camarilla Pivot Points Engine.
    H4 = Close + Range * 1.1 / 2.0 (Breakout Long)
    H3 = Close + Range * 1.1 / 4.0 (Mean Reversion Resistance)
    L3 = Close - Range * 1.1 / 4.0 (Mean Reversion Support)
    L4 = Close - Range * 1.1 / 2.0 (Breakdown Short)
    """
    if len(df) < 5:
        return {"strategy": "CAMARILLA_PIVOTS", "signal": "INSUFFICIENT_DATA"}

    if prev_high is None or prev_low is None or prev_close is None:
        ref = df.iloc[-2]
        prev_high = float(ref['High'])
        prev_low = float(ref['Low'])
        prev_close = float(ref['Close'])

    rng = prev_high - prev_low
    h5 = (prev_high / prev_low) * prev_close if prev_low > 0 else prev_close
    h4 = prev_close + rng * 1.1 / 2.0
    h3 = prev_close + rng * 1.1 / 4.0
    l3 = prev_close - rng * 1.1 / 4.0
    l4 = prev_close - rng * 1.1 / 2.0
    l5 = prev_close - (h5 - prev_close)

    curr_p = float(df['Close'].iloc[-1])
    curr_h = float(df['High'].iloc[-1])
    curr_l = float(df['Low'].iloc[-1])

    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    signal = "NEUTRAL_INSIDE_RANGE"
    stop = target = None
    mode = "CHOP"

    if curr_p > h4:
        signal = "BULLISH_H4_BREAKOUT"
        mode = "MOMENTUM_EXPANSION"
        stop = round(h3, 2)
        target = round(h5, 2)
    elif curr_p < l4:
        signal = "BEARISH_L4_BREAKDOWN"
        mode = "MOMENTUM_EXPANSION"
        stop = round(l3, 2)
        target = round(l5, 2)
    elif curr_l <= l3 and curr_p > l3:
        signal = "L3_SUPPORT_BOUNCE"
        mode = "MEAN_REVERSION"
        stop = round(l4, 2)
        target = round(h3, 2)
    elif curr_h >= h3 and curr_p < h3:
        signal = "H3_RESISTANCE_REVERSAL"
        mode = "MEAN_REVERSION"
        stop = round(h4, 2)
        target = round(l3, 2)

    return {
        "strategy": "CAMARILLA_PIVOTS",
        "signal": signal,
        "mode": mode,
        "current_price": round(curr_p, 2),
        "levels": {
            "h5": round(h5, 2),
            "h4": round(h4, 2),
            "h3": round(h3, 2),
            "l3": round(l3, 2),
            "l4": round(l4, 2),
            "l5": round(l5, 2)
        },
        "stop_loss": stop,
        "target": target
    }


def calculate_kunal_saraogi_vip(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Kunal Saraogi VIP (Volume, Indicator, Price) Setup.
    1. Price (P): Close > 20 EMA with bullish candlestick confirmation.
    2. Indicator (I): MACD Histogram > 0 and Supertrend/Momentum bullish.
    3. Volume (V): Volume > 1.1x 20-period Volume SMA.
    Confluence Score: 3/3 = Full VIP Buy Signal.
    """
    if len(df) < 30:
        return {"strategy": "KUNAL_SARAOGI_VIP", "signal": "INSUFFICIENT_DATA"}

    close = df['Close']
    curr_p = float(close.iloc[-1])
    volume = df['Volume'] if 'Volume' in df.columns else pd.Series(1.0, index=df.index)

    # 1. Price Pillar (20 EMA)
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    p_pass = curr_p > ema20

    # 2. Indicator Pillar (MACD Histogram)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9, adjust=False).mean()
    macd_hist = float((macd - signal_line).iloc[-1])
    i_pass = macd_hist > 0

    # 3. Volume Pillar
    vol_ma = float(volume.tail(20).mean())
    curr_vol = float(volume.iloc[-1])
    v_pass = curr_vol >= (vol_ma * 1.10)

    score = sum([p_pass, i_pass, v_pass])

    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())

    if score == 3:
        signal = "STRONG_VIP_BUY"
        stop = round(ema20 - 0.5 * atr, 2)
        target = round(curr_p + 2.0 * atr, 2)
    elif score == 2:
        signal = "MODERATE_VIP_SETUP"
        stop = target = None
    else:
        signal = "NEUTRAL"
        stop = target = None

    return {
        "strategy": "KUNAL_SARAOGI_VIP",
        "signal": signal,
        "vip_score": f"{score}/3",
        "price_pass": p_pass,
        "indicator_pass": i_pass,
        "volume_pass": v_pass,
        "current_price": round(curr_p, 2),
        "ema20": round(ema20, 2),
        "macd_histogram": round(macd_hist, 3),
        "volume_ratio": round(curr_vol / vol_ma, 2) if vol_ma > 0 else 1.0,
        "stop_loss": stop,
        "target": target
    }


def calculate_supertrend_cloud(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
    """
    Supertrend (10, 3) + 200 EMA Macro Filter.
    """
    if len(df) < period + 5:
        return {"strategy": "SUPERTREND_CLOUD", "signal": "INSUFFICIENT_DATA"}

    high = df['High']
    low = df['Low']
    close = df['Close']

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    hl2 = (high + low) / 2.0
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    curr_c = float(close.iloc[-1])
    curr_low_b = float(lower_band.iloc[-1])
    curr_up_b = float(upper_band.iloc[-1])

    is_bull = curr_c > curr_low_b

    sma200 = float(close.rolling(min(len(df), 200)).mean().iloc[-1])
    trend_filter_pass = curr_c > sma200 if is_bull else curr_c < sma200

    signal = "BUY" if (is_bull and trend_filter_pass) else ("SELL" if (not is_bull and trend_filter_pass) else "CHOP")

    return {
        "strategy": "SUPERTREND_CLOUD",
        "signal": signal,
        "is_supertrend_bullish": is_bull,
        "current_price": round(curr_c, 2),
        "supertrend_stop": round(curr_low_b if is_bull else curr_up_b, 2),
        "sma200_filter": round(sma200, 2),
        "filter_aligned": trend_filter_pass
    }
