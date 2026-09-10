import unittest
import pandas as pd
import numpy as np

from src.engine.position_sizer import calculate_atr, calculate_volatility_parity_position


class TestPositionSizer(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 50
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        closes = 1000.0 + np.cumsum(np.random.normal(0, 10, n))
        highs = closes + np.random.uniform(5, 15, n)
        lows = closes - np.random.uniform(5, 15, n)
        opens = closes + np.random.uniform(-2, 2, n)
        self.df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes
        })

    def test_calculate_atr(self):
        atr = calculate_atr(self.df, period=14)
        self.assertGreater(atr, 0.0)
        self.assertIsInstance(atr, float)

        # Empty / tiny dataframe fallback
        self.assertEqual(calculate_atr(None), 0.0)
        self.assertEqual(calculate_atr(pd.DataFrame()), 0.0)

    def test_volatility_parity_basic_sizing(self):
        # Account Equity = 100,000, Price = 1000, ATR = 20
        # 1% risk = 1000 INR
        # 2x ATR stop = 40 INR stop distance
        # Target shares = 1000 / 40 = 25 shares
        res = calculate_volatility_parity_position(
            account_equity=100000.0,
            current_price=1000.0,
            atr=20.0,
            risk_pct=0.01,
            atr_stop_multiple=2.0,
            target_rr_ratio=2.0,
            tier_multiplier=1.0,
            available_cash=50000.0
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["quantity"], 25)
        self.assertEqual(res["stop_loss"], 960.0)
        self.assertEqual(res["target_price"], 1080.0)
        self.assertEqual(res["risk_per_share"], 40.0)
        self.assertEqual(res["total_risk_inr"], 1000.0)
        self.assertAlmostEqual(res["risk_pct_actual"], 0.01, places=3)
        self.assertEqual(res["allocation_inr"], 25000.0)

    def test_volatility_parity_defensive_tier_halving(self):
        # In DEFENSIVE mode (tier_multiplier=0.5), dollar risk is cut in half: 500 INR
        # Shares = 500 / 40 = 12 shares
        res = calculate_volatility_parity_position(
            account_equity=100000.0,
            current_price=1000.0,
            atr=20.0,
            risk_pct=0.01,
            atr_stop_multiple=2.0,
            tier_multiplier=0.5,
            available_cash=50000.0
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["quantity"], 12)
        self.assertEqual(res["total_risk_inr"], 480.0)

    def test_volatility_parity_critical_tier_blocks(self):
        # In CRITICAL mode (multiplier=0.0), trading is blocked
        res = calculate_volatility_parity_position(
            account_equity=100000.0,
            current_price=1000.0,
            atr=20.0,
            tier_multiplier=0.0
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["quantity"], 0)
        self.assertIn("blocked", res["reason"].lower())

    def test_insufficient_cash_blocks(self):
        # Available cash = 500 INR, Price = 1000 INR
        res = calculate_volatility_parity_position(
            account_equity=100000.0,
            current_price=1000.0,
            atr=20.0,
            available_cash=500.0
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["quantity"], 0)


if __name__ == "__main__":
    unittest.main()