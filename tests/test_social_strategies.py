import unittest
import pandas as pd
import numpy as np
from src.analysis.social_strategies import (
    calculate_mamba_fx_setup,
    calculate_mandeep_pivot_9ema,
    calculate_king_research_5pillar,
    calculate_trading_geek_snd,
    calculate_dark_pool_absorption,
    calculate_tradeiq_9_21_ema,
    calculate_stock_burner_9_20
)

class TestSocialStrategies(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 100
        prices = 100.0 + np.cumsum(np.random.randn(n) * 0.8)
        self.df = pd.DataFrame({
            'Open': prices + np.random.randn(n) * 0.2,
            'High': prices + np.abs(np.random.randn(n) * 0.7),
            'Low': prices - np.abs(np.random.randn(n) * 0.7),
            'Close': prices,
            'Volume': np.random.randint(1000, 50000, n).astype(float)
        })

    def test_mamba_fx(self):
        res = calculate_mamba_fx_setup(self.df)
        self.assertEqual(res["strategy"], "MAMBA_FX_SCALPER")
        self.assertIn("signal", res)
        self.assertIn(res["signal"], ["BUY", "SELL", "HOLD"])

    def test_mandeep_pivot(self):
        res = calculate_mandeep_pivot_9ema(self.df)
        self.assertEqual(res["strategy"], "MANDEEP_9EMA_PIVOT")
        self.assertIn("pivots", res)
        self.assertIn("pp", res["pivots"])

    def test_king_research(self):
        res = calculate_king_research_5pillar(self.df)
        self.assertEqual(res["strategy"], "KING_RESEARCH_5PILLAR")
        self.assertIn("confluence_score", res)
        self.assertIn("bullish_pillars", res)

    def test_trading_geek(self):
        res = calculate_trading_geek_snd(self.df)
        self.assertEqual(res["strategy"], "TRADING_GEEK_SND")
        self.assertIn("total_demand_zones", res)
        self.assertIn("total_supply_zones", res)

    def test_dark_pool(self):
        res = calculate_dark_pool_absorption(self.df)
        self.assertEqual(res["strategy"], "DARK_POOL_ABSORPTION")
        self.assertIn("total_absorption_events_found", res)

    def test_tradeiq_ema(self):
        res = calculate_tradeiq_9_21_ema(self.df)
        self.assertEqual(res["strategy"], "TRADEIQ_9_21_EMA")
        self.assertIn("signal", res)

    def test_stock_burner(self):
        res = calculate_stock_burner_9_20(self.df)
        self.assertEqual(res["strategy"], "STOCK_BURNER_9_20")
        self.assertIn("signal", res)

if __name__ == "__main__":
    unittest.main()
