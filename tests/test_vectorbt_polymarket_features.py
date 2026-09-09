import unittest
from src.analysis.backtester import run_parameter_sweep
from src.data.macro_data import get_indian_macro_event_probabilities

class TestVectorBTPolymarketFeatures(unittest.TestCase):
    def test_parameter_sweep_grid_generation(self):
        res = run_parameter_sweep(symbol="RELIANCE.NS", period="6mo", initial_capital=100000.0)
        
        self.assertIn("symbol", res)
        self.assertIn("grid_results", res)
        self.assertIn("best_combination", res)
        self.assertIn("summary", res)
        
        # 3 fast [9, 15, 20] * 3 slow [30, 50, 100] = 9 combinations
        self.assertEqual(res["total_combinations_tested"], 9)
        self.assertEqual(len(res["grid_results"]), 9)

        best = res["best_combination"]
        self.assertIn("combo_label", best)
        self.assertIn("net_return_pct", best)
        self.assertIn("sharpe_ratio", best)
        self.assertIn("win_rate_pct", best)

        # Confirm grid is sorted descending by Sharpe / Net Return
        first = res["grid_results"][0]
        self.assertEqual(first["combo_label"], best["combo_label"])

    def test_macro_event_probabilities_structure(self):
        res = get_indian_macro_event_probabilities()
        
        self.assertIn("macro_risk_state", res)
        self.assertIn("catalyst_guidance", res)
        self.assertIn("catalysts", res)
        
        catalysts = res["catalysts"]
        self.assertGreaterEqual(len(catalysts), 4)

        for c in catalysts:
            self.assertIn("id", c)
            self.assertIn("title", c)
            self.assertIn("question", c)
            self.assertIn("implied_probability_pct", c)
            self.assertGreaterEqual(c["implied_probability_pct"], 0.0)
            self.assertLessEqual(c["implied_probability_pct"], 100.0)
            self.assertIn(c["impact_level"], ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
            self.assertIn(c["uncertainty_rating"], ["LOW", "MODERATE", "HIGH"])

        self.assertIn(res["macro_risk_state"], [
            "STABLE_MACRO_REGIME",
            "MODERATE_CATALYST_WATCH",
            "ELEVATED_VOLATILITY_GUARD"
        ])

if __name__ == "__main__":
    unittest.main()
