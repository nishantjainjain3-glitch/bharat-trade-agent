import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PortfolioRecycler:
    """
    Self-Funding Portfolio Capital Recycling & Rebalancing Engine.
    Enables the trading bot to operate and compound autonomously strictly from
    the existing portfolio equity without requiring external cash deposits.
    
    Functions:
    1. Audits current concentration risk (flags holdings > 25% of equity).
    2. Identifies micro/dust positions (< 1.5% equity) that create clutter.
    3. Formulates a Capital Recycling Plan to fund high-conviction setups by:
       - Pruning dust holdings with low momentum.
       - Trimming over-concentrated positions back to balanced 15-20% weights.
    """
    def __init__(self, max_single_stock_pct: float = 25.0, min_dust_threshold_pct: float = 1.5):
        self.max_single_stock_pct = max_single_stock_pct
        self.min_dust_threshold_pct = min_dust_threshold_pct

    def audit_portfolio_allocation(self, portfolio_summary: Dict[str, Any]) -> Dict[str, Any]:
        tot_val = float(portfolio_summary.get("total_portfolio_value", 0.0))
        avail_cash = float(portfolio_summary.get("available_cash", 0.0))
        raw_holdings = portfolio_summary.get("holdings", [])

        if tot_val <= 0:
            tot_val = sum(float(h.get("quantity", 0)) * float(h.get("ltp", 0.0)) for h in raw_holdings) + avail_cash

        analyzed_holdings = []
        overconcentrated = []
        dust_positions = []
        core_holdings = []

        for h in raw_holdings:
            sym = h.get("tradingsymbol", "").replace("-EQ", "").strip().upper()
            qty = int(h.get("quantity", 0))
            ltp = float(h.get("ltp", 0.0))
            mkt_val = round(qty * ltp, 2)
            weight_pct = round((mkt_val / tot_val * 100.0) if tot_val > 0 else 0.0, 2)

            item = {
                "symbol": sym,
                "quantity": qty,
                "ltp": ltp,
                "market_value": mkt_val,
                "weight_pct": weight_pct,
                "pnl": h.get("pnl")
            }

            if weight_pct > self.max_single_stock_pct:
                excess_val = round(mkt_val - (tot_val * (self.max_single_stock_pct / 100.0)), 2)
                shares_to_trim = int(excess_val / ltp) if ltp > 0 else 0
                item["category"] = "OVERCONCENTRATED"
                item["shares_to_trim"] = shares_to_trim
                item["excess_capital_inr"] = excess_val
                overconcentrated.append(item)
            elif weight_pct < self.min_dust_threshold_pct and qty <= 2:
                item["category"] = "DUST_POSITION"
                item["shares_to_trim"] = qty
                item["excess_capital_inr"] = mkt_val
                dust_positions.append(item)
            else:
                item["category"] = "CORE_HOLDING"
                item["shares_to_trim"] = 0
                item["excess_capital_inr"] = 0.0
                core_holdings.append(item)

            analyzed_holdings.append(item)

        # Sort holdings by weight descending
        analyzed_holdings.sort(key=lambda x: x["weight_pct"], reverse=True)

        return {
            "total_portfolio_value": round(tot_val, 2),
            "available_cash": round(avail_cash, 2),
            "holdings_count": len(raw_holdings),
            "holdings": analyzed_holdings,
            "overconcentrated_positions": overconcentrated,
            "dust_positions": dust_positions,
            "core_positions": core_holdings,
            "cash_pct": round((avail_cash / tot_val * 100.0) if tot_val > 0 else 0.0, 2)
        }

    def generate_capital_recycling_plan(
        self,
        portfolio_summary: Dict[str, Any],
        required_cash: float,
        target_symbol: str
    ) -> Dict[str, Any]:
        """
        Creates an exact step-by-step trimming and sell order plan to raise `required_cash`
        internally from the existing portfolio.
        """
        audit = self.audit_portfolio_allocation(portfolio_summary)
        avail_cash = audit["available_cash"]
        cash_deficit = max(0.0, required_cash - avail_cash)

        if cash_deficit <= 0:
            return {
                "status": "SUFFICIENT_CASH",
                "required_cash": required_cash,
                "available_cash": avail_cash,
                "cash_deficit": 0.0,
                "actions_needed": [],
                "target_symbol": target_symbol,
                "message": f"Sufficient cash available (INR {avail_cash}) to fund target order."
            }

        actions = []
        accumulated_cash = 0.0

        from src.broker.execution_microstructure import calculate_statutory_friction

        actions = []
        accumulated_gross = 0.0
        accumulated_net = 0.0

        # Phase 1: Trim overconcentrated positions first (Maximum cash release, tiny <0.5% statutory friction)
        for oc in audit["overconcentrated_positions"]:
            if accumulated_net >= cash_deficit:
                break
            ltp = oc["ltp"]
            excess_val = oc["excess_capital_inr"]
            trim_qty = oc["shares_to_trim"]

            needed = cash_deficit - accumulated_net
            if needed < excess_val and ltp > 0:
                trim_qty = min(trim_qty, int(needed / ltp) + 1)

            if trim_qty > 0:
                gross_released = round(trim_qty * ltp, 2)
                friction = calculate_statutory_friction(oc["symbol"], "SELL", ltp, trim_qty, "DELIVERY")
                net_released = round(gross_released - friction["total_friction_inr"], 2)

                actions.append({
                    "action": "TRIM",
                    "symbol": oc["symbol"],
                    "quantity": trim_qty,
                    "price": ltp,
                    "gross_cash_released": gross_released,
                    "statutory_friction_inr": friction["total_friction_inr"],
                    "friction_pct": friction["friction_pct"],
                    "net_cash_released": net_released,
                    "rationale": f"Trim concentration from {oc['weight_pct']}% toward 20% risk ceiling (Friction: {friction['friction_pct']:.2f}%)."
                })
                accumulated_gross += gross_released
                accumulated_net += net_released

        # Phase 2: If still deficient, prune dust positions (Warn if DP charge > 2.0% of value)
        if accumulated_net < cash_deficit:
            for d in audit["dust_positions"]:
                if accumulated_net >= cash_deficit:
                    break
                qty = d["quantity"]
                ltp = d["ltp"]
                gross_val = d["market_value"]
                friction = calculate_statutory_friction(d["symbol"], "SELL", ltp, qty, "DELIVERY")
                net_released = round(max(0.0, gross_val - friction["total_friction_inr"]), 2)

                actions.append({
                    "action": "SELL_DUST",
                    "symbol": d["symbol"],
                    "quantity": qty,
                    "price": ltp,
                    "gross_cash_released": gross_val,
                    "statutory_friction_inr": friction["total_friction_inr"],
                    "friction_pct": friction["friction_pct"],
                    "net_cash_released": net_released,
                    "is_fee_prohibitive": friction["is_fee_prohibitive"],
                    "rationale": (
                        f"Prune micro dust position ({d['weight_pct']}% of portfolio). "
                        + (f"⚠️ High statutory friction ({friction['friction_pct']:.1f}%) due to DP charges on small lot." if friction["is_fee_prohibitive"] else "")
                    )
                })
                accumulated_gross += gross_val
                accumulated_net += net_released

        # Phase 3: If still deficient, trim largest non-gold core holding
        if accumulated_net < cash_deficit:
            for c in audit["core_positions"]:
                if "GOLD" in c["symbol"]:
                    continue  # 100% preserve Gold hedge
                if accumulated_net >= cash_deficit:
                    break
                ltp = c["ltp"]
                needed = cash_deficit - accumulated_net
                trim_qty = min(c["quantity"], int(needed / ltp) + 1) if ltp > 0 else 0
                if trim_qty > 0:
                    gross_released = round(trim_qty * ltp, 2)
                    friction = calculate_statutory_friction(c["symbol"], "SELL", ltp, trim_qty, "DELIVERY")
                    net_released = round(gross_released - friction["total_friction_inr"], 2)
                    actions.append({
                        "action": "TRIM_CORE",
                        "symbol": c["symbol"],
                        "quantity": trim_qty,
                        "price": ltp,
                        "gross_cash_released": gross_released,
                        "statutory_friction_inr": friction["total_friction_inr"],
                        "friction_pct": friction["friction_pct"],
                        "net_cash_released": net_released,
                        "rationale": f"Reallocate from {c['symbol']} to higher-conviction setup {target_symbol}."
                    })
                    accumulated_gross += gross_released
                    accumulated_net += net_released

        plan_viable = (accumulated_net + avail_cash) >= required_cash

        return {
            "status": "RECYCLING_PLAN_READY" if plan_viable else "PARTIAL_CAPITAL_AVAILABLE",
            "required_cash": round(required_cash, 2),
            "available_cash": round(avail_cash, 2),
            "cash_deficit": round(cash_deficit, 2),
            "total_cash_to_be_released": round(accumulated_net, 2),
            "net_cash_released": round(accumulated_net, 2),
            "gross_cash_released": round(accumulated_gross, 2),
            "total_statutory_friction": round(accumulated_gross - accumulated_net, 2),
            "projected_total_cash": round(accumulated_net + avail_cash, 2),
            "actions_needed": actions,
            "target_symbol": target_symbol,
            "message": (
                f"Generated {len(actions)} capital recycling trims to raise net INR {round(accumulated_net, 2)} "
                f"(Gross: ₹{round(accumulated_gross, 2)}, Friction: ₹{round(accumulated_gross - accumulated_net, 2)}) "
                f"from internal portfolio equity to fund {target_symbol}."
            )
        }

portfolio_recycler = PortfolioRecycler()
