import unittest
from src.analysis.battle_plan import generate_tactical_battle_plan

class TestBattlePlanFeatures(unittest.TestCase):
    def setUp(self):
        self.quote = {
            "symbol": "RELIANCE.NS",
            "clean_symbol": "RELIANCE",
            "name": "Reliance Industries",
            "price": 2500.0,
            "change": 35.0,
            "change_pct": 1.42
        }
        self.technicals = {
            "trend": "BULLISH",
            "score": 4,
            "rsi": 58.5,
            "emas": {
                "ema_20": 2470.0,
                "ema_50": 2420.0,
                "ema_200": 2350.0
            },
            "levels": {
                "support": 2450.0,
                "resistance": 2560.0,
                "recent_high_20d": 2550.0,
                "recent_low_20d": 2440.0,
                "atr": 32.0
            },
            "volume": {
                "current_volume": 4500000,
                "avg_volume_20d": 2800000,
                "rvol_20d": 1.61,
                "status": "SURGE",
                "meaning": "High volume surge"
            }
        }
        self.fundamentals = {
            "score": 2,
            "verdict": "UNDERVALUED",
            "metrics": {"pe_ratio": 22.4, "roe_pct": 14.8}
        }
        self.research = {
            "verdict": "BUY",
            "conviction": 8,
            "time_horizon": "Swing (1-3 weeks)"
        }

    def test_battle_plan_sniper_levels(self):
        bp = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="NORMAL")
        sp = bp["sniper_points"]
        self.assertLessEqual(sp["ideal_buy"], self.quote["price"])
        self.assertLess(sp["stop_loss"], sp["ideal_buy"])
        self.assertGreater(sp["target_1"], self.quote["price"])
        self.assertGreater(sp["target_2"], sp["target_1"])
        self.assertGreater(sp["risk_per_share"], 0)
        self.assertIn("1 : 1.5", sp["rr_ratio_t1"])

    def test_battle_plan_dual_track_advice(self):
        bp = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="NORMAL")
        dt = bp["dual_track_advice"]
        self.assertIn("Ideal Pullback", dt["no_position"])
        self.assertIn("Target 1", dt["has_position"])
        self.assertIn("50% profit", dt["has_position"])

    def test_battle_plan_volume_confluence(self):
        bp = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="NORMAL")
        vc = bp["volume_confluence"]
        self.assertEqual(vc["rvol_20d"], 1.61)
        self.assertEqual(vc["status"], "SURGE_BULLISH")
        self.assertIn("accumulation", vc["interpretation"].lower())

    def test_battle_plan_survival_tier_scaling(self):
        # NORMAL tier
        bp_norm = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="NORMAL")
        self.assertEqual(bp_norm["position_sizing"]["max_risk_pct"], 1.5)
        self.assertEqual(bp_norm["position_sizing"]["allocation_multiplier"], 1.0)

        # DEFENSIVE tier
        bp_def = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="DEFENSIVE")
        self.assertEqual(bp_def["position_sizing"]["max_risk_pct"], 0.75)
        self.assertEqual(bp_def["position_sizing"]["allocation_multiplier"], 0.5)

        # CRITICAL tier
        bp_crit = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="CRITICAL")
        self.assertEqual(bp_crit["position_sizing"]["max_risk_pct"], 0.0)
        self.assertEqual(bp_crit["position_sizing"]["allocation_multiplier"], 0.0)

    def test_battle_plan_pre_trade_checklist(self):
        bp = generate_tactical_battle_plan(self.quote, self.technicals, self.fundamentals, self.research, survival_tier="NORMAL")
        cl = bp["pre_trade_checklist"]
        self.assertEqual(len(cl), 4)
        check_ids = [c["id"] for c in cl]
        self.assertIn("check_rr", check_ids)
        self.assertIn("check_trend", check_ids)
        self.assertIn("check_risk_cap", check_ids)
        self.assertIn("check_stop_order", check_ids)

        rr_check = next(c for c in cl if c["id"] == "check_rr")
        self.assertTrue(rr_check["passed"])

if __name__ == "__main__":
    unittest.main()
