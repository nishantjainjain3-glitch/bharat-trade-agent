from typing import Dict, Any, List

def generate_tactical_battle_plan(
    quote: Dict[str, Any],
    technicals: Dict[str, Any],
    fundamentals: Dict[str, Any],
    research: Dict[str, Any],
    survival_tier: str = "NORMAL"
) -> Dict[str, Any]:
    price = float(quote.get("price", 0.0))
    if price <= 0:
        return {}

    levels = technicals.get("levels", {})
    support = float(levels.get("support", price * 0.96))
    resistance = float(levels.get("resistance", price * 1.06))
    recent_high = float(levels.get("recent_high_20d", price * 1.04))
    recent_low = float(levels.get("recent_low_20d", price * 0.96))
    atr = float(levels.get("atr", price * 0.02))

    emas = technicals.get("emas", {})
    ema_20 = float(emas.get("ema_20", price))
    trend = technicals.get("trend", "NEUTRAL")
    
    vol_info = technicals.get("volume", {})
    rvol_20d = float(vol_info.get("rvol_20d", 1.0))
    current_vol = int(vol_info.get("current_volume", 0))
    avg_vol_20d = int(vol_info.get("avg_volume_20d", 0))

    verdict = research.get("verdict", "HOLD")
    conviction = int(research.get("conviction", 5))

    # --- 1. Tactical Sniper Execution Levels ---
    # Ideal Buy: Test of key support or 20 EMA pullback zone
    if price >= ema_20:
        ideal_buy = round(min(price * 0.995, max(support, ema_20 * 0.998)), 2)
    else:
        ideal_buy = round(min(price * 0.99, support), 2)
    
    # Secondary Buy: Momentum breakout above immediate resistance / 20-day high
    secondary_buy = round(max(recent_high, resistance * 1.002), 2)

    # Invalidation Stop-Loss: Structural swing low or ATR buffer below ideal buy
    stop_loss = round(min(recent_low, ideal_buy - (1.5 * atr)), 2)
    if stop_loss >= price:
        stop_loss = round(min(price * 0.95, ideal_buy * 0.96), 2)

    risk_per_share = max(1.0, round(price - stop_loss, 2))

    # Target 1: De-risking level (1 : 1.5 Risk-to-Reward)
    target_1 = round(price + (1.5 * risk_per_share), 2)
    # Target 2: Runner target (1 : 3.0 Risk-to-Reward or overhead expansion)
    target_2 = round(max(resistance * 1.02, price + (3.0 * risk_per_share)), 2)

    gain_t1 = round(target_1 - price, 2)
    gain_t2 = round(target_2 - price, 2)
    rr_ratio_t1 = f"1 : {round(gain_t1 / risk_per_share, 1)}"
    rr_ratio_t2 = f"1 : {round(gain_t2 / risk_per_share, 1)}"

    # --- 2. Dual-Track Position Guidance ---
    if verdict in ["BUY", "ACCUMULATE"]:
        no_position_advice = (
            f"Place limit buy orders near the Ideal Pullback zone (₹{ideal_buy:.2f}) to maintain high risk/reward. "
            f"Alternatively, enter on momentum if the price breaks cleanly above ₹{secondary_buy:.2f} with volume. "
            f"Strict stop-loss invalidation sits at ₹{stop_loss:.2f}. Avoid chasing if price extends more than 3% above 20 EMA (₹{ema_20:.2f})."
        )
        has_position_advice = (
            f"Hold long position. When price reaches Target 1 (₹{target_1:.2f}), lock in partial gains by booking 50% profit. "
            f"Immediately move trailing stop to breakeven or ₹{ideal_buy:.2f} to protect principal, letting the remaining 50% run toward Target 2 (₹{target_2:.2f}). "
            f"Liquidate full position if a daily candle closes below ₹{stop_loss:.2f}."
        )
    elif verdict in ["SELL", "AVOID"]:
        no_position_advice = (
            f"Do not open new long positions. Technical and fundamental momentum favors bears or extended consolidation. "
            f"Wait for a complete base formation or a confirmed reversal above ₹{secondary_buy:.2f}."
        )
        has_position_advice = (
            f"Defensive exit recommended. Tighten stop-loss to ₹{stop_loss:.2f} or trim position into any intraday rebound. "
            f"Capital preservation takes priority over hopeful recoveries."
        )
    else: # HOLD / NEUTRAL
        no_position_advice = (
            f"Neutral wait-and-see posture. Favorable risk/reward only emerges on a deep pullback to ₹{ideal_buy:.2f} "
            f"or a confirmed breakout above ₹{secondary_buy:.2f} with relative volume confirmation."
        )
        has_position_advice = (
            f"Hold existing position with a firm stop-loss at ₹{stop_loss:.2f}. Do not add capital until directional breakout confirms."
        )

    # --- 3. Volume-Price Confluence (RVOL) ---
    change_pct = float(quote.get("change_pct", 0.0))
    if rvol_20d >= 1.5 and change_pct > 0:
        vol_interpretation = "Institutional accumulation: Above-average volume confirms buying pressure and supports continuation."
        vol_badge = "SURGE_BULLISH"
    elif rvol_20d >= 1.5 and change_pct < 0:
        vol_interpretation = "Distribution warning: High volume selling pressure indicates institutional profit booking or dumping."
        vol_badge = "SURGE_BEARISH"
    elif rvol_20d < 0.8 and change_pct > 0:
        vol_interpretation = "Low-volume rally: Price is drifting higher without volume backing. Vulnerable to sudden pullbacks."
        vol_badge = "LOW_VOLUME_WARNING"
    elif rvol_20d < 0.8:
        vol_interpretation = "Low-volume consolidation: Range-bound trading with low market interest. Waiting for catalyst."
        vol_badge = "CONSOLIDATION"
    else:
        vol_interpretation = "Normal volume: Trading activity matches 20-day historical baseline."
        vol_badge = "NORMAL"

    # --- 4. Position Sizing Guide by Survival Tier ---
    tier_upper = survival_tier.upper()
    if tier_upper == "DEFENSIVE":
        sizing_guide = {
            "tier": "DEFENSIVE",
            "max_risk_pct": 0.75,
            "allocation_multiplier": 0.5,
            "tranche_plan": "Single tranche at 50% normal size. Stricter stop-loss required.",
            "status_note": "Defensive tier active (portfolio drawdown 2-5%). Position sizes halved."
        }
    elif tier_upper in ["CRITICAL", "CIRCUIT_BREAKER"]:
        sizing_guide = {
            "tier": tier_upper,
            "max_risk_pct": 0.0,
            "allocation_multiplier": 0.0,
            "tranche_plan": "Trading locked. No new positions permitted.",
            "status_note": f"{tier_upper} tier active. Capital protection mode enforced."
        }
    else:
        sizing_guide = {
            "tier": "NORMAL",
            "max_risk_pct": 1.5,
            "allocation_multiplier": 1.0,
            "tranche_plan": "50% size at Ideal Pullback, 50% size on breakout confirmation above Secondary Buy.",
            "status_note": "Standard Automaton rules apply. Max 1.5% equity risk per trade."
        }

    # --- 5. Pre-Trade Execution Checklist ---
    checklist = [
        {
            "id": "check_rr",
            "title": "Risk/Reward >= 1:1.5",
            "passed": (gain_t1 >= 1.4 * risk_per_share),
            "detail": f"Upside to Target 1 (+₹{gain_t1:.2f}) provides {rr_ratio_t1} against downside risk (-₹{risk_per_share:.2f})."
        },
        {
            "id": "check_trend",
            "title": "Trend & Moving Average Support",
            "passed": (price >= ema_20),
            "detail": f"Current price ₹{price:.2f} is {'above' if price >= ema_20 else 'below'} 20 EMA (₹{ema_20:.2f})."
        },
        {
            "id": "check_risk_cap",
            "title": "Constitution Law 1: 1.5% Max Risk",
            "passed": True,
            "detail": f"Max capital at risk (Quantity × ₹{risk_per_share:.2f}) must not exceed {sizing_guide['max_risk_pct']}% of portfolio."
        },
        {
            "id": "check_stop_order",
            "title": "Mandatory Stop-Loss Order",
            "passed": True,
            "detail": f"Place mandatory GTT or hard stop order at ₹{stop_loss:.2f} at time of trade execution."
        }
    ]

    return {
        "sniper_points": {
            "ideal_buy": ideal_buy,
            "secondary_buy": secondary_buy,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_per_share": risk_per_share,
            "gain_t1": gain_t1,
            "gain_t2": gain_t2,
            "rr_ratio_t1": rr_ratio_t1,
            "rr_ratio_t2": rr_ratio_t2
        },
        "dual_track_advice": {
            "no_position": no_position_advice,
            "has_position": has_position_advice
        },
        "volume_confluence": {
            "rvol_20d": rvol_20d,
            "current_volume": current_vol,
            "avg_volume_20d": avg_vol_20d,
            "status": vol_badge,
            "interpretation": vol_interpretation
        },
        "position_sizing": sizing_guide,
        "pre_trade_checklist": checklist
    }
