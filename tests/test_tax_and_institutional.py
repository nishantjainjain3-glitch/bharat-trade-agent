import pytest
from src.engine.tax_calculator import calculate_trade_costs, is_trade_asymmetric_after_costs
from src.data.fii_dii import get_fii_dii_activity
from src.engine.risk_tiers import evaluate_survival_tier, SurvivalTier


def test_calculate_trade_costs_structure():
    costs = calculate_trade_costs(buy_price=100.0, sell_price=110.0, quantity=50)
    assert costs["gross_pnl"] == 500.0
    assert costs["total_charges"] > 0
    assert costs["net_pnl"] < costs["gross_pnl"]
    assert "stt" in costs["breakdown"]
    assert "dp_charges" in costs["breakdown"]
    assert costs["breakdown"]["dp_charges"] == 15.93


def test_fee_drag_rejection_on_tiny_trade():
    """A Rs 100 trade gaining Rs 10 should be rejected due to massive fee drag from Rs 15.93 DP charge."""
    asym = is_trade_asymmetric_after_costs(entry_price=100.0, target_price=110.0, stop_loss=95.0, quantity=1)
    assert asym["passed"] is False
    assert asym["fee_drag_pct"] > 20.0


def test_asymmetric_trade_passes():
    """A Rs 10,000 trade gaining Rs 1,000 (10%) with Rs 400 risk (4%) should pass asymmetry test."""
    asym = is_trade_asymmetric_after_costs(entry_price=100.0, target_price=110.0, stop_loss=96.0, quantity=100)
    assert asym["passed"] is True
    assert asym["net_reward_risk"] >= 1.5


def test_fii_dii_activity_structure():
    data = get_fii_dii_activity()
    assert "fii_net_crores" in data
    assert "dii_net_crores" in data
    assert "institutional_regime" in data
    assert "position_size_multiplier" in data
    assert data["institutional_regime"] in ("STRONG_ACCUMULATION", "MODERATE_INFLOW", "FII_DISTRIBUTION", "NET_OUTFLOW", "NEUTRAL")


def test_daily_drawdown_circuit_breaker_tripped():
    """If daily loss hits -2.0% or drawdown hits 6.0%, CIRCUIT_BREAKER must trigger immediately."""
    tier_info = evaluate_survival_tier(
        current_equity=48000.0,
        peak_equity=50000.0,
        daily_pnl_pct=-2.1
    )
    assert tier_info["tier"] == SurvivalTier.CIRCUIT_BREAKER.value
    assert tier_info["trading_allowed"] is False
    assert tier_info["position_size_multiplier"] == 0.0
