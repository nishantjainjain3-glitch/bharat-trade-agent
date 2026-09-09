from typing import Dict, Any, Optional

DEFAULT_MINIMAL_ROI_TABLE: Dict[int, float] = {
    0: 4.0,  # Days 0 - 1: Target +4.0%
    2: 2.5,  # Days 2 - 4: Target +2.5%
    5: 1.2   # Days 5+: Target +1.2% (Covers statutory Indian taxes & frees capital)
}

DEFAULT_TRAILING_STOP_CONFIG = {
    "activation_profit_pct": 1.5,  # Trailing stop only activates after +1.5% profit
    "trailing_distance_pct": 1.0   # Trails 1.0% below the highest peak price reached
}

def compute_positive_trailing_stop(
    entry_price: float,
    current_price: float,
    highest_price: float,
    initial_stop_loss: float,
    activation_profit_pct: float = 1.5,
    trailing_distance_pct: float = 1.0
) -> Dict[str, Any]:
    if entry_price <= 0:
        return {
            "effective_stop_loss": initial_stop_loss,
            "is_trailing_active": False,
            "highest_price": highest_price,
            "max_profit_pct": 0.0
        }

    peak = max(highest_price, current_price, entry_price)
    max_profit_pct = round(((peak - entry_price) / entry_price) * 100, 2)
    
    is_trailing_active = max_profit_pct >= activation_profit_pct
    
    if is_trailing_active:
        calculated_trail = round(peak * (1.0 - (trailing_distance_pct / 100.0)), 2)
        effective_stop = max(initial_stop_loss, calculated_trail)
    else:
        effective_stop = initial_stop_loss

    return {
        "effective_stop_loss": round(effective_stop, 2),
        "is_trailing_active": is_trailing_active,
        "highest_price": round(peak, 2),
        "max_profit_pct": max_profit_pct,
        "activation_profit_pct": activation_profit_pct,
        "trailing_distance_pct": trailing_distance_pct,
        "rule_description": f"Trailing stop engages after +{activation_profit_pct}% gain, trailing {trailing_distance_pct}% below highest price."
    }

def evaluate_minimal_roi_exit(
    entry_price: float,
    current_price: float,
    holding_days: int,
    roi_table: Optional[Dict[int, float]] = None
) -> Dict[str, Any]:
    if entry_price <= 0:
        return {
            "should_exit": False,
            "current_profit_pct": 0.0,
            "active_target_roi_pct": 0.0,
            "holding_days": holding_days
        }

    table = roi_table or DEFAULT_MINIMAL_ROI_TABLE
    current_profit_pct = round(((current_price - entry_price) / entry_price) * 100, 2)
    
    active_target = 4.0
    for day_threshold in sorted(table.keys(), reverse=True):
        if holding_days >= day_threshold:
            active_target = table[day_threshold]
            break

    should_exit = current_profit_pct >= active_target
    
    if should_exit:
        reason = f"Holding for {holding_days} days reached decaying target of +{active_target}% with current gain of +{current_profit_pct}%."
    else:
        reason = f"Day {holding_days} target (+{active_target}%) not reached. Current return: {current_profit_pct}%."

    return {
        "should_exit": should_exit,
        "current_profit_pct": current_profit_pct,
        "active_target_roi_pct": active_target,
        "holding_days": holding_days,
        "reason": reason
    }

def get_default_exit_rules() -> Dict[str, Any]:
    return {
        "minimal_roi_table": [
            {"days": "Days 0 - 1", "min_holding_days": 0, "target_profit_pct": 4.0, "purpose": "Quick momentum surge capture"},
            {"days": "Days 2 - 4", "min_holding_days": 2, "target_profit_pct": 2.5, "purpose": "Standard swing target"},
            {"days": "Days 5+", "min_holding_days": 5, "target_profit_pct": 1.2, "purpose": "Time-decay exit (frees capital above statutory taxes)"}
        ],
        "positive_trailing_stop": {
            "activation_profit_pct": DEFAULT_TRAILING_STOP_CONFIG["activation_profit_pct"],
            "trailing_distance_pct": DEFAULT_TRAILING_STOP_CONFIG["trailing_distance_pct"],
            "description": "Stationary stop at trade entry. Trails 1.0% below peak only after +1.5% profit is achieved."
        }
    }
