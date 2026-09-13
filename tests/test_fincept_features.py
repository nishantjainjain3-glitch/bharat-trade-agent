import unittest
import math
from src.analysis.personas import (
    evaluate_buffett,
    evaluate_graham,
    evaluate_lynch,
    evaluate_ray_fu,
    evaluate_day_trading_guruji,
    evaluate_minervini,
    evaluate_turtle,
    evaluate_all_investor_personas
)
from src.data.macro_data import get_nse_sector_heatmap
from src.analysis.technical import (
    calculate_donchian_channel,
    calculate_williams_r,
    calculate_india_vix_regime
)
from src.analysis.frvp import calculate_frvp, evaluate_frvp_setup, get_frvp_analysis
from src.analysis.order_flow import detect_ict_order_blocks, get_ict_killzone_status
import pandas as pd
import numpy as np

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
        self.sample_technicals = {
            "trend": "BULLISH",
            "rsi": 55.0,
            "adx": {"adx": 28.0},
            "levels": {
                "support": 3900.0,
                "resistance": 4150.0,
                "atr": 60.0 # 1.5% ATR
            },
            "cpr": {
                "pivot": 3980.0,
                "tc": 3990.0,
                "bc": 3970.0,
                "width_pct": 0.30, # Narrow CPR
                "price_position": "ABOVE_CPR (Bullish Institutional Bias)"
            }
        }
        self.sample_order_flow = {
            "liquidity_sweeps": [
                {
                    "type": "SELL_SIDE_LIQUIDITY_SWEEP",
                    "price_level": 3890.0,
                    "volume_absorbed": 150000
                }
            ]
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

    def test_ray_fu_evaluation_quant_regime(self):
        res = evaluate_ray_fu(self.sample_quote, self.sample_technicals, self.sample_fundamentals)
        self.assertEqual(res["persona"], "Ray Fu")
        self.assertGreaterEqual(res["score"], 70)
        self.assertIn("Trend Following", res["regime"])
        self.assertEqual(res["audit_tag"], "VERIFIED_DATA")
        self.assertIn("Ray Fu criteria score", res["rationale"])

    def test_day_trading_guruji_liquidity_sweep(self):
        res = evaluate_day_trading_guruji(self.sample_quote, self.sample_technicals, self.sample_order_flow)
        self.assertEqual(res["persona"], "Day Trading Guruji")
        self.assertGreaterEqual(res["score"], 75)
        self.assertEqual(res["verdict"], "SWEEP_CONFIRMED_BUY")
        self.assertIn("Narrow CPR", res["cpr_setup"])
        self.assertIn("Sell-Side Liquidity (SSL) sweep confirmed", res["rationale"])

    def test_minervini_vcp_trend_template(self):
        res = evaluate_minervini(self.sample_quote, self.sample_technicals, self.sample_fundamentals)
        self.assertEqual(res["persona"], "Mark Minervini")
        self.assertGreaterEqual(res["score"], 60)
        self.assertIn("Minervini SEPA score", res["rationale"])
        self.assertIn("verdict", res)
        self.assertIn("badge", res)

    def test_turtle_donchian_breakout(self):
        res = evaluate_turtle(self.sample_quote, self.sample_technicals)
        self.assertEqual(res["persona"], "Richard Dennis / Turtle")
        self.assertGreaterEqual(res["score"], 50)
        self.assertIn("turtle_stop", res)
        self.assertLess(res["turtle_stop"], self.sample_quote["price"])
        self.assertIn("Turtle Trading score", res["rationale"])

    def test_composite_guru_consensus(self):
        comp = evaluate_all_investor_personas(
            self.sample_quote,
            self.sample_fundamentals,
            self.sample_technicals,
            self.sample_order_flow
        )
        self.assertIn("buffett", comp)
        self.assertIn("graham", comp)
        self.assertIn("lynch", comp)
        self.assertIn("ray_fu", comp)
        self.assertIn("day_trading_guruji", comp)
        self.assertIn("minervini", comp)
        self.assertIn("turtle", comp)
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

    def test_donchian_channel_calculation(self):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "High": np.linspace(100, 130, 30),
            "Low": np.linspace(90, 115, 30),
            "Close": np.linspace(95, 125, 30),
            "Open": np.linspace(92, 120, 30),
            "Volume": [1000] * 30
        }, index=dates)
        res = calculate_donchian_channel(df, period=20)
        self.assertIn("upper", res)
        self.assertIn("lower", res)
        self.assertIn("mid", res)
        self.assertGreater(res["upper"], res["lower"])
        self.assertEqual(res["period"], 20)

    def test_williams_r_indicator(self):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "High": [100 + i for i in range(30)],
            "Low": [90 + i for i in range(30)],
            "Close": [95 + i for i in range(30)],
            "Open": [92 + i for i in range(30)],
            "Volume": [1000] * 30
        }, index=dates)
        res = calculate_williams_r(df, period=14)
        self.assertIn("williams_r", res)
        self.assertGreaterEqual(res["williams_r"], -100.0)
        self.assertLessEqual(res["williams_r"], 0.0)
        self.assertIn("status", res)

    def test_india_vix_regime_classification(self):
        low_vol = calculate_india_vix_regime(11.5)
        self.assertEqual(low_vol["regime"], "LOW_VOL")
        self.assertEqual(low_vol["position_size_multiplier"], 0.0)

        sweet = calculate_india_vix_regime(15.2)
        self.assertEqual(sweet["regime"], "SWEET_SPOT")
        self.assertEqual(sweet["position_size_multiplier"], 1.0)
        self.assertAlmostEqual(sweet["recommended_delta"], 0.22)

        elevated = calculate_india_vix_regime(21.0)
        self.assertEqual(elevated["regime"], "ELEVATED")
        self.assertEqual(elevated["position_size_multiplier"], 0.5)

        crisis = calculate_india_vix_regime(29.0)
        self.assertEqual(crisis["regime"], "CRISIS")
        self.assertEqual(crisis["position_size_multiplier"], 0.0)

    def test_frvp_profile_and_setup_calculation(self):
        dates = pd.date_range("2026-01-01", periods=25)
        df = pd.DataFrame({
            "Open": [100, 102, 101, 103, 105] * 5,
            "High": [105, 107, 104, 108, 110] * 5,
            "Low": [98, 99, 97, 100, 102] * 5,
            "Close": [102, 104, 100, 106, 108] * 5,
            "Volume": [50000, 60000, 45000, 80000, 90000] * 5
        }, index=dates)
        profile = calculate_frvp(df, n_bins=30)
        self.assertIn("poc", profile)
        self.assertIn("vah", profile)
        self.assertIn("val", profile)
        self.assertGreater(profile["vah"], profile["val"])
        self.assertGreaterEqual(profile["poc"], profile["val"])
        self.assertLessEqual(profile["poc"], profile["vah"])

        # Test long VAL bounce setup
        setup = evaluate_frvp_setup(
            current_price=profile["val"],
            vah=profile["vah"],
            val=profile["val"],
            poc=profile["poc"],
            atr=2.0,
            candle_bullish=True,
            volume_above_avg=True
        )
        self.assertEqual(setup["setup"], "LONG_VAL_BOUNCE")
        self.assertLess(setup["stop"], setup["entry"])
        self.assertGreater(setup["risk_reward"], 0)

    def test_ict_order_blocks_and_killzones(self):
        kz = get_ict_killzone_status()
        self.assertIn("current_time_ist", kz)
        self.assertIn("active_killzones", kz)
        self.assertIn("ict_recommendation", kz)

        dates = pd.date_range("2026-01-01", periods=20)
        df = pd.DataFrame({
            "Open": [100, 95, 96, 105, 104, 103, 98, 90, 89, 98] * 2,
            "High": [102, 97, 106, 107, 106, 104, 99, 91, 99, 100] * 2,
            "Low": [98, 94, 95, 103, 102, 97, 91, 88, 88, 96] * 2,
            "Close": [99, 96, 105, 106, 103, 98, 91, 89, 98, 99] * 2,
            "Volume": [10000] * 20
        }, index=dates)
        obs = detect_ict_order_blocks(df)
        self.assertIn("bullish_obs", obs)
        self.assertIn("bearish_obs", obs)
        self.assertIn("status", obs)

    def test_portfolio_recycling_plan(self):
        from src.engine.portfolio_recycler import portfolio_recycler
        sample_portfolio = {
            "total_portfolio_value": 50000.0,
            "available_cash": 200.0,
            "holdings": [
                {"tradingsymbol": "STOCK_A", "quantity": 100, "ltp": 200.0},
                {"tradingsymbol": "STOCK_B", "quantity": 1, "ltp": 300.0},
                {"tradingsymbol": "GOLDBEES", "quantity": 50, "ltp": 120.0},
            ]
        }
        plan = portfolio_recycler.generate_capital_recycling_plan(sample_portfolio, required_cash=5000.0, target_symbol="BHEL")
        self.assertEqual(plan["status"], "RECYCLING_PLAN_READY")
        self.assertGreater(plan["total_cash_to_be_released"], 4500.0)
        self.assertGreaterEqual(len(plan["actions_needed"]), 1)

    def test_adversarial_council_clean_pass(self):
        from src.agents.adversarial_council import adversarial_council
        audit = adversarial_council.audit_trade_proposal(
            symbol="BHEL",
            price=430.0,
            stop_loss=415.0,
            target_price=465.0,
            technicals={"rsi": 55.0, "adx": {"adx": 26.0}, "atr": 8.0},
            fundamentals={"metrics": {"pe_ratio": 28.0, "roe_pct": 14.0, "debt_to_equity": 0.40}},
            news_headlines=["BHEL bags multi-crore infrastructure order."]
        )
        self.assertEqual(audit["verdict"], "PASSED_CLEAN_AUDIT")
        self.assertGreaterEqual(audit["overall_audit_score"], 80.0)
        self.assertEqual(len(audit["objections"]), 0)
        self.assertGreaterEqual(audit["math_metrics"]["reward_to_risk"], 1.5)

    def test_adversarial_council_rejection_and_caveats(self):
        from src.agents.adversarial_council import adversarial_council
        # Violates R:R and overbought RSI
        audit = adversarial_council.audit_trade_proposal(
            symbol="OVERPRICED",
            price=100.0,
            stop_loss=95.0,
            target_price=103.0,  # 3 reward / 5 risk = 0.6 RR (< 1.5)
            technicals={"rsi": 78.0, "adx": {"adx": 12.0}, "atr": 2.0},
            fundamentals={"metrics": {"pe_ratio": 95.0, "roe_pct": "N/A", "debt_to_equity": "N/A"}},
            news_headlines=["Stock rises"]
        )
        self.assertEqual(audit["verdict"], "REJECTED_BY_ADVERSARIAL_COUNCIL")
        self.assertLess(audit["overall_audit_score"], 60.0)
        self.assertTrue(any("CRITICAL" in o for o in audit["objections"]))

    def test_media_syndication_deduplicator(self):
        from src.agents.adversarial_council import adversarial_council
        syndicated = [
            "XYZ Corporation signs definitive pact for green hydrogen facility in Gujarat",
            "Gujarat green hydrogen facility definitive pact signed by XYZ Corporation",
            "Definitive agreement for green hydrogen plant signed by XYZ Corporation in Gujarat",
            "XYZ Corporation enters into pact for new green hydrogen facility in Gujarat"
        ]
        media_audit = adversarial_council._critic_media_syndication(syndicated)
        self.assertEqual(media_audit["unique_stories_count"], 1)
        self.assertTrue(media_audit["is_syndication_spam"])
        self.assertLess(media_audit["syndication_ratio"], 0.5)

    def test_research_vault_lifecycle(self):
        import tempfile
        from src.data.research_vault import ResearchVault
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = ResearchVault(vault_dir=tmpdir)
            save_res = vault.save_dossier("INFY", {
                "verdict": "BUY",
                "conviction": 8,
                "time_horizon": "Swing",
                "entry_range": "INR 1800 - INR 1820",
                "target_price": "INR 1950",
                "stop_loss": "INR 1740",
                "risk_reward_ratio": "1 : 2.1",
                "executive_summary": "Tier-1 IT major with deal renewal momentum.",
                "technical_summary": "Bounce from 200 EMA support.",
                "fundamental_summary": "Low debt, consistent operating cash flows.",
                "bull_case": "Large cloud modernization deal pipeline.",
                "bear_case": "US discretionary tech spend delay.",
                "adversarial_council_audit": {
                    "verdict": "PASSED_CLEAN_AUDIT",
                    "overall_audit_score": 92.0,
                    "component_scores": {"fact_score": 100.0, "bear_survival_score": 85.0, "math_score": 90.0, "media_independence_score": 100.0}
                }
            })
            self.assertEqual(save_res["status"], "SAVED")
            dossier = vault.get_dossier("INFY")
            self.assertIsNotNone(dossier)
            self.assertEqual(dossier["symbol"], "INFY")
            self.assertEqual(dossier["verdict"], "BUY")

            md = vault.get_dossier_markdown("INFY")
            self.assertIn("# 🏛️ Research Vault Dossier: INFY", md)
            self.assertIn("Operational Trade Boundaries", md)

            results = vault.list_dossiers()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["symbol"], "INFY")

            search_res = vault.search_vault("modernization")
            self.assertEqual(len(search_res), 1)

            deleted = vault.delete_dossier("INFY")
            self.assertTrue(deleted)
            self.assertIsNone(vault.get_dossier("INFY"))

if __name__ == "__main__":
    unittest.main()


