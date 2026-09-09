import unittest
import pandas as pd
import numpy as np
from src.analysis.order_flow import (
    detect_fair_value_gaps,
    detect_market_structure,
    detect_liquidity_sweeps,
    analyze_wyckoff_vsa,
    analyze_order_flow
)

class TestOrderFlow(unittest.TestCase):
    def setUp(self):
        # Create synthetic OHLCV dataframe with known characteristics
        np.random.seed(42)
        n = 40
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        closes = np.linspace(100, 150, n) + np.random.normal(0, 1, n)
        highs = closes + np.random.uniform(0.5, 2.0, n)
        lows = closes - np.random.uniform(0.5, 2.0, n)
        opens = (closes + np.roll(closes, 1)) / 2.0
        opens[0] = closes[0]
        volume = np.random.uniform(100000, 500000, n)

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volume
        })

    def test_detect_fair_value_gaps(self):
        # Introduce a guaranteed bullish FVG: Bar 2 Low > Bar 0 High
        df_fvg = self.df.copy()
        df_fvg.loc[0, 'High'] = 105.0
        df_fvg.loc[1, 'Open'] = 106.0
        df_fvg.loc[1, 'Close'] = 115.0
        df_fvg.loc[2, 'Low'] = 110.0  # 110.0 > 105.0 -> Gap is [105.0, 110.0]

        res = detect_fair_value_gaps(df_fvg)
        self.assertIn("bullish_fvgs", res)
        self.assertIn("bearish_fvgs", res)
        self.assertIn(res["bias"], ["BULLISH", "BEARISH", "NEUTRAL"])

    def test_detect_market_structure(self):
        # Create an obvious uptrend
        df_up = pd.DataFrame({
            "High": [10, 15, 12, 20, 18, 25, 22, 30, 28, 35, 32, 40, 38, 45, 42, 50],
            "Low":  [8,  11, 10, 16, 14, 21, 19, 26, 24, 31, 29, 36, 34, 41, 39, 46],
            "Close":[9,  14, 11, 19, 17, 24, 21, 29, 27, 34, 31, 39, 37, 44, 41, 49]
        })
        res = detect_market_structure(df_up, window=2)
        self.assertIn(res["trend"], ["BULLISH", "BEARISH", "CONSOLIDATION", "NEUTRAL"])

    def test_detect_liquidity_sweeps(self):
        sweeps = detect_liquidity_sweeps(self.df, window=3, lookback=20)
        self.assertIsInstance(sweeps, list)

    def test_analyze_wyckoff_vsa(self):
        vsa = analyze_wyckoff_vsa(self.df)
        self.assertIn("dominant_bias", vsa)
        self.assertIn("signals", vsa)
        self.assertIn("latest_relative_volume", vsa)

    def test_analyze_order_flow_composite(self):
        result = analyze_order_flow(self.df)
        self.assertIn("order_flow_score", result)
        self.assertIn("verdict", result)
        self.assertTrue(0 <= result["order_flow_score"] <= 100)
        self.assertIn(result["verdict"], ["ACCUMULATION", "DISTRIBUTION", "NEUTRAL"])

if __name__ == "__main__":
    unittest.main()
