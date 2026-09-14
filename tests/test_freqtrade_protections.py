import unittest
import os
import tempfile
from src.engine.protections import FreqtradeProtectionManager


class TestFreqtradeProtections(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.temp_dir, "test_cooldowns.json")
        self.mgr = FreqtradeProtectionManager(storage_path=self.storage_file)

    def test_cooldown_set_and_check(self):
        self.mgr.set_cooldown("BHEL", hours=2.0, reason="Test Cooldown")
        in_cd, reason = self.mgr.is_in_cooldown("BHEL")
        self.assertTrue(in_cd)
        self.assertIn("Test Cooldown", reason)

        # Clear cooldown
        self.mgr.clear_cooldown("BHEL")
        in_cd2, _ = self.mgr.is_in_cooldown("BHEL")
        self.assertFalse(in_cd2)

    def test_stoploss_guard_trigger(self):
        # 1st hit -> should not trigger cooldown
        trig1 = self.mgr.record_stoploss_hit("TMCV", exit_price=410.0, loss_pct=-2.5)
        self.assertFalse(trig1)
        in_cd, _ = self.mgr.is_in_cooldown("TMCV")
        self.assertFalse(in_cd)

        # 2nd hit within 5 days -> triggers StoplossGuard 72h cooldown
        trig2 = self.mgr.record_stoploss_hit("TMCV", exit_price=405.0, loss_pct=-3.0)
        self.assertTrue(trig2)
        in_cd2, reason2 = self.mgr.is_in_cooldown("TMCV")
        self.assertTrue(in_cd2)
        self.assertIn("StoplossGuard", reason2)

    def test_entry_protections_evaluation(self):
        # Healthy state
        eval1 = self.mgr.evaluate_entry_protections("BEL", current_equity=100000.0, peak_equity=100000.0)
        self.assertTrue(eval1["allowed"])

        # Severe drawdown violation
        eval2 = self.mgr.evaluate_entry_protections("BEL", current_equity=94000.0, peak_equity=100000.0)
        self.assertFalse(eval2["allowed"])
        self.assertTrue(any("MAX_DRAWDOWN" in v for v in eval2["violations"]))

        # Daily loss violation
        eval3 = self.mgr.evaluate_entry_protections("BEL", current_equity=99000.0, peak_equity=100000.0, daily_loss_pct=-2.5)
        self.assertFalse(eval3["allowed"])
        self.assertTrue(any("DAILY_LOSS" in v for v in eval3["violations"]))


if __name__ == "__main__":
    unittest.main()
