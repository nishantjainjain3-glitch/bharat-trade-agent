import unittest
import tempfile
import shutil
import os
from src.engine.constitution import (
    get_constitution_articles,
    validate_order_against_constitution
)
from src.engine.risk_tiers import evaluate_survival_tier, SurvivalTier
from src.engine.memory import AgentMemoryJournal
from src.engine.heartbeat import AutonomousHeartbeat

class TestAutomatonEngine(unittest.TestCase):
    def test_constitution_articles_count(self):
        articles = get_constitution_articles()
        self.assertEqual(len(articles), 5)
        self.assertEqual(articles[0]["article"], 1)
        self.assertIn("Capital Preservation", articles[0]["title"])

    def test_constitution_order_validation_approved(self):
        res = validate_order_against_constitution(
            symbol="INFY.NS",
            price=100.0,
            stop_loss=95.0,
            target_price=110.0,
            quantity=10,
            portfolio_equity=100000.0
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(len(res["violations"]), 0)
        self.assertEqual(res["approved_metrics"]["risk_reward_ratio"], "1:2.0")

    def test_constitution_order_validation_rejected_excess_risk(self):
        res = validate_order_against_constitution(
            symbol="TCS.NS",
            price=100.0,
            stop_loss=80.0,
            target_price=150.0,
            quantity=100,
            portfolio_equity=100000.0
        )
        self.assertFalse(res["allowed"])
        self.assertTrue(any("Article I Violation" in v for v in res["violations"]))

    def test_constitution_order_validation_rejected_bad_risk_reward(self):
        res = validate_order_against_constitution(
            symbol="RELIANCE.NS",
            price=100.0,
            stop_loss=90.0,
            target_price=105.0,
            quantity=10,
            portfolio_equity=100000.0
        )
        self.assertFalse(res["allowed"])
        self.assertTrue(any("Article IV Violation" in v for v in res["violations"]))

    def test_survival_tier_transitions(self):
        t1 = evaluate_survival_tier(current_equity=100000.0, peak_equity=100000.0, nifty_day_change_pct=0.2)
        self.assertEqual(t1["tier"], SurvivalTier.NORMAL.value)
        self.assertEqual(t1["position_size_multiplier"], 1.0)

        t2 = evaluate_survival_tier(current_equity=97000.0, peak_equity=100000.0, nifty_day_change_pct=-0.5)
        self.assertEqual(t2["tier"], SurvivalTier.DEFENSIVE.value)
        self.assertEqual(t2["position_size_multiplier"], 0.5)

        t3 = evaluate_survival_tier(current_equity=93000.0, peak_equity=100000.0, nifty_day_change_pct=-1.0)
        self.assertEqual(t3["tier"], SurvivalTier.CRITICAL.value)
        self.assertFalse(t3["trading_allowed"])

        t4 = evaluate_survival_tier(current_equity=88000.0, peak_equity=100000.0, nifty_day_change_pct=0.0)
        self.assertEqual(t4["tier"], SurvivalTier.CIRCUIT_BREAKER.value)
        self.assertFalse(t4["trading_allowed"])

    def test_memory_journal(self):
        temp_dir = tempfile.mkdtemp()
        try:
            journal_path = os.path.join(temp_dir, "test_journal.json")
            journal = AgentMemoryJournal(storage_path=journal_path)
            entry = journal.record_entry("TEST", "Test Observation", "Testing memory journal record.")
            self.assertGreater(entry["id"], 0)
            self.assertGreater(len(journal.get_recent_entries()), 0)
            
            reflection = journal.record_reflection("NTPC.NS", "TARGET_HIT", 4.5, "EMA 20 bounce momentum")
            self.assertEqual(reflection["category"], "REFLECTION")
            self.assertIn("NTPC.NS", reflection["title"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_heartbeat_status(self):
        hb = AutonomousHeartbeat(interval_seconds=30)
        status = hb.get_status()
        self.assertIn("market_session", status)
        self.assertIn("survival_tier", status)
        self.assertEqual(len(status["constitution_articles"]), 5)

if __name__ == "__main__":
    unittest.main()
