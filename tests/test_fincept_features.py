import unittest
import math
from src.analysis.personas import (
    evaluate_buffett,
    evaluate_graham,
    evaluate_lynch,
    evaluate_all_investor_personas
)
from src.data.macro_data import get_nse_sector_heatmap

class TestFinceptFeatures(unittest.TestCase):
    def setUp(self):
        self.sample_quote = {
            "symbol": "TCS.NS",
            "name": "Tata Consultancy Services",
            "price": 4000.0
        }
        self.sample_fundamentals = {
            "metrics": {
                "pe_ratio": 28.5,
                "forward_pe": 26.0,
                "price_to_book": 12.0,
                "peg_ratio": 1.8,
                "debt_to_equity": 0.08, # Virtually zero debt
                "roe_pct": 48.0,        # Exceptional ROE
                "profit_margin_pct": 19.5,
                "dividend_yield_pct": 1.4,
                "book_value": 333.3,
                "eps": 140.0
            }
        }

    def test_buffett_evaluation_wide_moat(self):
        res = evaluate_buffett(self.sample_quote, self.sample_fundamentals)
        self.assertEqual(res["persona"], "Warren Buffett")
        self.assertGreaterEqual(res["score"], 70)
        self.assertIn("Moat", res["badge"])
        self.assertIn("ROE", res["rationale"])

    def test_graham_evaluation_graham_number(self):
        eps = 140.0
        bv = 333.3
        expected_graham = round(math.sqrt(22.5 * eps * bv), 2)
        res = evaluate_graham(self.sample_quote, self.sample_fundamentals)
        
        self.assertEqual(res["persona"], "Benjamin Graham")
        self.assertAlmostEqual(res["graham_number"], expected_graham, delta=1.0)
        self.assertIsNotNone(res["margin_of_safety_pct"])

    def test_lynch_evaluation_garp(self):
        # Underpriced fast grower: PEG 0.6
        fast_grower_fund = {
            "metrics": {
                "pe_ratio": 15.0,
                "peg_ratio": 0.6,
                "roe_pct": 25.0
            }
        }
        res = evaluate_lynch(self.sample_quote, fast_grower_fund)
        self.assertEqual(res["persona"], "Peter Lynch")
        self.assertGreaterEqual(res["score"], 75)
        self.assertIn("Fast Grower", res["category"])

    def test_composite_guru_consensus(self):
        comp = evaluate_all_investor_personas(self.sample_quote, self.sample_fundamentals)
        self.assertIn("buffett", comp)
        self.assertIn("graham", comp)
        self.assertIn("lynch", comp)
        self.assertIn("composite_guru_score", comp)
        self.assertIn("consensus_verdict", comp)

    def test_sector_heatmap_data_structure(self):
        res = get_nse_sector_heatmap()
        self.assertIn("sectors", res)
        self.assertGreaterEqual(len(res["sectors"]), 5)
        self.assertIn("top_gaining_sector", res)
        self.assertIn("top_losing_sector", res)
        self.assertIn("market_breadth", res)
        
        first_sector = res["sectors"][0]
        self.assertIn("sector", first_sector)
        self.assertIn("change_pct", first_sector)
        self.assertIn("status", first_sector)

if __name__ == "__main__":
    unittest.main()
