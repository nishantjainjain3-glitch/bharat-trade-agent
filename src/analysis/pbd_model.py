import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from src.analysis.frvp import calculate_frvp

def detect_pbd_structure(
    df: pd.DataFrame, 
    impulse_window: int = 8,
    consolidation_window: int = 12
) -> Dict[str, Any]:
    """
    Patrick Nill PBD Model Structure Detector.
    Classifies recent price history into:
    - 'P' Structure: Sharp bullish impulse followed by a consolidation range at high prices.
    - 'B' Structure: Sharp bearish impulse followed by a consolidation range at low prices.
    - 'D' Structure: Symmetrical consolidation with no dominant directional impulse.

    Parameters:
      df: Historical DataFrame with ['Open', 'High', 'Low', 'Close', 'Volume']
      impulse_window: Number of bars used to measure the preceding directional move
      consolidation_window: Number of bars forming the current consolidation range
    """
    min_required = impulse_window + consolidation_window
    if len(df) < min_required or not all(c in df.columns for c in ['Open', 'High', 'Low', 'Close']):
        return {
            "structure": "INSUFFICIENT_DATA",
            "status": "NEED_MORE_BARS",
            "description": f"Need at least {min_required} bars to detect PBD structures."
        }

    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    n = len(df)

    # 1. 14-period ATR for volatility normalization
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean()) if len(df) >= 14 else float(high.iloc[-1] - low.iloc[-1])
    current_price = float(close.iloc[-1])

    # 2. Split into Impulse Segment and Consolidation Segment
    consolidation_df = df.iloc[n - consolidation_window:]
    impulse_df = df.iloc[n - min_required : n - consolidation_window]

    range_high = float(consolidation_df['High'].max())
    range_low = float(consolidation_df['Low'].min())
    range_mid = round((range_high + range_low) / 2.0, 2)
    range_width_pct = round(((range_high - range_low) / range_mid) * 100.0, 2) if range_mid > 0 else 0.0

    # Calculate Fixed Range Volume Profile on consolidation zone
    profile = calculate_frvp(df, start_idx=n - consolidation_window, end_idx=n - 1)
    vah = profile.get("vah", range_high)
    val = profile.get("val", range_low)
    poc = profile.get("poc", range_mid)

    # 3. Analyze the preceding impulse move
    impulse_start_price = float(impulse_df['Open'].iloc[0])
    impulse_end_price = float(impulse_df['Close'].iloc[-1])
    impulse_net_change = impulse_end_price - impulse_start_price
    impulse_change_pct = round((impulse_net_change / impulse_start_price) * 100.0, 2) if impulse_start_price > 0 else 0.0
    impulse_atr_mult = round(abs(impulse_net_change) / atr, 2) if atr > 0 else 1.0

    # 4. Measure consolidation tightness relative to impulse
    consolidation_height = range_high - range_low
    impulse_height = float(impulse_df['High'].max()) - float(impulse_df['Low'].min())
    is_consolidating = consolidation_height < (impulse_height * 0.85)

    # 5. Structure Classification
    structure = "D_STRUCTURE"
    bias = "NEUTRAL_BALANCED"
    impulse_origin = impulse_start_price

    if impulse_change_pct >= 2.0 and impulse_atr_mult >= 1.8 and is_consolidating:
        # P Structure: strong rally then consolidation at top
        if range_low >= impulse_start_price:
            structure = "P_STRUCTURE"
            bias = "BULLISH_IMPULSE_PAUSE"
            impulse_origin = float(impulse_df['Low'].min())
    elif impulse_change_pct <= -2.0 and impulse_atr_mult >= 1.8 and is_consolidating:
        # B Structure: strong selloff then consolidation at bottom
        if range_high <= impulse_start_price:
            structure = "B_STRUCTURE"
            bias = "BEARISH_IMPULSE_PAUSE"
            impulse_origin = float(impulse_df['High'].max())

    # Current Price Location relative to range boundaries
    buffer = 0.003 * current_price # 0.3% boundary buffer
    if current_price <= (range_low + buffer):
        location = "AT_RANGE_LOW"
    elif current_price >= (range_high - buffer):
        location = "AT_RANGE_HIGH"
    elif current_price > range_high:
        location = "ABOVE_RANGE_EXPANSION"
    elif current_price < range_low:
        location = "BELOW_RANGE_EXPANSION"
    else:
        location = "INSIDE_CONSOLIDATION_MID"

    return {
        "structure": structure,
        "bias": bias,
        "current_price": round(current_price, 2),
        "atr": round(atr, 2),
        "range_high": round(range_high, 2),
        "range_low": round(range_low, 2),
        "range_mid": range_mid,
        "range_width_pct": range_width_pct,
        "vah": round(vah, 2),
        "val": round(val, 2),
        "poc": round(poc, 2),
        "price_location": location,
        "impulse_origin": round(impulse_origin, 2),
        "impulse_change_pct": impulse_change_pct,
        "impulse_atr_mult": impulse_atr_mult,
        "consolidation_bars": consolidation_window,
        "impulse_bars": impulse_window
    }


def evaluate_patrick_nill_setup(
    df: pd.DataFrame, 
    account_equity: float = 100000.0, 
    max_risk_pct: float = 1.0
) -> Dict[str, Any]:
    """
    Patrick Nill PBD Trading Setup Evaluator & Risk Budgeter.
    Applies Patrick Nill's two primary execution playbooks:
    1. Playbook 1: Range Boundary 'Ping-Pong' (Mean Reversion)
       - Buy at Range Low / VAL towards POC and Range High.
       - Sell at Range High / VAH towards POC and Range Low.
       - Counter-trend swing target extends to the origin of the initial impulse.
    2. Playbook 2: Breakout / Pullback Continuation
       - When price breaks range in the direction of the impulse and retests the broken edge.

    Enforces:
    - Never risk more than 1.0% of portfolio equity.
    - Predefined stop placed outside the marked zone.
    """
    struct = detect_pbd_structure(df)
    if struct.get("structure") == "INSUFFICIENT_DATA":
        return {
            "strategy": "PATRICK_NILL_PBD",
            "setup": "NO_SETUP",
            "action": "NONE",
            "status": "INSUFFICIENT_DATA",
            "structure": struct
        }

    current_price = struct["current_price"]
    atr = struct["atr"]
    range_high = struct["range_high"]
    range_low = struct["range_low"]
    poc = struct["poc"]
    impulse_origin = struct["impulse_origin"]
    location = struct["price_location"]
    pbd_type = struct["structure"]

    risk_budget = round(account_equity * (max_risk_pct / 100.0), 2)
    setup = "NO_SETUP"
    action = "WAIT_FOR_RANGE_BOUNDARY"
    playbook = "NONE"
    entry_price = current_price
    stop_loss = 0.0
    tp1 = poc
    tp2 = 0.0
    tp3_impulse_origin = impulse_origin
    risk_per_share = 0.0
    shares = 0

    stop_buffer = round(0.5 * atr, 2)

    # -------------------------------------------------------------
    # Playbook 1: Boundary Ping-Pong (Mean Reversion)
    # -------------------------------------------------------------
    if location == "AT_RANGE_LOW":
        # Long Ping-Pong Setup at Range Floor / VAL
        setup = f"PBD_{pbd_type}_PINGPONG_LONG"
        action = "BUY_RANGE_LOW"
        playbook = "PLAYBOOK_1_PINGPONG_BOUNDARY"
        entry_price = round(current_price, 2)
        stop_loss = round(range_low - stop_buffer, 2)
        risk_per_share = round(entry_price - stop_loss, 2)
        tp1 = poc
        tp2 = range_high
        tp3_impulse_origin = impulse_origin if pbd_type == "B_STRUCTURE" else range_high

    elif location == "AT_RANGE_HIGH":
        # Short Ping-Pong Setup at Range Ceiling / VAH
        setup = f"PBD_{pbd_type}_PINGPONG_SHORT"
        action = "SELL_RANGE_HIGH"
        playbook = "PLAYBOOK_1_PINGPONG_BOUNDARY"
        entry_price = round(current_price, 2)
        stop_loss = round(range_high + stop_buffer, 2)
        risk_per_share = round(stop_loss - entry_price, 2)
        tp1 = poc
        tp2 = range_low
        tp3_impulse_origin = impulse_origin if pbd_type == "P_STRUCTURE" else range_low

    # -------------------------------------------------------------
    # Playbook 2: Breakout Pullback Continuation
    # -------------------------------------------------------------
    elif pbd_type == "P_STRUCTURE" and location == "ABOVE_RANGE_EXPANSION":
        setup = "PBD_P_STRUCTURE_BREAKOUT_EXPANSION"
        action = "BUY_PULLBACK_RETEST"
        playbook = "PLAYBOOK_2_BREAKOUT_CONTINUATION"
        entry_price = round(current_price, 2)
        stop_loss = round(range_high - stop_buffer, 2)
        risk_per_share = round(entry_price - stop_loss, 2)
        tp1 = round(entry_price + (2.0 * atr), 2)
        tp2 = round(entry_price + (3.5 * atr), 2)
        tp3_impulse_origin = round(entry_price + (5.0 * atr), 2)

    elif pbd_type == "B_STRUCTURE" and location == "BELOW_RANGE_EXPANSION":
        setup = "PBD_B_STRUCTURE_BREAKDOWN_EXPANSION"
        action = "SELL_PULLBACK_RETEST"
        playbook = "PLAYBOOK_2_BREAKOUT_CONTINUATION"
        entry_price = round(current_price, 2)
        stop_loss = round(range_low + stop_buffer, 2)
        risk_per_share = round(stop_loss - entry_price, 2)
        tp1 = round(entry_price - (2.0 * atr), 2)
        tp2 = round(entry_price - (3.5 * atr), 2)
        tp3_impulse_origin = round(entry_price - (5.0 * atr), 2)

    # Calculate Position Sizing under strict 1.0% Account Risk Rule
    if risk_per_share > 0:
        shares = int(risk_budget / risk_per_share)
        total_outlay = round(shares * entry_price, 2)
        target_reward = abs(tp2 - entry_price)
        rr_ratio = round(target_reward / risk_per_share, 2) if risk_per_share > 0 else 0.0
    else:
        total_outlay = 0.0
        rr_ratio = 0.0

    return {
        "strategy": "PATRICK_NILL_PBD",
        "mentor": "Patrick Nill (World Trading Championship)",
        "source": "TradeIQ (@tradeiq.with.nitz)",
        "setup": setup,
        "action": action,
        "playbook": playbook,
        "is_active": setup != "NO_SETUP",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "tp1_mid_poc": tp1,
        "tp2_opposite_boundary": tp2,
        "tp3_impulse_origin": tp3_impulse_origin,
        "risk_per_share": risk_per_share,
        "risk_reward_ratio": rr_ratio,
        "sizing": {
            "account_equity": account_equity,
            "max_risk_pct": max_risk_pct,
            "risk_budget_inr": risk_budget,
            "allowed_shares": shares,
            "total_outlay_inr": total_outlay,
            "risk_rule": "Strict 1.0% Portfolio Equity Cap (0.2-2.0% Scale)"
        },
        "structure": struct,
        "checklist": [
            "1. Large impulse (P or B) complete - trading consolidation only",
            "2. Range boundaries marked on 15m/1h chart",
            "3. Weekly VAH/VAL aligns with consolidation boundaries",
            "4. Stop-loss defined outside boundary before entry",
            "5. Position sized for max 1% account risk",
            "6. Target set to POC and opposite boundary / impulse origin"
        ]
    }
