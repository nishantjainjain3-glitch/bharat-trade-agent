from typing import Dict, Any, List, Optional

CONSTITUTION_ARTICLES = [
    {
        "article": 1,
        "title": "Capital Preservation Mandate",
        "description": "Never risk more than 1.5% of total portfolio equity on any single trade setup. Capital survival precedes return generation.",
        "max_risk_pct": 1.5
    },
    {
        "article": 2,
        "title": "Mandatory Stop-Loss Law",
        "description": "Every position must have a predetermined hard stop-loss registered before entry. Averaging down on losing positions is strictly forbidden.",
        "requires_stop_loss": True
    },
    {
        "article": 3,
        "title": "Macro Trend Alignment",
        "description": "No aggressive long equity allocations when benchmark index (Nifty 50) trades below its long-term 200 EMA regime.",
        "requires_trend_alignment": True
    },
    {
        "article": 4,
        "title": "Risk-to-Reward Threshold",
        "description": "Trade ideas must offer a minimum projected profit-to-risk ratio of 1.5:1. Mediocre asymmetry setups are rejected.",
        "min_risk_reward": 1.5
    },
    {
        "article": 5,
        "title": "Autonomous Transparency & Auditability",
        "description": "Every trade execution, signal cancellation, and tier change must be immutably recorded with technical and fundamental rationales in the reflection journal.",
        "requires_journaling": True
    }
]

def get_constitution_articles() -> List[Dict[str, Any]]:
    """Returns the immutable constitution articles governing agent operations."""
    return CONSTITUTION_ARTICLES

def validate_order_against_constitution(
    symbol: str,
    price: float,
    stop_loss: Optional[float],
    target_price: Optional[float],
    quantity: int,
    portfolio_equity: float,
    nifty_below_200_ema: bool = False
) -> Dict[str, Any]:
    """
    Evaluates an order against the 5 constitutional articles.
    Returns:
        {
            'allowed': bool,
            'violations': List[str],
            'approved_metrics': Dict[str, Any]
        }
    """
    violations = []
    
    if price <= 0 or quantity <= 0:
        return {
            "allowed": False,
            "violations": ["Invalid order dimensions: price and quantity must be positive."],
            "approved_metrics": {}
        }
        
    position_value = price * quantity
    
    # Article 2: Mandatory Stop-Loss
    if stop_loss is None or stop_loss <= 0:
        violations.append("Article II Violation: Every trade must have a hard stop-loss specified before entry.")
    elif stop_loss >= price:
        violations.append("Article II Violation: Long stop-loss must be strictly below current entry price.")
        
    # Article 1: Capital Preservation (Risk <= 1.5% of total portfolio equity)
    if stop_loss and stop_loss < price and portfolio_equity > 0:
        risk_per_share = price - stop_loss
        total_risk_amount = risk_per_share * quantity
        risk_pct_of_portfolio = (total_risk_amount / portfolio_equity) * 100.0
        
        if risk_pct_of_portfolio > 1.5:
            max_allowed_shares = int((portfolio_equity * 0.015) / risk_per_share)
            violations.append(
                f"Article I Violation: Proposed risk is {risk_pct_of_portfolio:.2f}% of equity "
                f"(max allowed is 1.5%). Reduce quantity to {max(1, max_allowed_shares)} shares."
            )
    else:
        risk_per_share = 0.0
        total_risk_amount = 0.0
        risk_pct_of_portfolio = 0.0

    # Article 3: Macro Trend Alignment
    if nifty_below_200_ema:
        violations.append("Article III Violation: Nifty 50 is trading in a bear regime below 200 EMA. Long entries restricted.")

    # Article 4: Risk-Reward Threshold (minimum 1.5)
    rr_ratio = 0.0
    if target_price and target_price > price and risk_per_share > 0:
        reward_per_share = target_price - price
        rr_ratio = round(reward_per_share / risk_per_share, 2)
        if rr_ratio < 1.5:
            violations.append(
                f"Article IV Violation: Risk-to-reward ratio is 1:{rr_ratio} "
                f"(minimum constitutional threshold is 1:1.5)."
            )
            
    is_allowed = len(violations) == 0
    
    return {
        "allowed": is_allowed,
        "violations": violations,
        "approved_metrics": {
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "position_value": round(position_value, 2),
            "stop_loss": stop_loss,
            "target_price": target_price,
            "total_risk_inr": round(total_risk_amount, 2),
            "risk_pct_of_equity": round(risk_pct_of_portfolio, 2),
            "risk_reward_ratio": f"1:{rr_ratio}" if rr_ratio > 0 else "N/A"
        }
    }
