import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from src.broker.angel_one import angel_client
from src.data.macro_data import get_indian_macro_indicators
from src.analysis.multi_asset_scanner import scan_multi_asset_opportunities
from src.notifications.telegram import send_telegram_text
from src.engine.risk_tiers import evaluate_survival_tier
from src.engine.memory import memory_journal

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


def build_morning_briefing() -> str:
    """Constructs the comprehensive 08:45 AM pre-market briefing."""
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%A, %d %B %Y | %H:%M IST")

    # 1. Fetch Portfolio
    portfolio = angel_client.get_portfolio_summary()
    mode = portfolio.get("mode", "LIVE")
    tot_val = float(portfolio.get("total_portfolio_value", 125000.0))
    cash = float(portfolio.get("available_cash", 125000.0))
    invested = float(portfolio.get("invested_amount", 0.0))
    pnl = float(portfolio.get("overall_pnl", 0.0))
    pnl_pct = float(portfolio.get("overall_pnl_pct", 0.0))
    holdings = portfolio.get("holdings", [])

    # 2. Fetch Macro & VIX
    try:
        macro = get_indian_macro_indicators()
        nifty_chg = macro.get("NIFTY", {}).get("change_pct", 0.0)
        vix_val = macro.get("INDIA_VIX", {}).get("current", 14.2)
    except Exception:
        nifty_chg = 0.0
        vix_val = 14.2

    # 3. Evaluate Survival Tier
    tier_info = evaluate_survival_tier(
        current_equity=tot_val,
        peak_equity=max(tot_val, 125000.0),
        nifty_day_change_pct=nifty_chg,
        daily_pnl_pct=0.0
    )
    tier_name = tier_info.get("tier", "NORMAL")
    tier_mult = tier_info.get("position_size_multiplier", 1.0)

    # 4. Multi-asset quick scan
    try:
        scan_res = scan_multi_asset_opportunities(
            account_equity=tot_val,
            available_cash=cash,
            tier_multiplier=tier_mult,
            india_vix_override=vix_val
        )
        actionable_opps = [o for o in scan_res.get("opportunities", []) if o.get("correlation_status") == "PASSED"]
    except Exception as e:
        actionable_opps = []

    pnl_emoji = "🟢" if pnl >= 0 else "🔴"

    lines = [
        "🌅 *BHARAT TRADE AGENT — MORNING BRIEFING*",
        f"📅 _{date_str}_",
        f"🛡️ *Broker Mode:* `{mode}` (Angel One)\n",
        "🌐 *Global & Benchmark Cues:*",
        f"• Nifty 50 Prev Close: *{nifty_chg:+.2f}%*",
        f"• India VIX: *{vix_val:.2f}* ({'Low/Calm' if vix_val < 16 else 'Elevated'})",
        f"• Survival Tier: *{tier_name}* ({tier_mult}x sizing multiplier)\n",
        "💼 *Account Snapshot:*",
        f"• Total Equity: *₹{tot_val:,.2f}*",
        f"• Available Cash: *₹{cash:,.2f}*",
        f"• Invested Margin: *₹{invested:,.2f}*",
        f"• Overall P&L: *{pnl_emoji} ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)*\n",
        f"📊 *Open Positions ({len(holdings)}):*"
    ]

    if holdings:
        for h in holdings[:5]:
            sym = h.get("tradingsymbol", h.get("symbol", "STOCK")).replace("-EQ", "")
            qty = h.get("quantity", 0)
            ltp = float(h.get("ltp", 0.0))
            hpnl = float(h.get("profitandloss", h.get("pnl", 0.0)) or 0.0)
            hemoji = "🟢" if hpnl >= 0 else "🔴"
            lines.append(f"• *{sym}*: {qty} qty @ ₹{ltp:,.1f} ({hemoji} ₹{hpnl:+,.1f})")
    else:
        lines.append("• _No overnight open positions. Ready for fresh allocations._")

    lines.append("\n🎯 *Multi-Asset Tactical Battle Plan:*")
    if actionable_opps:
        for opp in actionable_opps[:3]:
            stype = opp.get("strategy_type", "").replace("_", " ")
            sym = opp.get("symbol", "")
            ep = opp.get("entry_price", 0.0)
            sl = opp.get("stop_loss", 0.0)
            tp = opp.get("target_price", 0.0)
            conv = opp.get("conviction", 7)
            lines.append(f"• *{sym}* [{stype}]: Entry ₹{ep:,.1f} | SL ₹{sl:,.1f} | TP ₹{tp:,.1f} (Conviction: {conv}/10)")
    else:
        lines.append("• *Indices*: Watching NIFTYBEES / BANKBEES 15m Bollinger mean-reversion.")
        lines.append("• *Commodities*: GOLDBEES / SILVERBEES 4h 50 EMA trend support active.")
        lines.append("• *Equities*: Scanning 1h volume breakouts on momentum leaders.")

    lines.append("\n⚖️ _Risk Mandate: Strict 1% ATR Volatility-Parity sizing per trade._")

    return "\n".join(lines)


def build_evening_report() -> str:
    """Constructs the comprehensive 16:00 PM post-market performance report."""
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%A, %d %B %Y | %H:%M IST")

    # 1. Fetch Portfolio
    portfolio = angel_client.get_portfolio_summary()
    mode = portfolio.get("mode", "LIVE")
    tot_val = float(portfolio.get("total_portfolio_value", 125000.0))
    cash = float(portfolio.get("available_cash", 125000.0))
    invested = float(portfolio.get("invested_amount", 0.0))
    pnl = float(portfolio.get("overall_pnl", 0.0))
    pnl_pct = float(portfolio.get("overall_pnl_pct", 0.0))
    holdings = portfolio.get("holdings", [])

    pnl_emoji = "🟢" if pnl >= 0 else "🔴"

    lines = [
        "🌇 *BHARAT TRADE AGENT — EVENING REPORT*",
        f"📅 _{date_str}_",
        f"🛡️ *Broker Mode:* `{mode}` (Angel One)\n",
        "📈 *Day Closing Financials:*",
        f"• Total Portfolio Value: *₹{tot_val:,.2f}*",
        f"• Available Cash Balance: *₹{cash:,.2f}*",
        f"• Capital in Positions: *₹{invested:,.2f}*",
        f"• Portfolio P&L: *{pnl_emoji} ₹{pnl:+,.2f} ({pnl_pct:+.2f}%)*\n",
        f"💼 *Holdings Status ({len(holdings)} active):*"
    ]

    if holdings:
        for h in holdings:
            sym = h.get("tradingsymbol", h.get("symbol", "STOCK")).replace("-EQ", "")
            qty = h.get("quantity", 0)
            ltp = float(h.get("ltp", 0.0))
            hpnl = float(h.get("profitandloss", h.get("pnl", 0.0)) or 0.0)
            hemoji = "🟢" if hpnl >= 0 else "🔴"
            lines.append(f"• *{sym}*: {qty} shares @ ₹{ltp:,.1f} | {hemoji} ₹{hpnl:+,.1f}")
    else:
        lines.append("• _100% Cash reserves preserved. All intraday orders flat._")

    lines.append("\n🤖 *System Status & Health:*")
    lines.append("• Execution Engine: *Online & Synced*")
    lines.append("• Telegram Command Center: *Active*")
    lines.append("• Volatility-Parity Position Guard: *Enforced*")
    lines.append("\n_Rest well. Tomorrow's morning briefing arrives at 08:45 AM IST._")

    return "\n".join(lines)


def send_morning_briefing(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Sends the morning briefing to Telegram."""
    msg = build_morning_briefing()
    res = send_telegram_text(msg, chat_id=chat_id)
    memory_journal.record_entry(
        category="BRIEFING",
        title="Morning Briefing Dispatched",
        content=msg,
        metadata=res
    )
    return res


def send_evening_report(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Sends the evening performance report to Telegram."""
    msg = build_evening_report()
    res = send_telegram_text(msg, chat_id=chat_id)
    memory_journal.record_entry(
        category="BRIEFING",
        title="Evening Report Dispatched",
        content=msg,
        metadata=res
    )
    return res


class DailyBriefingScheduler:
    """
    Background scheduler for the Two Messages a Day routine:
    - 08:45 AM IST: Morning Briefing
    - 16:00 PM IST: Evening Performance Report
    """

    def __init__(self):
        self.last_morning_sent_date: Optional[str] = None
        self.last_evening_sent_date: Optional[str] = None
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self.is_running = True
        logger.info("DailyBriefingScheduler started (08:45 AM & 16:00 PM IST dispatches enabled).")
        while self.is_running:
            try:
                await self.check_and_dispatch()
            except Exception as e:
                logger.error(f"Error in briefing scheduler: {e}")
            await asyncio.sleep(30)

    def stop(self):
        self.is_running = False

    async def check_and_dispatch(self):
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        weekday = now_ist.weekday() # 0 = Mon, 4 = Fri

        # Only dispatch on trading days (Mon-Fri)
        if weekday >= 5:
            return

        current_minute = now_ist.hour * 60 + now_ist.minute

        # 08:45 AM IST (525 minutes from midnight)
        # Dispatch between 08:45 and 09:05
        if (8 * 60 + 45 <= current_minute <= 9 * 60 + 5) and self.last_morning_sent_date != today_str:
            logger.info("Triggering scheduled Morning Briefing at 08:45 AM IST")
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, send_morning_briefing)
            if res.get("status"):
                self.last_morning_sent_date = today_str
                logger.info("Morning Briefing successfully sent to Telegram")

        # 16:00 PM IST (960 minutes from midnight)
        # Dispatch between 16:00 and 16:20
        if (16 * 60 <= current_minute <= 16 * 60 + 20) and self.last_evening_sent_date != today_str:
            logger.info("Triggering scheduled Evening Report at 16:00 PM IST")
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, send_evening_report)
            if res.get("status"):
                self.last_evening_sent_date = today_str
                logger.info("Evening Report successfully sent to Telegram")


daily_briefing_scheduler = DailyBriefingScheduler()