import math
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calculate_atr(df: Optional[pd.DataFrame], period: int = 14) -> float:
    """
    Computes standard 14-period Average True Range (ATR) from OHLC dataframe.
    """
    if df is None or len(df) < 2:
        return 0.0

    high_col = "High" if "High" in df.columns else ("high" if "high" in df.columns else None)
    low_col = "Low" if "Low" in df.columns else ("low" if "low" in df.columns else None)
    close_col = "Close" if "Close" in df.columns else ("close" if "close" in df.columns else None)

    if not high_col or not low_col or not close_col:
        return 0.0

    high = df[high_col]
    low = df[low_col]
    close_prev = df[close_col].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    if len(df) >= period:
        atr_series = tr.rolling(window=period, min_periods=period).mean()
        val = atr_series.iloc[-1]
        if pd.isna(val):
            val = tr.mean()
    else:
        val = tr.mean()

    return round(float(val), 2) if not pd.isna(val) else 0.0


def calculate_volatility_parity_position(
    account_equity: float,
    current_price: float,
    atr: float,
    risk_pct: float = 0.01,
    atr_stop_multiple: float = 2.0,
    target_rr_ratio: float = 2.0,
    tier_multiplier: float = 1.0,
    available_cash: Optional[float] = None,
    max_allocation_pct: float = 0.35
) -> Dict[str, Any]:
    """
    Calculates exact share sizing using 1% ATR Volatility-Parity.
    
    Every single trade position is dynamically sized so that a 
    (atr_stop_multiple * ATR) adverse move equals exactly 1% of total account equity
    (scaled by survival tier multiplier).
    """
    if account_equity <= 0 or current_price <= 0:
        return {
            "quantity": 0,
            "allowed": False,
            "reason": "Invalid account equity or current price",
            "current_price": current_price,
            "atr": atr,
            "stop_loss": 0.0,
            "target_price": 0.0,
            "risk_per_share": 0.0,
            "total_risk_inr": 0.0,
            "risk_pct_actual": 0.0,
            "allocation_inr": 0.0,
            "allocation_pct": 0.0
        }

    effective_atr = max(atr, current_price * 0.005)
    stop_distance = round(effective_atr * atr_stop_multiple, 2)
    stop_distance = max(stop_distance, round(current_price * 0.005, 2))

    stop_loss = round(max(0.05, current_price - stop_distance), 2)
    target_price = round(current_price + (stop_distance * target_rr_ratio), 2)

    dollar_risk_budget = account_equity * risk_pct * max(0.0, tier_multiplier)

    if tier_multiplier <= 0:
        return {
            "quantity": 0,
            "allowed": False,
            "reason": "Trading blocked by Survival Tier (multiplier 0.0)",
            "current_price": current_price,
            "atr": effective_atr,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "risk_per_share": stop_distance,
            "total_risk_inr": 0.0,
            "risk_pct_actual": 0.0,
            "allocation_inr": 0.0,
            "allocation_pct": 0.0
        }

    target_shares_by_risk = math.floor(dollar_risk_budget / stop_distance)

    cash_pool = account_equity if available_cash is None else available_cash
    max_capital_for_stock = min(cash_pool, account_equity * max_allocation_pct)
    max_shares_by_cash = math.floor(max_capital_for_stock / current_price)

    if max_shares_by_cash <= 0:
        return {
            "quantity": 0,
            "allowed": False,
            "reason": f"Insufficient cash (₹{cash_pool:,.2f}) or allocation cap for price ₹{current_price:,.2f}",
            "current_price": current_price,
            "atr": effective_atr,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "risk_per_share": stop_distance,
            "total_risk_inr": 0.0,
            "risk_pct_actual": 0.0,
            "allocation_inr": 0.0,
            "allocation_pct": 0.0
        }

    raw_quantity = min(target_shares_by_risk, max_shares_by_cash)

    if raw_quantity == 0 and (cash_pool >= current_price):
        one_share_risk = stop_distance
        one_share_risk_pct = one_share_risk / account_equity
        if one_share_risk_pct <= 0.015:
            quantity = 1
        else:
            return {
                "quantity": 0,
                "allowed": False,
                "reason": f"1 share risk ({one_share_risk_pct*100:.2f}%) exceeds 1.5% constitutional threshold",
                "current_price": current_price,
                "atr": effective_atr,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "risk_per_share": stop_distance,
                "total_risk_inr": 0.0,
                "risk_pct_actual": 0.0,
                "allocation_inr": 0.0,
                "allocation_pct": 0.0
            }
    else:
        quantity = max(0, raw_quantity)

    if quantity <= 0:
        return {
            "quantity": 0,
            "allowed": False,
            "reason": "Calculated zero allocation",
            "current_price": current_price,
            "atr": effective_atr,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "risk_per_share": stop_distance,
            "total_risk_inr": 0.0,
            "risk_pct_actual": 0.0,
            "allocation_inr": 0.0,
            "allocation_pct": 0.0
        }

    total_risk_inr = round(quantity * stop_distance, 2)
    risk_pct_actual = round(total_risk_inr / account_equity, 4)
    allocation_inr = round(quantity * current_price, 2)
    allocation_pct = round(allocation_inr / account_equity, 4)

    return {
        "quantity": quantity,
        "allowed": True,
        "reason": f"Volatility-parity 1% ATR allocation verified ({quantity} shares)",
        "current_price": current_price,
        "atr": effective_atr,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "risk_per_share": stop_distance,
        "total_risk_inr": total_risk_inr,
        "risk_pct_actual": risk_pct_actual,
        "allocation_inr": allocation_inr,
        "allocation_pct": allocation_pct
    }