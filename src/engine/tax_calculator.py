"""
Indian Statutory Transaction Costs & Net Realized PnL Calculator.
Calculates exact net profit/loss after Indian regulatory charges:
1. STT (Securities Transaction Tax): 0.1% on delivery Buy and Sell.
2. Exchange Turnover Charges (NSE): 0.00325% on turnover.
3. SEBI Turnover Charges: 0.0001% (Rs 10 per crore).
4. Stamp Duty: 0.015% on Buy turnover.
5. GST: 18% on (Brokerage + Exchange turnover fees + SEBI fees).
6. CDSL Depository DP Charges: Rs 15.93 per script per day on delivery Sell.
"""
from typing import Dict, Any

STT_DELIVERY_PCT = 0.001       # 0.1% on Buy & Sell
NSE_TURNOVER_FEE_PCT = 0.0000325 # 0.00325%
SEBI_CHARGES_PCT = 0.000001    # Rs 10 per crore
STAMP_DUTY_BUY_PCT = 0.00015   # 0.015% on Buy
GST_PCT = 0.18                 # 18% on eligible charges
DP_CHARGE_PER_SCRIPT = 15.93   # CDSL DP charges including GST per delivery sell


def calculate_trade_costs(
    buy_price: float,
    sell_price: float,
    quantity: int,
    brokerage_per_order: float = 0.0 # Angel One delivery brokerage is Rs 0
) -> Dict[str, Any]:
    """
    Computes exact breakdown of statutory costs and net realized PnL.
    """
    if buy_price <= 0 or sell_price <= 0 or quantity <= 0:
        return {
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "total_charges": 0.0,
            "charges_breakdown": {},
            "net_pnl_pct": 0.0,
            "is_profitable_net": False
        }

    buy_val = round(buy_price * quantity, 2)
    sell_val = round(sell_price * quantity, 2)
    total_turnover = buy_val + sell_val

    # Gross profit
    gross_pnl = round(sell_val - buy_val, 2)

    # 1. STT: 0.1% on buy and sell
    stt = round((buy_val * STT_DELIVERY_PCT) + (sell_val * STT_DELIVERY_PCT), 2)

    # 2. Exchange turnover charge: 0.00325%
    exchange_charges = round(total_turnover * NSE_TURNOVER_FEE_PCT, 2)

    # 3. SEBI turnover fee: 0.0001%
    sebi_fees = round(total_turnover * SEBI_CHARGES_PCT, 2)

    # 4. Stamp duty: 0.015% on buy only
    stamp_duty = round(buy_val * STAMP_DUTY_BUY_PCT, 2)

    # 5. Brokerage
    brokerage = round(brokerage_per_order * 2, 2) # buy + sell

    # 6. GST: 18% on (brokerage + exchange_charges + sebi_fees)
    gst_taxable = brokerage + exchange_charges + sebi_fees
    gst = round(gst_taxable * GST_PCT, 2)

    # 7. DP Charges: Rs 15.93 on delivery sell
    dp_charges = DP_CHARGE_PER_SCRIPT

    total_charges = round(stt + exchange_charges + sebi_fees + stamp_duty + brokerage + gst + dp_charges, 2)
    net_pnl = round(gross_pnl - total_charges, 2)
    net_pnl_pct = round((net_pnl / buy_val) * 100.0, 2) if buy_val > 0 else 0.0

    return {
        "buy_value": buy_val,
        "sell_value": sell_val,
        "turnover": total_turnover,
        "gross_pnl": gross_pnl,
        "total_charges": total_charges,
        "net_pnl": net_pnl,
        "net_pnl_pct": net_pnl_pct,
        "is_profitable_net": net_pnl > 0,
        "breakdown": {
            "stt": stt,
            "exchange_charges": exchange_charges,
            "sebi_fees": sebi_fees,
            "stamp_duty": stamp_duty,
            "brokerage": brokerage,
            "gst": gst,
            "dp_charges": dp_charges
        }
    }


def is_trade_asymmetric_after_costs(
    entry_price: float,
    target_price: float,
    stop_loss: float,
    quantity: int,
    min_net_reward_risk: float = 1.5
) -> Dict[str, Any]:
    """
    Validates if a proposed trade setup maintains a favorable risk-to-reward ratio
    AFTER deducting all Indian statutory exchange taxes and DP charges.
    Rejects setups where taxes consume more than 20% of the projected profit.
    """
    if entry_price <= 0 or target_price <= entry_price or stop_loss >= entry_price or quantity <= 0:
        return {"passed": False, "reason": "Invalid price geometry", "net_rr": 0.0}

    # Win scenario
    win_result = calculate_trade_costs(entry_price, target_price, quantity)
    net_profit = win_result["net_pnl"]
    fee_drag_pct = round((win_result["total_charges"] / win_result["gross_pnl"]) * 100, 1) if win_result["gross_pnl"] > 0 else 100.0

    # Loss scenario
    loss_result = calculate_trade_costs(entry_price, stop_loss, quantity)
    net_loss = abs(loss_result["net_pnl"]) # loss is magnified by charges

    if net_loss <= 0:
        return {"passed": False, "reason": "Calculated net loss non-positive", "net_rr": 0.0}

    net_rr = round(net_profit / net_loss, 2)

    passed = net_rr >= min_net_reward_risk and fee_drag_pct <= 20.0
    reason = "Setup passes net asymmetry test" if passed else (
        f"Fee drag too high ({fee_drag_pct}%) or Net R:R too low ({net_rr} vs {min_net_reward_risk})"
    )

    return {
        "passed": passed,
        "net_reward_risk": net_rr,
        "net_projected_profit": net_profit,
        "net_projected_risk": net_loss,
        "fee_drag_pct": fee_drag_pct,
        "total_charges_on_target": win_result["total_charges"],
        "reason": reason
    }
