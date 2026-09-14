import unittest
import pandas as pd
import numpy as np
from src.analysis.order_flow import evaluate_liquidity_sweep_setup
from src.analysis.backtester import backtest_strategy


class TestLiquiditySweeps(unittest.TestCase):
    def test_evaluate_liquidity_sweep_setup(self):
        # Create synthetic data with a stop hunt:
        # Range with low at 100, then last candle dips to 98 (sweeping 100) and closes at 102
        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        highs = [105.0] * 19 + [103.0]
        lows = [100.0] * 19 + [98.0]   # pierced below 100.0
        closes = [103.0] * 19 + [102.0] # closed back above 100.0
        opens = [102.0] * 20
        volumes = [1000] * 19 + [3000] # volume spike

        df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes
        })

        res = evaluate_liquidity_sweep_setup(df, swing_lookback=10)
        self.assertEqual(res["setup"], "BULLISH_SSL_SWEEP")
        self.assertEqual(res["swept_level"], 100.0)
        self.assertEqual(res["sweep_low"], 98.0)
        self.assertTrue(res["volume_confirmed"])
        self.assertGreater(res["target_price"], res["entry_price"])
        self.assertLess(res["stop_loss"], res["entry_price"])


if __name__ == "__main__":
    unittest.main()
