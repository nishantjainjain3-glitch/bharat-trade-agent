import unittest
import pandas as pd
import numpy as np
from src.analysis.hyperopt import freqtrade_loss_objective, simulate_breakout_vectorized


class TestHyperopt(unittest.TestCase):
    def test_freqtrade_loss_objective(self):
        # Good strategy: positive return, high win rate, good PF
        loss_good = freqtrade_loss_objective(
            total_return_pct=30.0,
            max_drawdown_pct=8.0,
            win_rate_pct=60.0,
            total_trades=10,
            profit_factor=3.0
        )
        self.assertLess(loss_good, 0.0)

        # Bad strategy: high drawdown, low trades
        loss_bad = freqtrade_loss_objective(
            total_return_pct=-15.0,
            max_drawdown_pct=25.0,
            win_rate_pct=20.0,
            total_trades=2,
            profit_factor=0.3
        )
        self.assertGreater(loss_bad, 500.0)

    def test_simulate_breakout_vectorized(self):
        # Synthetic trending data
        dates = pd.date_range("2025-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100.0 + np.cumsum(np.random.normal(0.5, 1.2, size=100))
        df = pd.DataFrame({
            "Date": dates,
            "Open": prices - 0.5,
            "High": prices + 1.5,
            "Low": prices - 1.0,
            "Close": prices,
            "Volume": 50000
        })

        res = simulate_breakout_vectorized(
            df,
            lookback_entry=15,
            lookback_exit=10,
            atr_stop_mult=2.0,
            target_mult=3.5,
            rsi_filter=50.0
        )
        self.assertIn("total_return_pct", res)
        self.assertIn("win_rate_pct", res)
        self.assertIn("profit_factor", res)


if __name__ == "__main__":
    unittest.main()
