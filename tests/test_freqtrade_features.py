import unittest
from src.engine.exit_manager import (
    compute_positive_trailing_stop,
    evaluate_minimal_roi_exit,
    get_default_exit_rules
)
from src.analysis.backtester import backtest_strategy

class TestFreqtradeFeatures(unittest.TestCase):
    def test_positive_trailing_stop_inactive_below_threshold(self):
        # Entry 100, peak 101 (+1.0%), activation 1.5% -> should remain at initial SL
        res = compute_positive_trailing_stop(
            entry_price=100.0,
            current_price=101.0,
            highest_price=101.0,
            initial_stop_loss=95.0,
            activation_profit_pct=1.5,
            trailing_distance_pct=1.0
        )
        self.assertFalse(res["is_trailing_active"])
        self.assertEqual(res["effective_stop_loss"], 95.0)
        self.assertEqual(res["max_profit_pct"], 1.0)

    def test_positive_trailing_stop_active_above_threshold(self):
        # Entry 100, peak 104 (+4.0%), activation 1.5% -> trailing engages at 104 * 0.99 = 102.96
        res = compute_positive_trailing_stop(
            entry_price=100.0,
            current_price=103.5,
            highest_price=104.0,
            initial_stop_loss=95.0,
            activation_profit_pct=1.5,
            trailing_distance_pct=1.0
        )
        self.assertTrue(res["is_trailing_active"])
        self.assertEqual(res["effective_stop_loss"], 102.96)
        self.assertEqual(res["highest_price"], 104.0)

    def test_minimal_roi_exit_decay_ladder(self):
        # Day 1: Target is +4.0%
        res_d1_low = evaluate_minimal_roi_exit(entry_price=100.0, current_price=103.0, holding_days=1)
        self.assertFalse(res_d1_low["should_exit"])
        self.assertEqual(res_d1_low["active_target_roi_pct"], 4.0)

        res_d1_high = evaluate_minimal_roi_exit(entry_price=100.0, current_price=104.5, holding_days=1)
        self.assertTrue(res_d1_high["should_exit"])

        # Day 3: Target decays to +2.5%
        res_d3 = evaluate_minimal_roi_exit(entry_price=100.0, current_price=102.8, holding_days=3)
        self.assertTrue(res_d3["should_exit"])
        self.assertEqual(res_d3["active_target_roi_pct"], 2.5)

        # Day 6: Target decays to +1.2% (above taxes)
        res_d6_pass = evaluate_minimal_roi_exit(entry_price=100.0, current_price=101.4, holding_days=6)
        self.assertTrue(res_d6_pass["should_exit"])
        self.assertEqual(res_d6_pass["active_target_roi_pct"], 1.2)

        res_d6_fail = evaluate_minimal_roi_exit(entry_price=100.0, current_price=100.8, holding_days=6)
        self.assertFalse(res_d6_fail["should_exit"])

    def test_default_exit_rules_payload(self):
        rules = get_default_exit_rules()
        self.assertIn("minimal_roi_table", rules)
        self.assertIn("positive_trailing_stop", rules)
        self.assertEqual(len(rules["minimal_roi_table"]), 3)
        self.assertEqual(rules["positive_trailing_stop"]["activation_profit_pct"], 1.5)

    def test_backtester_trade_expectancy(self):
        bt = backtest_strategy(symbol="RELIANCE.NS", strategy_name="EMA_CROSS", period="6mo", initial_capital=100000.0)
        self.assertIn("trade_expectancy_inr", bt)
        self.assertIn("expectancy_ratio", bt)
        self.assertIn("edge_status", bt)
        self.assertIn(bt["edge_status"], ["POSITIVE_EDGE", "NEGATIVE_EDGE"])

        # Verify mathematical consistency
        if bt["total_trades"] > 0 and bt["winning_trades"] > 0 and bt["losing_trades"] > 0:
            win_rate = bt["winning_trades"] / bt["total_trades"]
            loss_rate = bt["losing_trades"] / bt["total_trades"]
            expected = round((win_rate * bt["avg_win_inr"]) - (loss_rate * bt["avg_loss_inr"]), 2)
            self.assertAlmostEqual(bt["trade_expectancy_inr"], expected, places=1)

if __name__ == "__main__":
    unittest.main()
