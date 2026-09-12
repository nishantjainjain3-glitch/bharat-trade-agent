import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calculate_frvp(df: pd.DataFrame, start_idx: int = None, end_idx: int = None,
                   n_bins: int = 50) -> Dict[str, Any]:
    """
    Fixed Range Volume Profile (FRVP) — as used by @algotrader.sahil / Anish Singh Thakur (Booming Bulls).
    Calculates POC (Point of Control), VAH (Value Area High), VAL (Value Area Low)
    from a user-defined slice of OHLCV data.

    df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
    start_idx: start row index (default: beginning of df)
    end_idx: end row index (default: last row of df)
    n_bins: number of price levels in the profile (default 50)
    """
    if len(df) < 3:
        return {
            "poc": 0.0, "vah": 0.0, "val": 0.0,
            "value_area_pct": 0.0, "status": "INSUFFICIENT_DATA"
        }

    if start_idx is None:
        start_idx = 0
    if end_idx is None:
        end_idx = len(df) - 1

    start_idx = max(0, start_idx)
    end_idx = min(len(df) - 1, end_idx)

    slice_df = df.iloc[start_idx:end_idx + 1].copy()

    # Handle missing volume — distribute equally
    if 'Volume' not in slice_df.columns or slice_df['Volume'].sum() == 0:
        slice_df['Volume'] = 1.0

    price_min = float(slice_df['Low'].min())
    price_max = float(slice_df['High'].max())

    if price_max <= price_min:
        mid = (price_max + price_min) / 2.0
        return {
            "poc": round(mid, 2), "vah": round(price_max, 2), "val": round(price_min, 2),
            "value_area_pct": 70.0, "status": "FLAT_RANGE"
        }

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_mids = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # Distribute each bar's volume proportionally across the bins it spans
    volume_at_price = np.zeros(n_bins)
    for _, row in slice_df.iterrows():
        bar_low = float(row['Low'])
        bar_high = float(row['High'])
        bar_vol = float(row['Volume'])
        in_range = (bin_mids >= bar_low) & (bin_mids <= bar_high)
        n_covered = int(in_range.sum())
        if n_covered > 0:
            volume_at_price[in_range] += bar_vol / n_covered

    # POC: bin with highest accumulated volume
    poc_idx = int(np.argmax(volume_at_price))
    poc = round(float(bin_mids[poc_idx]), 2)

    # Value Area: expand outward from POC until 70% of total volume is captured
    total_vol = float(volume_at_price.sum())
    target_vol = total_vol * 0.70
    accumulated = float(volume_at_price[poc_idx])
    upper_idx = poc_idx
    lower_idx = poc_idx

    while accumulated < target_vol:
        can_up = upper_idx < n_bins - 1
        can_down = lower_idx > 0
        vol_up = float(volume_at_price[upper_idx + 1]) if can_up else 0.0
        vol_down = float(volume_at_price[lower_idx - 1]) if can_down else 0.0

        if not can_up and not can_down:
            break
        if vol_up >= vol_down and can_up:
            upper_idx += 1
            accumulated += vol_up
        elif can_down:
            lower_idx -= 1
            accumulated += vol_down
        else:
            upper_idx += 1
            accumulated += vol_up

    vah = round(float(bin_mids[upper_idx]), 2)
    val = round(float(bin_mids[lower_idx]), 2)
    value_area_pct = round(accumulated / total_vol * 100.0, 1) if total_vol > 0 else 0.0

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "value_area_pct": value_area_pct,
        "price_range_low": round(price_min, 2),
        "price_range_high": round(price_max, 2),
        "n_bars_analyzed": len(slice_df),
        "status": "OK"
    }


def evaluate_frvp_setup(current_price: float, vah: float, val: float,
                        poc: float, atr: float,
                        candle_bullish: bool = True,
                        volume_above_avg: bool = True) -> Dict[str, Any]:
    """
    Given FRVP levels and current bar conditions, determine if a VAH/VAL
    setup is active and compute entry, stop, and targets.

    Long setup: price at or below VAL with bullish rejection candle + above-average volume.
    Short setup: price at or above VAH with bearish candle + above-average volume.
    Returns NO_SETUP when neither condition is met.
    """
    at_val = current_price <= val * 1.003  # within 0.3% of VAL
    at_vah = current_price >= vah * 0.997  # within 0.3% of VAH

    if at_val and candle_bullish and volume_above_avg:
        setup = "LONG_VAL_BOUNCE"
        entry = round(current_price, 2)
        stop = round(val - atr, 2)
        tp1 = poc
        tp2 = vah
        risk = entry - stop
        rr = round((tp2 - entry) / risk, 2) if risk > 0 else 0.0
        description = "Price at VAL discount zone with bullish rejection. Long toward POC (TP1) then VAH (TP2)."

    elif at_vah and not candle_bullish and volume_above_avg:
        setup = "SHORT_VAH_REJECTION"
        entry = round(current_price, 2)
        stop = round(vah + atr, 2)
        tp1 = poc
        tp2 = val
        risk = stop - entry
        rr = round((entry - tp2) / risk, 2) if risk > 0 else 0.0
        description = "Price at VAH premium zone with bearish rejection. Short toward POC (TP1) then VAL (TP2)."

    else:
        setup = "NO_SETUP"
        entry = stop = tp1 = tp2 = rr = None
        description = "Price is inside the Value Area or lacks confirmation. No FRVP setup active."

    return {
        "setup": setup,
        "description": description,
        "entry": entry,
        "stop": stop,
        "tp1_poc": tp1,
        "tp2_extreme": tp2,
        "risk_reward": rr,
        "levels": {"vah": vah, "poc": poc, "val": val}
    }


def get_frvp_analysis(df: pd.DataFrame, lookback_bars: int = 20) -> Dict[str, Any]:
    """
    High-level FRVP analysis for a symbol's recent price history.
    Uses the last `lookback_bars` as the fixed range, then evaluates the current setup.
    Returns POC/VAH/VAL levels and any active setup signal.
    """
    if len(df) < lookback_bars + 1:
        lookback_bars = max(3, len(df) - 1)

    start = len(df) - lookback_bars - 1
    end = len(df) - 2  # exclude current bar (not yet closed)

    profile = calculate_frvp(df, start_idx=start, end_idx=end)

    if profile.get("status") != "OK":
        return profile

    current_close = float(df['Close'].iloc[-1])
    current_open = float(df['Open'].iloc[-1])
    candle_bullish = current_close > current_open

    # Volume check: current bar vs 20-bar average
    avg_vol = float(df['Volume'].tail(20).mean()) if 'Volume' in df.columns else 1.0
    current_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else avg_vol
    volume_above_avg = current_vol >= avg_vol * 1.2

    # ATR for stop calculation
    tr_series = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr_series.tail(14).mean())

    setup = evaluate_frvp_setup(
        current_price=current_close,
        vah=profile['vah'],
        val=profile['val'],
        poc=profile['poc'],
        atr=atr,
        candle_bullish=candle_bullish,
        volume_above_avg=volume_above_avg
    )

    return {
        **profile,
        "current_price": round(current_close, 2),
        "atr": round(atr, 2),
        "setup": setup
    }
