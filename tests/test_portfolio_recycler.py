import pytest
from src.engine.portfolio_recycler import PortfolioRecycler

@pytest.fixture
def sample_portfolio():
    return {
        "total_portfolio_value": 50000.0,
        "available_cash": 150.0,
        "holdings": [
            {
                "tradingsymbol": "TMCV-EQ",
                "quantity": 38,
                "ltp": 434.55,
                "pnl": 7000.0
            },
            {
                "tradingsymbol": "TEXMOPIPES-EQ",
                "quantity": 345,
                "ltp": 60.08,
                "pnl": 200.0
            },
            {
                "tradingsymbol": "MANAPPURAM-EQ",
                "quantity": 1,
                "ltp": 337.0,
                "pnl": 127.0
            },
            {
                "tradingsymbol": "PNB-EQ",
                "quantity": 1,
                "ltp": 118.0,
                "pnl": 11.0
            },
            {
                "tradingsymbol": "TATASTEEL-EQ",
                "quantity": 1,
                "ltp": 185.0,
                "pnl": 21.0
            },
            {
                "tradingsymbol": "IDFCFIRSTB-EQ",
                "quantity": 13,
                "ltp": 86.5,
                "pnl": -30.0
            }
        ]
    }

def test_audit_portfolio_allocation(sample_portfolio):
    recycler = PortfolioRecycler(max_single_stock_pct=25.0, min_dust_threshold_pct=1.5)
    audit = recycler.audit_portfolio_allocation(sample_portfolio)
    
    assert audit["total_portfolio_value"] == 50000.0
    assert audit["available_cash"] == 150.0
    assert audit["holdings_count"] == 6
    
    # Check overconcentrated detection
    overconcentrated_syms = [p["symbol"] for p in audit["overconcentrated_positions"]]
    assert "TMCV" in overconcentrated_syms or "TEXMOPIPES" in overconcentrated_syms
    
    # Check dust position detection
    dust_syms = [p["symbol"] for p in audit["dust_positions"]]
    assert "PNB" in dust_syms
    assert "TATASTEEL" in dust_syms

def test_recycling_plan_sufficient_cash(sample_portfolio):
    recycler = PortfolioRecycler(max_single_stock_pct=25.0)
    plan = recycler.generate_capital_recycling_plan(
        portfolio_summary=sample_portfolio,
        required_cash=100.0,
        target_symbol="BHEL"
    )
    assert plan["status"] == "SUFFICIENT_CASH"
    assert len(plan["actions_needed"]) == 0

def test_recycling_plan_generates_trims(sample_portfolio):
    recycler = PortfolioRecycler(max_single_stock_pct=25.0)
    plan = recycler.generate_capital_recycling_plan(
        portfolio_summary=sample_portfolio,
        required_cash=4310.0,
        target_symbol="BHEL"
    )
    assert plan["status"] == "RECYCLING_PLAN_READY"
    assert len(plan["actions_needed"]) > 0
    
    total_net = sum(a["net_cash_released"] for a in plan["actions_needed"])
    assert total_net >= (4310.0 - 150.0)
    
    first_action = plan["actions_needed"][0]
    assert first_action["action"] == "TRIM"
    assert first_action["quantity"] > 0
    assert first_action["statutory_friction_inr"] > 0

def test_dust_position_fee_warning(sample_portfolio):
    recycler = PortfolioRecycler(max_single_stock_pct=50.0)
    plan = recycler.generate_capital_recycling_plan(
        portfolio_summary=sample_portfolio,
        required_cash=300.0,
        target_symbol="BEL"
    )
    assert plan["status"] == "RECYCLING_PLAN_READY"
    dust_actions = [a for a in plan["actions_needed"] if a["action"] == "SELL_DUST"]
    if dust_actions:
        assert any(a.get("is_fee_prohibitive") for a in dust_actions)
