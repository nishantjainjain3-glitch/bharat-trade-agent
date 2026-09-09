import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def detect_fair_value_gaps(df: pd.DataFrame, min_gap_pct: float = 0.05) -> Dict[str, Any]:
    """
    Identifies bullish and bearish Fair Value Gaps (FVG) / Liquidity Imbalances.
    - Bullish FVG: Bar[i-2].High < Bar[i].Low (unfilled void in Bar[i-1])
    - Bearish FVG: Bar[i-2].Low > Bar[i].High (unfilled void in Bar[i-1])
    Tracks mitigation status across subsequent candles.
    """
    if len(df) < 3 or not all(col in df.columns for col in ['High', 'Low', 'Close']):
        return {"bullish_fvgs": [], "bearish_fvgs": [], "active_count": 0, "status": "INSUFFICIENT_DATA"}

    bullish_fvgs = []
    bearish_fvgs = []
    n = len(df)

    for i in range(2, n):
        c_prev2_high = float(df['High'].iloc[i - 2])
        c_prev2_low = float(df['Low'].iloc[i - 2])
        c_curr_high = float(df['High'].iloc[i])
        c_curr_low = float(df['Low'].iloc[i])
        c_mid_close = float(df['Close'].iloc[i - 1])

        # Bullish FVG: High of candle i-2 is strictly less than Low of candle i
        if c_curr_low > c_prev2_high:
            gap_size = c_curr_low - c_prev2_high
            gap_pct = (gap_size / c_mid_close) * 100.0 if c_mid_close > 0 else 0.0
            if gap_pct >= min_gap_pct:
                mitigated = False
                # Check subsequent bars for fill/mitigation
                for j in range(i + 1, n):
                    subsequent_low = float(df['Low'].iloc[j])
                    if subsequent_low <= c_prev2_high:
                        mitigated = True
                        break
                bullish_fvgs.append({
                    "candle_index": int(i - 1),
                    "top": round(c_curr_low, 2),
                    "bottom": round(c_prev2_high, 2),
                    "size_pct": round(gap_pct, 2),
                    "mitigated": mitigated
                })

        # Bearish FVG: Low of candle i-2 is strictly greater than High of candle i
        elif c_prev2_low > c_curr_high:
            gap_size = c_prev2_low - c_curr_high
            gap_pct = (gap_size / c_mid_close) * 100.0 if c_mid_close > 0 else 0.0
            if gap_pct >= min_gap_pct:
                mitigated = False
                for j in range(i + 1, n):
                    subsequent_high = float(df['High'].iloc[j])
                    if subsequent_high >= c_prev2_low:
                        mitigated = True
                        break
                bearish_fvgs.append({
                    "candle_index": int(i - 1),
                    "top": round(c_prev2_low, 2),
                    "bottom": round(c_curr_high, 2),
                    "size_pct": round(gap_pct, 2),
                    "mitigated": mitigated
                })

    active_bullish = [f for f in bullish_fvgs if not f["mitigated"]]
    active_bearish = [f for f in bearish_fvgs if not f["mitigated"]]

    return {
        "bullish_fvgs": bullish_fvgs[-10:],
        "bearish_fvgs": bearish_fvgs[-10:],
        "active_bullish_count": len(active_bullish),
        "active_bearish_count": len(active_bearish),
        "bias": "BULLISH" if len(active_bullish) > len(active_bearish) else ("BEARISH" if len(active_bearish) > len(active_bullish) else "NEUTRAL")
    }

def detect_market_structure(df: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
    """
    Detects market swing highs/lows, Break of Structure (BoS), and Change of Character (CHoCH).
    """
    if len(df) < (window * 2 + 3):
        return {"trend": "NEUTRAL", "bos": None, "choch": None, "recent_swings": []}

    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        # Local peak
        if highs[i] == max(highs[i - window : i + window + 1]):
            swing_highs.append({"index": i, "price": float(highs[i])})
        # Local trough
        if lows[i] == min(lows[i - window : i + window + 1]):
            swing_lows.append({"index": i, "price": float(lows[i])})

    latest_close = float(closes[-1])
    bos = None
    choch = None
    trend = "NEUTRAL"

    if swing_highs and swing_lows:
        last_sh = swing_highs[-1]["price"]
        last_sl = swing_lows[-1]["price"]
        prev_sh = swing_highs[-2]["price"] if len(swing_highs) >= 2 else last_sh
        prev_sl = swing_lows[-2]["price"] if len(swing_lows) >= 2 else last_sl

        # Uptrend determination
        if last_sh > prev_sh and last_sl > prev_sl:
            trend = "BULLISH"
            if latest_close > last_sh:
                bos = {"type": "BULLISH_BOS", "trigger_price": round(last_sh, 2), "description": "Continuation Break of Structure above prior swing high"}
            elif latest_close < last_sl:
                choch = {"type": "BEARISH_CHOCH", "trigger_price": round(last_sl, 2), "description": "Reversal Change of Character below prior swing low"}
        # Downtrend determination
        elif last_sh < prev_sh and last_sl < prev_sl:
            trend = "BEARISH"
            if latest_close < last_sl:
                bos = {"type": "BEARISH_BOS", "trigger_price": round(last_sl, 2), "description": "Continuation Break of Structure below prior swing low"}
            elif latest_close > last_sh:
                choch = {"type": "BULLISH_CHOCH", "trigger_price": round(last_sh, 2), "description": "Reversal Change of Character above prior swing high"}
        else:
            trend = "CONSOLIDATION"

    return {
        "trend": trend,
        "bos": bos,
        "choch": choch,
        "last_swing_high": round(swing_highs[-1]["price"], 2) if swing_highs else None,
        "last_swing_low": round(swing_lows[-1]["price"], 2) if swing_lows else None,
        "swing_high_count": len(swing_highs),
        "swing_low_count": len(swing_lows)
    }

def detect_liquidity_sweeps(df: pd.DataFrame, window: int = 5, lookback: int = 20) -> List[Dict[str, Any]]:
    """
    Detects Buy-Side Liquidity (BSL) and Sell-Side Liquidity (SSL) sweeps.
    A sweep occurs when price penetrates a key swing level intraday but closes back inside,
    trapping retail breakout traders.
    """
    if len(df) < lookback:
        return []

    sweeps = []
    sub_df = df.iloc[-lookback:].copy().reset_index(drop=True)
    n = len(sub_df)

    for i in range(window, n):
        prior_slice = sub_df.iloc[:i]
        prior_high = float(prior_slice['High'].max())
        prior_low = float(prior_slice['Low'].min())

        curr_high = float(sub_df['High'].iloc[i])
        curr_low = float(sub_df['Low'].iloc[i])
        curr_close = float(sub_df['Close'].iloc[i])

        # BSL Sweep: High broke previous high, but Close failed to stay above
        if curr_high > prior_high and curr_close < prior_high:
            sweeps.append({
                "bar_index": int(i),
                "type": "BUY_SIDE_LIQUIDITY_SWEEP",
                "swept_level": round(prior_high, 2),
                "high": round(curr_high, 2),
                "close": round(curr_close, 2),
                "bias": "BEARISH_REVERSAL"
            })
        # SSL Sweep: Low breached previous low, but Close rallied back above
        elif curr_low < prior_low and curr_close > prior_low:
            sweeps.append({
                "bar_index": int(i),
                "type": "SELL_SIDE_LIQUIDITY_SWEEP",
                "swept_level": round(prior_low, 2),
                "low": round(curr_low, 2),
                "close": round(curr_close, 2),
                "bias": "BULLISH_REVERSAL"
            })

    return sweeps[-5:]

def analyze_wyckoff_vsa(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Volume Spread Analysis (VSA) based on Wyckoff methodologies.
    Examines the interaction between spread (High - Low) and Volume to detect smart money activity.
    """
    if len(df) < 25 or 'Volume' not in df.columns:
        return {"signals": [], "dominant_bias": "NEUTRAL", "status": "INSUFFICIENT_DATA"}

    spread = df['High'] - df['Low']
    avg_spread = spread.rolling(window=20).mean()
    rel_spread = spread / avg_spread.replace(0, np.nan)

    vol = df['Volume'].astype(float)
    avg_vol = vol.rolling(window=20).mean()
    rel_vol = vol / avg_vol.replace(0, np.nan)

    signals = []
    n = len(df)

    for i in range(max(20, n - 10), n):
        o = float(df['Open'].iloc[i])
        c = float(df['Close'].iloc[i])
        h = float(df['High'].iloc[i])
        l = float(df['Low'].iloc[i])
        rv = float(rel_vol.iloc[i]) if not np.isnan(rel_vol.iloc[i]) else 1.0
        rs = float(rel_spread.iloc[i]) if not np.isnan(rel_spread.iloc[i]) else 1.0

        bar_spread = h - l
        close_pos = (c - l) / bar_spread if bar_spread > 0 else 0.5

        # 1. Stopping Volume: Down bar, very high volume, close off the lows
        if c < o and rv > 1.6 and close_pos >= 0.4:
            signals.append({
                "bar_index": int(i),
                "name": "Stopping Volume",
                "bias": "BULLISH",
                "description": "Smart money absorbing selling pressure on high volume with price holding above lows"
            })
        # 2. Buying Climax: Up bar, massive volume, wide spread, close off highs
        elif c > o and rv > 2.2 and rs > 1.8 and close_pos < 0.6:
            signals.append({
                "bar_index": int(i),
                "name": "Buying Climax",
                "bias": "BEARISH",
                "description": "Institutional distribution into retail late-stage buying panic"
            })
        # 3. Selling Climax: Down bar, massive volume, wide spread, close off lows
        elif c < o and rv > 2.2 and rs > 1.8 and close_pos > 0.4:
            signals.append({
                "bar_index": int(i),
                "name": "Selling Climax",
                "bias": "BULLISH",
                "description": "Panic capitulation absorbed by institutional accumulator orders"
            })
        # 4. No Supply Test: Down bar, low volume, narrow spread
        elif c <= o and rv < 0.75 and rs < 0.85:
            signals.append({
                "bar_index": int(i),
                "name": "No Supply Test",
                "bias": "BULLISH",
                "description": "Low volume pullback indicating floating supply has evaporated"
            })
        # 5. No Demand Test: Up bar, low volume, narrow spread
        elif c >= o and rv < 0.75 and rs < 0.85:
            signals.append({
                "bar_index": int(i),
                "name": "No Demand Test",
                "bias": "BEARISH",
                "description": "Advance stalling on negligible institutional volume"
            })

    bull_count = sum(1 for s in signals if s["bias"] == "BULLISH")
    bear_count = sum(1 for s in signals if s["bias"] == "BEARISH")
    bias = "BULLISH" if bull_count > bear_count else ("BEARISH" if bear_count > bull_count else "NEUTRAL")

    return {
        "signals": signals[-5:],
        "dominant_bias": bias,
        "latest_relative_volume": round(float(rel_vol.iloc[-1]), 2) if not np.isnan(rel_vol.iloc[-1]) else 1.0,
        "latest_relative_spread": round(float(rel_spread.iloc[-1]), 2) if not np.isnan(rel_spread.iloc[-1]) else 1.0
    }

def analyze_order_flow(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Synthesizes Smart Money Concepts and Order Flow metrics into a unified assessment.
    """
    fvg_data = detect_fair_value_gaps(df)
    structure = detect_market_structure(df)
    sweeps = detect_liquidity_sweeps(df)
    vsa = analyze_wyckoff_vsa(df)

    score = 50
    if fvg_data.get("bias") == "BULLISH":
        score += 10
    elif fvg_data.get("bias") == "BEARISH":
        score -= 10

    if structure.get("trend") == "BULLISH":
        score += 15
    elif structure.get("trend") == "BEARISH":
        score -= 15

    if structure.get("bos"):
        if structure["bos"]["type"] == "BULLISH_BOS":
            score += 10
        else:
            score -= 10

    if structure.get("choch"):
        if structure["choch"]["type"] == "BULLISH_CHOCH":
            score += 15
        else:
            score -= 15

    if vsa.get("dominant_bias") == "BULLISH":
        score += 10
    elif vsa.get("dominant_bias") == "BEARISH":
        score -= 10

    score = max(0, min(100, score))
    verdict = "ACCUMULATION" if score >= 65 else ("DISTRIBUTION" if score <= 35 else "NEUTRAL")

    return {
        "order_flow_score": score,
        "verdict": verdict,
        "fair_value_gaps": fvg_data,
        "market_structure": structure,
        "liquidity_sweeps": sweeps,
        "wyckoff_vsa": vsa
    }
