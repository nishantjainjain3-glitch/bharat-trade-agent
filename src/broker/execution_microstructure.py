import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

def get_ist_time() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def estimate_bid_ask_spread(price: float, atr: float, avg_daily_volume: float = 1_000_000) -> Dict[str, Any]:
    """
    Estimates realistic bid-ask spread for Indian equities based on liquidity & volatility.
    Liquid Nifty 50 stocks (high ADV) trade with tight 0.03% - 0.08% spreads.
    Midcaps and smallcaps widen to 0.15% - 0.50%.
    """
    if price <= 0:
        return {"spread_abs": 0.05, "spread_bps": 5.0, "spread_pct": 0.05}

    volatility_ratio = (atr / price) if price > 0 else 0.02

    # Volume liquidity scaling factor
    if avg_daily_volume > 5_000_000:
        base_bps = 4.0  # ~0.04% for mega-caps like Reliance, TCS, BHEL
    elif avg_daily_volume > 1_000_000:
        base_bps = 8.0  # ~0.08% for large/midcaps
    elif avg_daily_volume > 200_000:
        base_bps = 18.0 # ~0.18% for midcaps
    else:
        base_bps = 35.0 # ~0.35% for lower liquidity

    # Adjust by current ATR volatility
    vol_multiplier = max(0.8, min(2.5, volatility_ratio / 0.02))
    effective_bps = round(base_bps * vol_multiplier, 2)
    spread_pct = effective_bps / 100.0
    spread_abs = round(price * (spread_pct / 100.0), 2)

    return {
        "spread_abs": spread_abs,
        "spread_bps": effective_bps,
        "spread_pct": round(spread_pct, 4),
        "half_spread": round(spread_abs / 2.0, 2)
    }

def calculate_realistic_execution(
    symbol: str,
    action: str, # "BUY" or "SELL"
    order_type: str, # "MARKET" or "LIMIT"
    price: float,
    quantity: int,
    atr: float,
    avg_daily_volume: float = 1_500_000
) -> Dict[str, Any]:
    """
    Simulates institutional execution quality, spread cost, and slippage.
    Incorporates:
    1. Bid-ask bounce (paying half-spread on market orders).
    2. Almgren-Chriss Square-Root Market Impact based on order size vs ADV.
    3. Market Open Volatility Penalty (9:15 - 9:35 AM IST) when spreads gap wide.
    """
    now_ist = get_ist_time()
    decimal_time = now_ist.hour + (now_ist.minute / 60.0)

    # 1. Opening Session Volatility Penalty
    # 9:15 to 9:35 AM IST represents the opening auction price discovery rush
    is_market_open_rush = (9.25 <= decimal_time <= 9.58)
    time_penalty_bps = 15.0 if is_market_open_rush else 0.0

    # 2. Spread Cost
    spread_info = estimate_bid_ask_spread(price, atr, avg_daily_volume)
    spread_bps = spread_info["spread_bps"]

    # 3. Market Impact (Square Root Law of Price Impact)
    # Impact ~ Volatility * sqrt(Quantity / ADV)
    participation_rate = (quantity / avg_daily_volume) if avg_daily_volume > 0 else 0.0001
    market_impact_pct = (atr / price) * math.sqrt(participation_rate) * 100.0 if price > 0 else 0.0
    market_impact_bps = max(0.5, market_impact_pct * 100.0)

    # Total expected slippage
    if order_type.upper() == "LIMIT":
        # Limit orders earn the spread or have zero slippage, but face execution latency
        slippage_bps = 0.0
        slippage_abs = 0.0
        expected_fill_price = price
        execution_type = "PASSIVE_MAKER"
    else:
        # Market orders cross the spread and suffer slippage
        total_slippage_bps = (spread_bps / 2.0) + market_impact_bps + time_penalty_bps
        slippage_pct = total_slippage_bps / 10000.0
        slippage_abs = round(price * slippage_pct, 2)
        
        if action.upper() == "BUY":
            expected_fill_price = round(price + slippage_abs, 2)
        else:
            expected_fill_price = round(max(0.1, price - slippage_abs), 2)
            
        execution_type = "AGGRESSIVE_TAKER"

    total_order_value = round(expected_fill_price * quantity, 2)
    slippage_cost_inr = round(slippage_abs * quantity, 2)

    return {
        "symbol": symbol,
        "action": action,
        "quoted_price": price,
        "expected_fill_price": expected_fill_price,
        "quantity": quantity,
        "total_value_inr": total_order_value,
        "slippage_abs_per_share": slippage_abs,
        "slippage_bps": round((slippage_abs / price * 10000.0) if price > 0 else 0.0, 1),
        "total_slippage_cost_inr": slippage_cost_inr,
        "spread_bps": spread_bps,
        "market_impact_bps": round(market_impact_bps, 1),
        "is_market_open_rush": is_market_open_rush,
        "execution_type": execution_type,
        "recommendation": "USE_LIMIT_ORDER" if total_slippage_bps > 25.0 else "MARKET_ORDER_ACCEPTABLE"
    }


def calculate_statutory_friction(
    symbol: str,
    action: str,  # "BUY", "SELL", or "ROUND_TRIP"
    price: float,
    quantity: int,
    trade_type: str = "DELIVERY"  # "DELIVERY" or "INTRADAY"
) -> Dict[str, Any]:
    """
    Statutory Indian Transaction Charges & Fee Arithmetic (The Penniless Agent Doctrine):
    Calculates exact statutory taxes and exchange levies:
    - Brokerage: ₹0 for Delivery on Angel One
    - STT (Securities Transaction Tax): 0.1% on buy & sell (Delivery)
    - Exchange Turnover Charges: 0.00297%
    - Stamp Duty: 0.015% (Buy delivery)
    - SEBI Turnover Fee: ₹10 / crore (0.0001%)
    - DP Charges: ₹15.34 + 18% GST = ₹18.10 per scrip per day (Delivery SELL only)
    - GST: 18% on (brokerage + exchange charges + sebi fee)

    Protects small portfolios by flagging FEE_PROHIBITIVE micro-trades (>2.5% friction).
    """
    turnover = price * quantity
    if turnover <= 0:
        return {"total_friction_inr": 0.0, "friction_pct": 0.0, "is_fee_prohibitive": False}

    # 1. Brokerage (Angel One: Flat ₹0 for Delivery)
    brokerage = 0.0 if trade_type.upper() == "DELIVERY" else min(20.0, round(turnover * 0.0003, 2))

    # 2. STT (Securities Transaction Tax)
    if trade_type.upper() == "DELIVERY":
        stt = round(turnover * 0.001, 2) if action.upper() in ("BUY", "SELL") else round(turnover * 0.002, 2)
    else:
        stt = round(turnover * 0.00025, 2) if action.upper() in ("SELL", "ROUND_TRIP") else 0.0

    # 3. Exchange turnover charges (NSE ~0.00297%)
    exchange_charges = round(turnover * 0.0000297, 2)

    # 4. Stamp duty (0.015% on Buy)
    stamp_duty = round(turnover * 0.00015, 2) if action.upper() in ("BUY", "ROUND_TRIP") else 0.0

    # 5. SEBI turnover fee (₹10 / crore)
    sebi_fee = round(turnover * 0.000001, 2)

    # 6. DP Charges (₹18.10 per scrip on Delivery SELL)
    dp_charges = 18.10 if (trade_type.upper() == "DELIVERY" and action.upper() in ("SELL", "ROUND_TRIP")) else 0.0

    # 7. GST (18% on Brokerage + Exchange charges + SEBI fee)
    gst = round((brokerage + exchange_charges + sebi_fee) * 0.18, 2)

    total_friction = round(brokerage + stt + exchange_charges + stamp_duty + sebi_fee + dp_charges + gst, 2)
    friction_pct = round((total_friction / turnover) * 100.0, 3)

    # Economic viability check: Flag trades where statutory friction eats > 2.0% of principal
    is_fee_prohibitive = bool(friction_pct > 2.0)
    min_viable_lot_for_delivery = max(1, math.ceil(1500.0 / price)) if price > 0 else 1

    return {
        "symbol": symbol,
        "action": action.upper(),
        "trade_type": trade_type.upper(),
        "price": price,
        "quantity": quantity,
        "turnover": round(turnover, 2),
        "brokerage": brokerage,
        "stt": stt,
        "exchange_charges": exchange_charges,
        "stamp_duty": stamp_duty,
        "sebi_fee": sebi_fee,
        "dp_charges": dp_charges,
        "gst": gst,
        "total_friction_inr": total_friction,
        "friction_pct": friction_pct,
        "is_fee_prohibitive": is_fee_prohibitive,
        "min_viable_lot_size": min_viable_lot_for_delivery,
        "warning": (
            f"FEE_PROHIBITIVE: Statutory charges (₹{total_friction:.2f}) consume {friction_pct:.2f}% of position value. "
            f"DP charges (₹18.10) make 1-share delivery sales economically irrational. Minimum viable lot is {min_viable_lot_for_delivery} shares."
            if is_fee_prohibitive else None
        )
    }

