import unittest
from src.broker.execution_algos import ExecutionAlgoEngine

class TestExecutionAlgos(unittest.TestCase):
    def setUp(self):
        self.engine = ExecutionAlgoEngine(random_seed=42)

    def test_twap_schedule_conservation(self):
        total_qty = 100
        slices = self.engine.generate_twap_schedule(
            total_quantity=total_qty,
            duration_minutes=60,
            slice_interval_minutes=5,
            jitter_pct=0.15
        )
        self.assertGreater(len(slices), 0)
        # Verify strict quantity conservation
        sum_qty = sum(s["quantity"] for s in slices)
        self.assertEqual(sum_qty, total_qty)

    def test_twap_edge_cases(self):
        # Quantity less than slice count
        slices = self.engine.generate_twap_schedule(total_quantity=3, duration_minutes=30, slice_interval_minutes=5)
        sum_qty = sum(s["quantity"] for s in slices)
        self.assertEqual(sum_qty, 3)

        # Zero quantity
        empty = self.engine.generate_twap_schedule(total_quantity=0)
        self.assertEqual(len(empty), 0)

    def test_vwap_schedule_conservation(self):
        total_qty = 500
        slices = self.engine.generate_vwap_schedule(total_quantity=total_qty, num_slices=6)
        self.assertEqual(len(slices), 6)
        sum_qty = sum(s["quantity"] for s in slices)
        self.assertEqual(sum_qty, total_qty)

    def test_simulate_execution_slippage_protection(self):
        slices = [
            {"slice_id": 1, "quantity": 50},
            {"slice_id": 2, "quantity": 50}
        ]
        # Low max slippage should abort when market drifts
        res = self.engine.simulate_execution(
            symbol="RELIANCE",
            transaction_type="BUY",
            slices=slices,
            reference_price=2800.0,
            price_volatility_pct=2.0,
            max_slippage_pct=0.10  # Very tight 0.1% collar
        )
        self.assertIn("total_filled_qty", res)
        self.assertIn("slippage_basis_points", res)
        self.assertIn("aborted", res)

    def test_simulate_execution_normal_fill(self):
        slices = [
            {"slice_id": 1, "quantity": 25},
            {"slice_id": 2, "quantity": 25}
        ]
        res = self.engine.simulate_execution(
            symbol="INFY",
            transaction_type="BUY",
            slices=slices,
            reference_price=1600.0,
            price_volatility_pct=0.01,
            max_slippage_pct=1.0
        )
        self.assertFalse(res["aborted"])
        self.assertEqual(res["total_filled_qty"], 50)
        self.assertEqual(res["fill_rate_pct"], 100.0)

if __name__ == "__main__":
    unittest.main()
