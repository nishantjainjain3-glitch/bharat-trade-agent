import unittest
import pandas as pd
import numpy as np
from src.analysis.technical import (
    calculate_fibonacci_retracements,
    detect_candlestick_patterns,
    analyze_technical_indicators
)
from src.analysis.screener import get_preset_screener_recommendations
from src.analysis.sector_rotation import get_sector_rotation_matrix
from src.analysis.backtester import run_parameter_sweep
from src.agents.research_team import calculate_sentiment_velocity


class TestBorrowedWorkflows(unittest.TestCase):
    def test_fibonacci_retracement_math(self):
        high = 100.0
        low = 50.0
        fib = calculate_fibonacci_retracements(high=high, low=low)

        self.assertEqual(fib["0.0%"], 100.0)
        self.assertEqual(fib["100.0%"], 50.0)
        self.assertAlmostEqual(fib["50.0%"], 75.0, places=2)
        self.assertAlmostEqual(fib["61.8%"], 69.1, places=1)
        self.assertAlmostEqual(fib["38.2%"], 80.9, places=1)
        self.assertAlmostEqual(fib["23.6%"], 88.2, places=1)
        self.assertAlmostEqual(fib["78.6%"], 60.7, places=1)

    def test_detect_candlestick_hammer_and_engulfing(self):
        # Create a synthetic dataframe with 5 days
        # Day 4: Bearish candle (Open 100, Close 95, High 101, Low 94)
        # Day 5: Bullish Engulfing (Open 94, Close 102, High 103, Low 93)
        dates = pd.date_range("2026-01-01", periods=5, freq="D")
        df_engulfing = pd.DataFrame({
            "Open": [98.0, 99.0, 97.0, 100.0, 94.0],
            "High": [100.0, 101.0, 99.0, 101.0, 103.0],
            "Low": [96.0, 97.0, 95.0, 94.0, 93.0],
            "Close": [99.0, 97.0, 98.0, 95.0, 102.0],
            "Volume": [1000, 1000, 1000, 1500, 3000]
        }, index=dates)

        patterns = detect_candlestick_patterns(df_engulfing)
        self.assertIn("Bullish Engulfing", patterns)

        # Day 5: Hammer (Open 98, High 98.6, Low 85, Close 98.5) -> long lower wick, tiny body near high
        df_hammer = pd.DataFrame({
            "Open": [100.0, 99.0, 98.0, 97.0, 98.0],
            "High": [102.0, 101.0, 100.0, 99.0, 98.6],
            "Low": [98.0, 97.0, 96.0, 95.0, 85.0],
            "Close": [99.0, 98.0, 97.0, 96.0, 98.5],
            "Volume": [1000, 1000, 1000, 1000, 2500]
        }, index=dates)

        patterns_hammer = detect_candlestick_patterns(df_hammer)
        self.assertTrue(any("Hammer" in p for p in patterns_hammer))

    def test_screener_presets(self):
        for preset in ["ALL", "BREAKOUT", "OVERSOLD", "VALUE"]:
            results = get_preset_screener_recommendations(preset=preset, limit=3)
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            
            first = results[0]
            self.assertIn("symbol", first)
            self.assertIn("name", first)
            self.assertIn("price", first)
            self.assertIn("target_price", first)
            self.assertIn("stop_loss", first)
            self.assertIn("candlestick_pattern", first)
            self.assertIn("dist_52w_high_pct", first)
            self.assertIn("relative_volume", first)

    def test_sector_rotation_rrg(self):
        res = get_sector_rotation_matrix()
        self.assertIn("benchmark", res)
        self.assertEqual(res["benchmark"], "NIFTY 50")
        self.assertIn("quadrant_matrix", res)
        self.assertIn("leading_sector", res)
        self.assertIn("lagging_sector", res)

        matrix = res["quadrant_matrix"]
        for quad in ["LEADING", "IMPROVING", "WEAKENING", "LAGGING"]:
            self.assertIn(quad, matrix)

        sectors = res["sectors"]
        self.assertGreaterEqual(len(sectors), 6)
        for s in sectors:
            self.assertIn("sector", s)
            self.assertIn("rs_ratio", s)
            self.assertIn("rs_momentum", s)
            self.assertIn(s["quadrant"], ["LEADING", "IMPROVING", "WEAKENING", "LAGGING"])
            self.assertIn("action", s)

    def test_backtester_walk_forward_split_and_slippage(self):
        res = run_parameter_sweep(symbol="RELIANCE.NS", period="6mo", initial_capital=100000.0)
        self.assertIn("walk_forward_validation", res)

        wf = res["walk_forward_validation"]
        self.assertIn("in_sample_return_pct", wf)
        self.assertIn("out_of_sample_return_pct", wf)
        self.assertIn("robustness_ratio", wf)
        self.assertIn("walk_forward_verdict", wf)
        self.assertIn(wf["walk_forward_verdict"], ["ROBUST", "MODERATE", "OVERFITTED"])
        self.assertEqual(wf["slippage_per_leg_pct"], 0.05)

    def test_sentiment_velocity(self):
        headlines = [
            "Reliance Q3 profits surge beating all analyst expectations strongly",
            "Brokerages issue unanimous upgrade citing margin expansion",
            "Market consolidates in sideways range ahead of policy"
        ]
        velocity = calculate_sentiment_velocity(headlines)
        self.assertIn("ACCELERATING_BULLISH", velocity)


if __name__ == "__main__":
    unittest.main()
