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
    calculate_stock_burner_9_20,
    calculate_cpr_regime,
    calculate_inside_bar_setup,
    calculate_fvg_imbalance,
    calculate_king_multibagger_setup,
    calculate_rsi_divergence_setup
)
from src.analysis.screener import (
    scan_king_5pillar_candidates,
    scan_supply_demand_candidates,
    scan_dark_pool_candidates,
    scan_nifty_pivot_candidates
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

    def test_mandeep_pivot(self):
        res = calculate_mandeep_pivot_9ema(self.df)
        self.assertEqual(res["strategy"], "MANDEEP_9EMA_PIVOT")
        self.assertIn("pivots", res)

    def test_king_research(self):
        res = calculate_king_research_5pillar(self.df)
        self.assertEqual(res["strategy"], "KING_RESEARCH_5PILLAR")
        self.assertIn("confluence_score", res)

    def test_trading_geek(self):
        res = calculate_trading_geek_snd(self.df)
        self.assertEqual(res["strategy"], "TRADING_GEEK_SND")

    def test_dark_pool(self):
        res = calculate_dark_pool_absorption(self.df)
        self.assertEqual(res["strategy"], "DARK_POOL_ABSORPTION")

    def test_tradeiq_ema(self):
        res = calculate_tradeiq_9_21_ema(self.df)
        self.assertEqual(res["strategy"], "TRADEIQ_9_21_EMA")

    def test_stock_burner(self):
        res = calculate_stock_burner_9_20(self.df)
        self.assertEqual(res["strategy"], "STOCK_BURNER_9_20")

    def test_scan_nifty_pivots(self):
        res = scan_nifty_pivot_candidates()
        self.assertEqual(res["scan_type"], "MANDEEP_9EMA_PIVOTS")
        self.assertIn("indices", res)

    def test_cpr_regime(self):
        res = calculate_cpr_regime(self.df)
        self.assertEqual(res["strategy"], "CPR_REGIME")
        self.assertIn("regime", res)
        self.assertIn("width_pct", res)

    def test_inside_bar_setup(self):
        res = calculate_inside_bar_setup(self.df)
        self.assertEqual(res["strategy"], "INSIDE_BAR_BREAKOUT")
        self.assertIn("is_inside_bar_detected", res)

    def test_fvg_imbalance(self):
        res = calculate_fvg_imbalance(self.df)
        self.assertEqual(res["strategy"], "FVG_IMBALANCE")
        self.assertIn("total_unmitigated_fvgs", res)

    def test_king_multibagger(self):
        res = calculate_king_multibagger_setup(self.df)
        self.assertEqual(res["strategy"], "KING_MULTIBAGGER")
        self.assertIn("multibagger_score", res)

    def test_rsi_divergence(self):
        res = calculate_rsi_divergence_setup(self.df)
        self.assertEqual(res["strategy"], "RSI_DIVERGENCE")
        self.assertIn("is_bullish_divergence", res)

if __name__ == "__main__":
    unittest.main()
