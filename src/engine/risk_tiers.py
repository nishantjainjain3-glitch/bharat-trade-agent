from enum import Enum
from typing import Dict, Any

class SurvivalTier(str, Enum):
    NORMAL = "NORMAL"
    DEFENSIVE = "DEFENSIVE"
    CRITICAL = "CRITICAL"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"

TIER_METADATA = {
    SurvivalTier.NORMAL: {
        "title": "Normal Operations",
        "badge_color": "#10b981", # Green
        "position_size_multiplier": 1.0,
        "min_conviction_score": 60,
        "trading_allowed": True,
        "description": "Portfolio equity near peak. Full tactical allocation (100% position sizing) permitted."
    },
    SurvivalTier.DEFENSIVE: {
        "title": "Defensive Capital Mode",
        "badge_color": "#f59e0b", # Amber
        "position_size_multiplier": 0.5,
        "min_conviction_score": 70,
        "trading_allowed": True,
        "description": "Moderate drawdown or macro headwind detected. Position sizes reduced by 50% and higher setup conviction required."
    },
    SurvivalTier.CRITICAL: {
        "title": "Capital Preservation Lock",
        "badge_color": "#ef4444", # Red
        "position_size_multiplier": 0.0,
        "min_conviction_score": 100,
        "trading_allowed": False,
        "description": "Severe market turbulence or portfolio drawdown. New buy allocations are locked. Existing stops tightened."
    },
    SurvivalTier.CIRCUIT_BREAKER: {
        "title": "Emergency Circuit Breaker",
        "badge_color": "#881337", # Dark Red
        "position_size_multiplier": 0.0,
        "min_conviction_score": 100,
        "trading_allowed": False,
        "description": "Daily loss threshold breached. All autonomous trading operations are fully suspended."
    }
}

def evaluate_survival_tier(
    current_equity: float,
    peak_equity: float,
    nifty_day_change_pct: float = 0.0,
    daily_pnl_pct: float = 0.0
) -> Dict[str, Any]:
    """
    Computes current survival tier based on portfolio health and macro conditions.
    """
    if peak_equity <= 0:
        peak_equity = max(current_equity, 100000.0)
        
    drawdown_pct = max(0.0, ((peak_equity - current_equity) / peak_equity) * 100.0)
    
    # Circuit Breaker: Daily loss exceeds 6% or overall drawdown exceeds 10%
    if daily_pnl_pct <= -6.0 or drawdown_pct >= 10.0:
        active_tier = SurvivalTier.CIRCUIT_BREAKER
        trigger_reason = f"Drawdown reached {drawdown_pct:.1f}% / Daily loss {daily_pnl_pct:.1f}%."
    # Critical: Drawdown between 5% and 10%, or benchmark index is down worse than -2.5%
    elif drawdown_pct >= 5.0 or nifty_day_change_pct <= -2.5:
        active_tier = SurvivalTier.CRITICAL
        trigger_reason = f"High risk environment: Drawdown {drawdown_pct:.1f}% or Nifty down {nifty_day_change_pct:.2f}%."
    # Defensive: Drawdown between 2% and 5%, or benchmark index is down -1.0% to -2.5%
    elif drawdown_pct >= 2.0 or nifty_day_change_pct <= -1.0:
        active_tier = SurvivalTier.DEFENSIVE
        trigger_reason = f"Defensive buffer: Drawdown {drawdown_pct:.1f}% or Nifty down {nifty_day_change_pct:.2f}%."
    # Normal: Portfolio healthy
    else:
        active_tier = SurvivalTier.NORMAL
        trigger_reason = "Capital reserves healthy and macro conditions stable."
        
    meta = TIER_METADATA[active_tier]
    
    return {
        "tier": active_tier.value,
        "title": meta["title"],
        "badge_color": meta["badge_color"],
        "position_size_multiplier": meta["position_size_multiplier"],
        "min_conviction_score": meta["min_conviction_score"],
        "trading_allowed": meta["trading_allowed"],
        "description": meta["description"],
        "trigger_reason": trigger_reason,
        "drawdown_pct": round(drawdown_pct, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "nifty_day_change_pct": round(nifty_day_change_pct, 2),
        "current_equity": round(current_equity, 2),
        "peak_equity": round(peak_equity, 2)
    }
