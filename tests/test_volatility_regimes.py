import unittest
import pandas as pd
import numpy as np
from src.analysis.volatility_regimes import (
    calculate_ttm_squeeze,
    calculate_hvr,
    calculate_cmo,
    calculate_supertrend,
    analyze_volatility_regime
)

class TestVolatilityRegimes(unittest.TestCase):
    def setUp(self):
        np.random.seed(101)
        n = 120
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        closes = 2000.0 + np.cumsum(np.random.normal(0, 15, n))
        highs = closes + np.random.uniform(5, 20, n)
        lows = closes - np.random.uniform(5, 20, n)
        opens = (closes + np.roll(closes, 1)) / 2.0
        opens[0] = closes[0]

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes
        })

    def test_ttm_squeeze(self):
        res = calculate_ttm_squeeze(self.df)
        self.assertIn("squeeze_on", res)
        self.assertIn("squeeze_fired", res)
        self.assertIn("momentum_histogram", res)
        self.assertIn("momentum_direction", res)
        self.assertIsInstance(res["squeeze_on"], bool)

    def test_hvr(self):
        res = calculate_hvr(self.df)
        self.assertIn("hvr", res)
        self.assertIn("coiled_breakout_imminent", res)
        self.assertIn("regime", res)
        self.assertGreater(res["hvr"], 0.0)

    def test_cmo(self):
        cmo = calculate_cmo(self.df['Close'])
        self.assertEqual(len(cmo), len(self.df))
        last_val = cmo.iloc[-1]
        self.assertTrue(-100.0 <= last_val <= 100.0)

    def test_supertrend(self):
        st = calculate_supertrend(self.df)
        self.assertIn("supertrend_price", st)
        self.assertIn("direction", st)
        self.assertIn(st["direction"], ["BULLISH", "BEARISH"])

    def test_analyze_volatility_regime_composite(self):
        res = analyze_volatility_regime(self.df)
        self.assertIn("ttm_squeeze", res)
        self.assertIn("hvr", res)
        self.assertIn("cmo", res)
        self.assertIn("supertrend", res)
        self.assertIn("is_coiling", res)

if __name__ == "__main__":
    unittest.main()
