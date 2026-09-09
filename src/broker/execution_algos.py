import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class ExecutionAlgoEngine:
    """
    Institutional Algorithmic Execution Engine for NSE/BSE Equity Markets.
    Supports Time-Weighted Average Price (TWAP) and Volume-Weighted Average Price (VWAP)
    parent-to-child order slicing with randomized jitter and slippage collar controls.
    """

    # Normalized historical intraday volume profile for NSE (09:15 - 15:30) in 30-min buckets
    NSE_INTRADAY_VOLUME_PROFILE = [
        0.18,  # 09:15 - 09:45 (Morning opening rush)
        0.14,  # 09:45 - 10:15
        0.10,  # 10:15 - 10:45
        0.07,  # 10:45 - 11:15
        0.05,  # 11:15 - 11:45
        0.04,  # 11:45 - 12:15 (Midday lull)
        0.04,  # 12:15 - 12:45
        0.05,  # 12:45 - 13:15
        0.06,  # 13:15 - 13:45
        0.08,  # 13:45 - 14:15
        0.09,  # 14:15 - 14:45
        0.10   # 14:45 - 15:30 (Market on Close auction ramp)
    ]

    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)

    def generate_twap_schedule(
        self,
        total_quantity: int,
        duration_minutes: int = 60,
        slice_interval_minutes: int = 5,
        jitter_pct: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Splits a parent order into equal child slices across duration_minutes.
        Applies randomized time and size jitter (+/- jitter_pct) to prevent predatory
        HFT algorithms from recognizing mechanical slicing patterns on the NSE order book.
        """
        if total_quantity <= 0:
            return []

        num_slices = max(1, duration_minutes // slice_interval_minutes)
        if total_quantity < num_slices:
            num_slices = total_quantity

        base_qty = total_quantity // num_slices
        remainder = total_quantity % num_slices

        slices = []
        now = datetime.now()
        allocated_qty = 0

        for i in range(num_slices):
            # Compute time offset with jitter
            base_offset = i * slice_interval_minutes * 60
            jitter_sec = int(random.uniform(-0.2, 0.2) * (slice_interval_minutes * 60)) if i > 0 else 0
            execution_time = now + timedelta(seconds=max(0, base_offset + jitter_sec))

            # Quantity jitter
            if i == num_slices - 1:
                slice_qty = total_quantity - allocated_qty
            else:
                q_jitter = int(round(base_qty * random.uniform(-jitter_pct, jitter_pct)))
                slice_qty = max(1, base_qty + q_jitter)
                if i < remainder:
                    slice_qty += 1
                if allocated_qty + slice_qty >= total_quantity:
                    slice_qty = max(1, total_quantity - allocated_qty - (num_slices - 1 - i))
                allocated_qty += slice_qty

            slices.append({
                "slice_id": i + 1,
                "quantity": slice_qty,
                "scheduled_time": execution_time.strftime("%H:%M:%S"),
                "offset_seconds": max(0, base_offset + jitter_sec),
                "status": "PENDING"
            })

        # Ensure total quantity conservation
        total_scheduled = sum(s["quantity"] for s in slices)
        diff = total_quantity - total_scheduled
        if diff != 0:
            slices[-1]["quantity"] += diff

        return slices

    def generate_vwap_schedule(
        self,
        total_quantity: int,
        num_slices: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Generates volume-weighted slice distribution based on Indian market intraday volume curve.
        """
        if total_quantity <= 0 or num_slices <= 0:
            return []

        # Sample or interpolate weights from NSE profile
        weights = self.NSE_INTRADAY_VOLUME_PROFILE[:num_slices]
        sum_w = sum(weights)
        norm_weights = [w / sum_w for w in weights]

        slices = []
        allocated = 0
        now = datetime.now()

        for i, w in enumerate(norm_weights):
            if i == len(norm_weights) - 1:
                slice_qty = total_quantity - allocated
            else:
                slice_qty = max(1, int(round(total_quantity * w)))
                allocated += slice_qty

            slices.append({
                "slice_id": i + 1,
                "quantity": slice_qty,
                "weight_pct": round(w * 100.0, 1),
                "scheduled_time": (now + timedelta(minutes=i * 15)).strftime("%H:%M:%S"),
                "status": "PENDING"
            })

        total_scheduled = sum(s["quantity"] for s in slices)
        diff = total_quantity - total_scheduled
        if diff != 0:
            slices[-1]["quantity"] += diff

        return slices

    def simulate_execution(
        self,
        symbol: str,
        transaction_type: str,
        slices: List[Dict[str, Any]],
        reference_price: float,
        price_volatility_pct: float = 0.05,
        max_slippage_pct: float = 0.50
    ) -> Dict[str, Any]:
        """
        Simulates order execution with market impact and slippage protection.
        Aborts execution if slippage exceeds max_slippage_pct.
        """
        filled_qty = 0
        total_val = 0.0
        executed_slices = []
        aborted = False
        abort_reason = None

        cur_price = reference_price

        for s in slices:
            # Simulate random drift + market impact
            drift = random.uniform(-price_volatility_pct, price_volatility_pct)
            impact = 0.01 * (s["quantity"] / 100.0)
            if transaction_type == "BUY":
                exec_price = cur_price * (1.0 + (drift + impact) / 100.0)
            else:
                exec_price = cur_price * (1.0 - (drift + impact) / 100.0)

            exec_price = round(exec_price, 2)
            slippage_pct = ((exec_price - reference_price) / reference_price) * 100.0 if transaction_type == "BUY" else ((reference_price - exec_price) / reference_price) * 100.0

            if slippage_pct > max_slippage_pct:
                aborted = True
                abort_reason = f"Slippage limit violated: {slippage_pct:.2f}% > {max_slippage_pct:.2f}%"
                break

            filled_qty += s["quantity"]
            total_val += (s["quantity"] * exec_price)
            executed_slices.append({
                "slice_id": s["slice_id"],
                "quantity": s["quantity"],
                "price": exec_price,
                "slippage_pct": round(slippage_pct, 3),
                "status": "FILLED"
            })
            cur_price = exec_price

        avg_price = round(total_val / filled_qty, 2) if filled_qty > 0 else reference_price
        total_slippage_bps = round(((avg_price - reference_price) / reference_price) * 10000.0, 1)

        return {
            "symbol": symbol,
            "transaction_type": transaction_type,
            "total_requested_qty": sum(s["quantity"] for s in slices),
            "total_filled_qty": filled_qty,
            "fill_rate_pct": round((filled_qty / sum(s["quantity"] for s in slices)) * 100.0, 1),
            "reference_price": reference_price,
            "average_execution_price": avg_price,
            "slippage_basis_points": total_slippage_bps,
            "aborted": aborted,
            "abort_reason": abort_reason,
            "executed_slices": executed_slices
        }

execution_engine = ExecutionAlgoEngine()
