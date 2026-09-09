import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_ttm_squeeze(
    df: pd.DataFrame, 
    bb_length: int = 20, 
    bb_mult: float = 2.0, 
    kc_length: int = 20, 
    kc_mult: float = 1.5
) -> Dict[str, Any]:
    """
    John Carter's TTM Squeeze indicator.
    Identifies periods of volatility consolidation (squeeze on) when Bollinger Bands contract
    inside Keltner Channels, followed by explosive expansion (squeeze fired).
    """
    if len(df) < max(bb_length, kc_length) + 10:
        return {
            "squeeze_on": False,
            "squeeze_fired": False,
            "momentum_histogram": 0.0,
            "momentum_direction": "NEUTRAL",
            "status": "INSUFFICIENT_DATA"
        }

    close = df['Close']
    high = df['High']
    low = df['Low']

    # 1. Bollinger Bands
    bb_basis = close.rolling(window=bb_length).mean()
    bb_std = close.rolling(window=bb_length).std()
    bb_upper = bb_basis + (bb_mult * bb_std)
    bb_lower = bb_basis - (bb_mult * bb_std)

    # 2. Keltner Channels
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=kc_length).mean()

    kc_basis = close.rolling(window=kc_length).mean()
    kc_upper = kc_basis + (kc_mult * atr)
    kc_lower = kc_basis - (kc_mult * atr)

    # 3. Squeeze condition (BB inside KC)
    squeeze_series = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    current_squeeze = bool(squeeze_series.iloc[-1])
    prev_squeeze = bool(squeeze_series.iloc[-2]) if len(squeeze_series) > 1 else False
    squeeze_fired = prev_squeeze and not current_squeeze

    # 4. Momentum Histogram: Linear regression of price delta from average of midline and (highest + lowest)/2
    highest_high = high.rolling(window=kc_length).max()
    lowest_low = low.rolling(window=kc_length).min()
    donchian_mid = (highest_high + lowest_low) / 2.0
    val = close - ((donchian_mid + kc_basis) / 2.0)

    # Vectorized 6-period linear regression slope of val
    x = np.arange(6)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    
    reg_hist = []
    val_clean = val.fillna(0.0).values
    for i in range(len(val_clean)):
        if i < 5:
            reg_hist.append(0.0)
        else:
            y_window = val_clean[i - 5 : i + 1]
            y_mean = y_window.mean()
            slope = np.sum((x - x_mean) * (y_window - y_mean)) / x_var
            reg_hist.append(slope)

    momentum_hist = float(reg_hist[-1])
    prev_momentum = float(reg_hist[-2]) if len(reg_hist) > 1 else 0.0

    if momentum_hist > 0:
        mom_dir = "BULLISH_EXPANSION" if momentum_hist >= prev_momentum else "BULLISH_EXHAUSTION"
    else:
        mom_dir = "BEARISH_EXPANSION" if momentum_hist <= prev_momentum else "BEARISH_EXHAUSTION"

    return {
        "squeeze_on": current_squeeze,
        "squeeze_fired": squeeze_fired,
        "momentum_histogram": round(momentum_hist, 4),
        "momentum_direction": mom_dir,
        "bb_upper": round(float(bb_upper.iloc[-1]), 2),
        "bb_lower": round(float(bb_lower.iloc[-1]), 2),
        "kc_upper": round(float(kc_upper.iloc[-1]), 2),
        "kc_lower": round(float(kc_lower.iloc[-1]), 2),
        "volatility_state": "COMPRESSION (Squeeze ON)" if current_squeeze else ("EXPLOSION (Squeeze FIRED)" if squeeze_fired else "EXPANSION (Normal)")
    }

def calculate_hvr(df: pd.DataFrame, short_window: int = 6, long_window: int = 100) -> Dict[str, Any]:
    """
    Historical Volatility Ratio (HVR).
    HVR = Short-term Volatility (6-period) / Long-term Volatility (100-period).
    When HVR < 0.50, volatility has compressed to extreme lows, setting up massive trend breakout.
    """
    if len(df) < long_window + 1:
        return {"hvr": 1.0, "coiled_breakout_imminent": False, "short_hv": 0.0, "long_hv": 0.0}

    log_ret = np.log(df['Close'] / df['Close'].shift(1))
    short_vol = log_ret.rolling(window=short_window).std() * np.sqrt(252) * 100.0
    long_vol = log_ret.rolling(window=long_window).std() * np.sqrt(252) * 100.0

    cur_short = float(short_vol.iloc[-1])
    cur_long = float(long_vol.iloc[-1])
    hvr = cur_short / cur_long if cur_long > 0 else 1.0

    return {
        "hvr": round(hvr, 2),
        "coiled_breakout_imminent": bool(hvr < 0.50),
        "short_term_hv_annualized": round(cur_short, 2),
        "long_term_hv_annualized": round(cur_long, 2),
        "regime": "COILING_COMPRESSION" if hvr < 0.50 else ("ELEVATED_VOLATILITY" if hvr > 1.20 else "EQUILIBRIUM")
    }

def calculate_cmo(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Chande Momentum Oscillator (CMO).
    Measures momentum on both up and down days without smoothing, scaled from -100 to +100.
    > +50 indicates extreme overbought condition; < -50 indicates extreme oversold condition.
    """
    diff = series.diff()
    up = diff.where(diff > 0, 0.0)
    down = (-diff).where(diff < 0, 0.0)

    sum_up = up.rolling(window=period).sum()
    sum_down = down.rolling(window=period).sum()

    denom = sum_up + sum_down
    cmo = 100.0 * (sum_up - sum_down) / denom.replace(0, np.nan)
    return cmo.fillna(0.0)

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
    """
    Supertrend dynamic trend follower & volatility trailing stop calculator.
    """
    if len(df) < period + 5:
        return {"supertrend": 0.0, "direction": "NEUTRAL", "trend": "NEUTRAL"}

    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    n = len(df)

    # ATR
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr1 = high[i] - low[i]
        tr2 = abs(high[i] - close[i - 1])
        tr3 = abs(low[i] - close[i - 1])
        tr[i] = max(tr1, tr2, tr3)

    atr = pd.Series(tr).rolling(window=period).mean().fillna(tr[0]).values

    hl2 = (high + low) / 2.0
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    trend_dir = np.zeros(n)  # 1 = bullish, -1 = bearish
    st = np.zeros(n)

    for i in range(period, n):
        # Upper band
        if basic_upper[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i - 1]

        # Lower band
        if basic_lower[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i - 1]

        # Direction
        if i == period:
            trend_dir[i] = 1 if close[i] > final_upper[i] else -1
        else:
            if trend_dir[i - 1] == 1:
                trend_dir[i] = -1 if close[i] < final_lower[i] else 1
            else:
                trend_dir[i] = 1 if close[i] > final_upper[i] else -1

        st[i] = final_lower[i] if trend_dir[i] == 1 else final_upper[i]

    cur_dir = int(trend_dir[-1])
    cur_st = float(st[-1])
    cur_close = float(close[-1])

    return {
        "supertrend_price": round(cur_st, 2),
        "direction": "BULLISH" if cur_dir == 1 else "BEARISH",
        "stop_loss_distance_pct": round(abs(cur_close - cur_st) / cur_close * 100.0, 2) if cur_close > 0 else 0.0
    }

def analyze_volatility_regime(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive multi-metric volatility and momentum assessment.
    """
    squeeze = calculate_ttm_squeeze(df)
    hvr = calculate_hvr(df)
    cmo_series = calculate_cmo(df['Close'])
    cmo_val = round(float(cmo_series.iloc[-1]), 2) if len(cmo_series) > 0 else 0.0
    supertrend = calculate_supertrend(df)

    # Volatility score: high = explosive/expanding, low = coiled/compressing
    compression_signals = 0
    if squeeze.get("squeeze_on"):
        compression_signals += 1
    if hvr.get("coiled_breakout_imminent"):
        compression_signals += 1

    return {
        "ttm_squeeze": squeeze,
        "hvr": hvr,
        "cmo": {
            "value": cmo_val,
            "status": "OVERBOUGHT" if cmo_val >= 50 else ("OVERSOLD" if cmo_val <= -50 else "NEUTRAL")
        },
        "supertrend": supertrend,
        "is_coiling": compression_signals >= 1,
        "breakout_setup": squeeze.get("squeeze_fired", False) or (squeeze.get("squeeze_on") and abs(cmo_val) > 25)
    }
