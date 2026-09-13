import unittest
import pandas as pd
import numpy as np
from src.analysis.quant_strategies import (
    calculate_connors_rsi2,
    calculate_camarilla_pivots,
    calculate_kunal_saraogi_vip,
    calculate_supertrend_cloud
)
from src.analysis.screener import (
    scan_connors_rsi2_dips,
    scan_camarilla_breakouts,
    scan_kunal_saraogi_vip
)

class TestQuantStrategies(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 100
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.8)
        self.df = pd.DataFrame({
            'Open': p + np.random.randn(n) * 0.2,
            'High': p + np.abs(np.random.randn(n) * 0.7),
            'Low': p - np.abs(np.random.randn(n) * 0.7),
            'Close': p,
            'Volume': np.random.randint(1000, 50000, n).astype(float)
        })

    def test_connors_rsi2(self):
        res = calculate_connors_rsi2(self.df)
        self.assertEqual(res["strategy"], "CONNORS_RSI2")
        self.assertIn("rsi2", res)
        self.assertIn("signal", res)

    def test_camarilla_pivots(self):
        res = calculate_camarilla_pivots(self.df)
        self.assertEqual(res["strategy"], "CAMARILLA_PIVOTS")
        self.assertIn("levels", res)
        self.assertIn("h4", res["levels"])
        self.assertIn("l4", res["levels"])

    def test_kunal_saraogi_vip(self):
        res = calculate_kunal_saraogi_vip(self.df)
        self.assertEqual(res["strategy"], "KUNAL_SARAOGI_VIP")
        self.assertIn("vip_score", res)
        self.assertIn("price_pass", res)

    def test_supertrend_cloud(self):
        res = calculate_supertrend_cloud(self.df)
        self.assertEqual(res["strategy"], "SUPERTREND_CLOUD")
        self.assertIn("is_supertrend_bullish", res)

    def test_scan_camarilla(self):
        res = scan_camarilla_breakouts(limit=5)
        self.assertEqual(res["scan_type"], "CAMARILLA_PIVOT_SCAN")
        self.assertIn("candidates", res)

if __name__ == "__main__":
    unittest.main()
