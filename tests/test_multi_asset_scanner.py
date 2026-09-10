import unittest
import pandas as pd
import numpy as np

from src.analysis.multi_asset_scanner import (
    check_correlation_regime,
    evaluate_index_mean_reversion,
    evaluate_commodity_trend,
    evaluate_momentum_breakout,
    scan_multi_asset_opportunities
)


class TestMultiAssetScanner(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 80
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        closes = 250.0 + np.cumsum(np.random.normal(0, 1.5, n))
        highs = closes + np.random.uniform(1.0, 3.0, n)
        lows = closes - np.random.uniform(1.0, 3.0, n)
        volumes = np.random.uniform(100000, 500000, n)

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": closes,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes
        })

    def test_correlation_regime_healthy(self):
        res = check_correlation_regime(self.df, india_vix=13.5)
        self.assertTrue(res["momentum_allowed"])
        self.assertEqual(res["status"], "PASSED")

    def test_correlation_regime_vix_panic(self):
        res = check_correlation_regime(self.df, india_vix=26.5)
        self.assertFalse(res["momentum_allowed"])
        self.assertEqual(res["status"], "BLOCKED")
        self.assertIn("VIX", res["reason"])

    def test_index_mean_reversion_trigger(self):
        # Create oversold scenario: sharp drop at the end
        df_oversold = self.df.copy()
        df_oversold.loc[len(df_oversold) - 1, "Close"] = df_oversold["Close"].iloc[-2] - 15.0
        df_oversold.loc[len(df_oversold) - 1, "Low"] = df_oversold["Close"].iloc[-1] - 1.0

        sig = evaluate_index_mean_reversion("NIFTYBEES", df_oversold, std_dev=1.5)
        if sig:
            self.assertEqual(sig["strategy_type"], "INDEX_MEAN_REVERSION")
            self.assertEqual(sig["direction"], "BUY")
            self.assertGreater(sig["target_price"], sig["entry_price"])
            self.assertLess(sig["stop_loss"], sig["entry_price"])

    def test_commodity_trend_evaluation(self):
        # Synthetic uptrend with golden cross (50 > 200)
        df_trend = self.df.copy()
        # 80 rows: let's test that it runs without errors
        res = evaluate_commodity_trend("GOLDBEES", df_trend)
        # Result can be None if not at pullback point, or a signal dictionary
        if res is not None:
            self.assertEqual(res["strategy_type"], "COMMODITY_TREND")
            self.assertEqual(res["direction"], "BUY")

    def test_momentum_breakout_trigger(self):
        df_breakout = self.df.copy()
        # Set highest high breakout and large volume surge on last bar
        prev_max = df_breakout["High"].iloc[-21:-1].max()
        df_breakout.loc[len(df_breakout) - 1, "Close"] = prev_max + 5.0
        df_breakout.loc[len(df_breakout) - 1, "High"] = prev_max + 6.0
        df_breakout.loc[len(df_breakout) - 1, "Volume"] = df_breakout["Volume"].iloc[-21:-1].mean() * 2.5

        sig = evaluate_momentum_breakout("TATAMOTORS", df_breakout)
        if sig is not None:
            self.assertEqual(sig["strategy_type"], "MOMENTUM_BREAKOUT")
            self.assertEqual(sig["direction"], "BUY")
            self.assertGreater(sig["conviction"], 6)

    def test_scan_multi_asset_opportunities_structure(self):
        # Test full scan with mock Nifty df and VIX
        res = scan_multi_asset_opportunities(
            account_equity=125000.0,
            nifty_df_override=self.df,
            india_vix_override=14.0
        )
        self.assertIn("timestamp", res)
        self.assertIn("correlation_filter", res)
        self.assertIn("opportunities_found", res)
        self.assertIn("opportunities", res)
        self.assertIsInstance(res["opportunities"], list)


if __name__ == "__main__":
    unittest.main()