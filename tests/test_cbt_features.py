import unittest
import pandas as pd
import numpy as np
from src.analysis.backtester import (
    calculate_indian_trade_charges,
    calculate_risk_adjusted_ratios,
    run_monte_carlo_simulation
)

class TestCBTFeatures(unittest.TestCase):
    def test_indian_trade_charges_structure(self):
        buy_val = 50000.0
        sell_val = 55000.0
        charges = calculate_indian_trade_charges(buy_val, sell_val)
        
        turnover = buy_val + sell_val # 105,000 INR
        self.assertEqual(charges["turnover"], turnover)
        
        # STT is 0.1% on buy + 0.1% on sell (105 INR)
        self.assertEqual(charges["stt"], 105.0)
        
        # Stamp duty is 0.015% on buy value (7.50 INR)
        self.assertEqual(charges["stamp_duty"], 7.50)
        
        # Brokerage should be capped at 20 per leg (max 40 INR)
        self.assertLessEqual(charges["brokerage"], 40.0)
        
        # Slippage is 0.05% of turnover (52.50 INR)
        self.assertEqual(charges["slippage"], 52.50)
        
        # Total charges should be positive and greater than STT
        self.assertGreater(charges["total_charges"], charges["stt"])

    def test_risk_adjusted_ratios_positive_returns(self):
        # 100 daily returns with positive drift (+0.1% per day, std 1%)
        rng = np.random.default_rng(seed=123)
        returns = pd.Series(rng.normal(0.0015, 0.008, 100))
        ratios = calculate_risk_adjusted_ratios(returns, risk_free_rate_annual=0.07)
        
        self.assertIn("sharpe_ratio", ratios)
        self.assertIn("sortino_ratio", ratios)
        self.assertIn("annualized_volatility_pct", ratios)
        self.assertGreater(ratios["annualized_volatility_pct"], 0)

    def test_monte_carlo_simulation_bounds(self):
        # 20 trade PnLs
        trades = [2.5, -1.2, 3.8, -0.8, 1.9, -1.5, 4.0, -2.1, 1.2, -0.5, 
                  3.1, -1.0, 2.2, -1.8, 0.9, -0.4, 2.7, -1.1, 1.5, -0.9]
        mc = run_monte_carlo_simulation(trades, initial_capital=100000.0, runs=500)
        
        self.assertEqual(mc["simulated_runs_count"], 500)
        self.assertGreaterEqual(mc["median_drawdown_pct"], 0.0)
        self.assertGreaterEqual(mc["var_95_drawdown_pct"], mc["median_drawdown_pct"])
        self.assertGreaterEqual(mc["risk_of_ruin_pct"], 0.0)
        self.assertLessEqual(mc["risk_of_ruin_pct"], 100.0)

if __name__ == "__main__":
    unittest.main()
