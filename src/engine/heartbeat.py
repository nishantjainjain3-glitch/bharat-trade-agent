import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

from src.engine.risk_tiers import evaluate_survival_tier, SurvivalTier
from src.engine.constitution import get_constitution_articles, validate_order_against_constitution
from src.engine.memory import memory_journal
from src.engine.position_sizer import calculate_volatility_parity_position
from src.data.macro_data import get_indian_macro_indicators
from src.analysis.screener import get_top_buy_recommendations
from src.broker.angel_one import angel_client
from src.notifications.telegram import send_telegram_text
from src.engine.exit_manager import compute_positive_trailing_stop
from src.data.holidays import is_nse_holiday

IST = timezone(timedelta(hours=5, minutes=30))

class AutonomousHeartbeat:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.cycle_count = 0
        self.is_running = False
        self.last_beat_time: Optional[str] = None
        self.market_session: str = "INITIALIZING"
        self.current_tier: Dict[str, Any] = {}
        self.last_observation: str = "Heartbeat initialized. Awaiting first cycle."
        self.peak_equity: float = 0.0
        self._task: Optional[asyncio.Task] = None

    def get_market_session(self) -> str:
        now = datetime.now(IST)
        weekday = now.weekday() # 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun
        if weekday >= 5:
            return "WEEKEND_CLOSED"
        
        is_holiday, holiday_name = is_nse_holiday(now)
        if is_holiday:
            return f"HOLIDAY_CLOSED ({holiday_name})"

        # Dual safety check: real-time news advisory detection
        try:
            from src.data.news_data import get_macro_market_news
            macro_news = get_macro_market_news()
            if macro_news.get("market_closure_indicated"):
                reason = macro_news.get("detected_reason") or "News Advisory"
                return f"HOLIDAY_CLOSED ({reason})"
        except Exception:
            pass

        current_minute = now.hour * 60 + now.minute
        # 09:00 - 09:15 = Pre-market
        if 9 * 60 <= current_minute < 9 * 60 + 15:
            return "PRE_MARKET"
        # 09:15 - 15:30 = Regular Trading Hours
        elif 9 * 60 + 15 <= current_minute <= 15 * 60 + 30:
            return "MARKET_OPEN"
        else:
            return "MARKET_CLOSED"

    def _execute_cycle_sync(self) -> Dict[str, Any]:
        """Runs one full Think -> Act -> Observe cycle."""
        self.cycle_count += 1
        now_ist = datetime.now(IST)
        self.last_beat_time = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        self.market_session = self.get_market_session()

        # 1. THINK: Inspect portfolio and macro benchmarks
        portfolio = angel_client.get_portfolio_summary()
        current_equity = float(portfolio.get("total_portfolio_value") or portfolio.get("net_liquidation_value") or 50000.0)
        if self.peak_equity <= 0 or current_equity > self.peak_equity:
            self.peak_equity = current_equity
        peak_equity = self.peak_equity
        
        try:
            macro = get_indian_macro_indicators()
            nifty_day_change = macro.get("NIFTY", {}).get("change_pct", 0.0)
        except Exception:
            nifty_day_change = 0.0

        # 2. ACT: Recalculate survival tier
        self.current_tier = evaluate_survival_tier(
            current_equity=current_equity,
            peak_equity=peak_equity,
            nifty_day_change_pct=nifty_day_change,
            daily_pnl_pct=0.0
        )

        # 3. OBSERVE: Synthesize observation
        if self.market_session == "MARKET_OPEN":
            obs = (
                f"Heartbeat #{self.cycle_count}: Market OPEN. Nifty 50: {nifty_day_change:+.2f}%. "
                f"Survival Tier: {self.current_tier['tier']} ({self.current_tier['position_size_multiplier']}x allocation). "
                f"Portfolio equity: INR {current_equity:,.2f}."
            )
        else:
            obs = (
                f"Heartbeat #{self.cycle_count}: Session {self.market_session}. "
                f"Survival Tier: {self.current_tier['tier']}. System in low-compute stand-by."
            )
        
        self.last_observation = obs

        # Log observation every 5 cycles or on tier shift
        if self.cycle_count % 5 == 1 or self.current_tier["tier"] != SurvivalTier.NORMAL.value:
            memory_journal.record_entry(
                category="HEARTBEAT",
                title=f"Cycle #{self.cycle_count}: {self.market_session}",
                content=obs,
                metadata={
                    "cycle": self.cycle_count,
                    "session": self.market_session,
                    "tier": self.current_tier["tier"],
                    "nifty_change": nifty_day_change
                }
            )

        # 3.5. MONITOR & EXIT: Evaluate active positions against stop-loss and profit target
        active_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "active_positions.json")
        if self.market_session == "MARKET_OPEN" and os.path.exists(active_file):
            try:
                import json
                with open(active_file, "r", encoding="utf-8") as f:
                    active_pos = json.load(f)

                updated_pos = dict(active_pos)
                for sym, pos_data in active_pos.items():
                    qty = int(pos_data.get("quantity", 0))
                    sl = float(pos_data.get("stop_loss", 0.0))
                    tp = float(pos_data.get("target_price", 0.0))
                    if qty <= 0:
                        continue

                    ltp = 0.0
                    for h in portfolio.get("holdings", []):
                        h_sym = str(h.get("tradingsymbol", "")).replace("-EQ", "").replace(".NS", "").upper()
                        if h_sym == sym:
                            ltp = float(h.get("ltp") or 0.0)
                            break
                    
                    if ltp <= 0.0:
                        try:
                            from src.data.market_data import get_stock_quote
                            q = get_stock_quote(f"{sym}.NS")
                            ltp = float(q.get("current_price") or 0.0)
                        except Exception:
                            pass

                    if ltp <= 0.0:
                        continue

                    entry_price = float(pos_data.get("entry_price", ltp))
                    highest_price = float(pos_data.get("highest_price", max(entry_price, ltp)))
                    if ltp > highest_price:
                        highest_price = ltp
                        pos_data["highest_price"] = highest_price
                        updated_pos[sym] = pos_data

                    trailing_dist = float(pos_data.get("trailing_distance_pct", 2.0))
                    activation_pct = float(pos_data.get("activation_profit_pct", 1.5))
                    is_dust = bool(pos_data.get("is_dust", False) or (qty <= 1 and (qty * ltp) < 500))

                    trail = compute_positive_trailing_stop(
                        entry_price=entry_price,
                        current_price=ltp,
                        highest_price=highest_price,
                        initial_stop_loss=sl,
                        activation_profit_pct=activation_pct,
                        trailing_distance_pct=trailing_dist
                    )
                    effective_sl = trail.get("effective_stop_loss", sl)
                    is_trailing = trail.get("is_trailing_active", False)

                    # A. Partial de-risking trim execution
                    trim_qty = int(pos_data.get("trim_quantity", 0))
                    trim_tp = float(pos_data.get("trim_target_price", 0.0))
                    if trim_qty > 0 and trim_tp > 0 and ltp >= trim_tp:
                        actual_trim = min(trim_qty, qty)
                        sell_res = angel_client.place_order(
                            symbol=sym,
                            quantity=actual_trim,
                            transaction_type="SELL",
                            order_type="MARKET",
                            price=ltp
                        )
                        if sell_res.get("status"):
                            rem_qty = qty - actual_trim
                            pos_data["quantity"] = rem_qty
                            pos_data.pop("trim_quantity", None)
                            pos_data.pop("trim_target_price", None)
                            if rem_qty <= 0:
                                updated_pos.pop(sym, None)
                            else:
                                updated_pos[sym] = pos_data
                            liberated = actual_trim * ltp
                            msg = (
                                f"🟡 *DE-RISKING TRIM EXECUTED*\n\n"
                                f"• Stock: *{sym}*\n"
                                f"• Action: *SELL {actual_trim} shares* @ ₹{ltp:.2f}\n"
                                f"• Liberated Cash: *₹{liberated:,.2f}*\n"
                                f"• Remaining Exposure: {rem_qty} shares\n"
                                f"• Order ID: `{sell_res.get('order_id')}`\n\n"
                                f"_Capital concentration reduced. Dry powder restored._"
                            )
                            send_telegram_text(msg)
                            memory_journal.record_entry(
                                category="TRIM",
                                title=f"De-Risk Trim: SELL {actual_trim}x {sym}",
                                content=msg,
                                metadata=sell_res
                            )
                            continue

                    # B. Full stop-loss / trailing exit
                    if effective_sl > 0 and ltp <= effective_sl:
                        if is_dust:
                            # Skip isolated single-share liquidation to prevent DP charges exceeding trade value
                            continue

                        sell_res = angel_client.place_order(
                            symbol=sym,
                            quantity=qty,
                            transaction_type="SELL",
                            order_type="MARKET",
                            price=ltp
                        )
                        if sell_res.get("status"):
                            exit_type = "TRAILING STOP-LOSS" if is_trailing else "HARD STOP-LOSS"
                            msg = (
                                f"🔴 *{exit_type} TRIGGERED & EXECUTED*\n\n"
                                f"• Stock: *{sym}*\n"
                                f"• Action: *SELL {qty} shares* @ ₹{ltp:.2f}\n"
                                f"• Exit Trigger: ₹{effective_sl:.2f}\n"
                                f"• Highest Peak: ₹{highest_price:.2f}\n"
                                f"• Order ID: `{sell_res.get('order_id')}`\n\n"
                                f"_Capital preservation discipline strictly enforced._"
                            )
                            send_telegram_text(msg)
                            updated_pos.pop(sym, None)
                            try:
                                from src.engine.protections import protections_manager
                                loss_pct = round(((ltp - float(pos_data.get("entry_price", ltp))) / float(pos_data.get("entry_price", ltp))) * 100.0, 2)
                                protections_manager.record_stoploss_hit(sym, ltp, loss_pct)
                            except Exception as pe:
                                logger.warning("Protections record warning: %s", pe)

                    elif tp > 0 and ltp >= tp:
                        sell_res = angel_client.place_order(
                            symbol=sym,
                            quantity=qty,
                            transaction_type="SELL",
                            order_type="MARKET",
                            price=ltp
                        )
                        if sell_res.get("status"):
                            msg = (
                                f"🟢 *PROFIT TARGET HIT & EXECUTED*\n\n"
                                f"• Stock: *{sym}*\n"
                                f"• Action: *SELL {qty} shares* @ ₹{ltp:.2f}\n"
                                f"• Target Level: ₹{tp:.2f}\n"
                                f"• Order ID: `{sell_res.get('order_id')}`\n\n"
                                f"_Target realized. Capital booked to available cash._"
                            )
                            send_telegram_text(msg)
                            memory_journal.record_entry(
                                category="EXIT",
                                title=f"Target Realized: SELL {qty}x {sym}",
                                content=msg,
                                metadata=sell_res
                            )
                            updated_pos.pop(sym, None)

                if len(updated_pos) != len(active_pos):
                    with open(active_file, "w", encoding="utf-8") as f:
                        json.dump(updated_pos, f, indent=2)
            except Exception as e:
                self.last_observation += f" | Exit monitor warning: {str(e)}"

        # 4. ACT: Autonomous opportunistic order placement & capital recycling
        autotrade_enabled = os.getenv("AUTOTRADE_ENABLED", "true").lower() in ("true", "1")
        trade_locked = os.getenv("TRADE_EXECUTION_LOCKED", "false").lower() in ("true", "1")
        if autotrade_enabled and not trade_locked and self.market_session == "MARKET_OPEN" and self.current_tier.get("trading_allowed", True):
            try:
                import time
                from src.engine.portfolio_recycler import PortfolioRecycler
                from src.analysis.screener import scan_institutional_risk_budgeted_trades

                cash = float(portfolio.get("available_cash", 0.0))
                existing_syms = [
                    str(h.get("tradingsymbol", "")).replace("-EQ", "").replace(".NS", "").upper()
                    for h in portfolio.get("holdings", [])
                ]

                # Check user-approved curated buy targets first (e.g. inspected breakout leaders)
                target_cand = None
                curated_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "curated_buy_targets.json")
                if os.path.exists(curated_file):
                    try:
                        import json
                        with open(curated_file, "r", encoding="utf-8") as f:
                            curated_list = json.load(f)
                        from src.engine.protections import protections_manager
                        for c in sorted(curated_list, key=lambda x: x.get("priority", 99)):
                            csym = c.get("clean_symbol", "").upper()
                            if csym not in existing_syms:
                                prot = protections_manager.evaluate_entry_protections(
                                    symbol=csym,
                                    current_equity=current_equity,
                                    peak_equity=peak_equity,
                                    daily_loss_pct=0.0
                                )
                                if not prot.get("allowed", True):
                                    logger.info("Skipping curated candidate %s: %s", csym, prot.get("violations"))
                                    continue
                                target_cand = {
                                    "symbol": c.get("symbol", f"{csym}.NS"),
                                    "clean_symbol": csym,
                                    "price": float(c.get("price", 0.0)),
                                    "stop_loss": float(c.get("stop_loss", 0.0)),
                                    "target_price": float(c.get("target_price", 0.0)),
                                    "atr": float(c.get("atr", 5.0)),
                                    "shares": int(c.get("shares", 10)),
                                    "conviction": int(c.get("conviction", 9)),
                                    "rationale": c.get("rationale", "")
                                }
                                break
                    except Exception as e_cur:
                        logger.warning("Curated targets read warning: %s", str(e_cur))

                if not target_cand:
                    try:
                        inst_scan = scan_institutional_risk_budgeted_trades(capital=current_equity, risk_pct=0.015, limit=5)
                        for c in inst_scan.get("candidates", []):
                            csym = c.get("symbol", "").upper()
                            if csym not in existing_syms:
                                target_cand = {
                                    "symbol": c.get("full_symbol", f"{csym}.NS"),
                                    "clean_symbol": csym,
                                    "price": float(c.get("current_price", 0.0)),
                                    "stop_loss": float(c.get("position_sizing", {}).get("stop_loss", 0.0)),
                                    "target_price": float(c.get("position_sizing", {}).get("target", 0.0)),
                                    "atr": float(c.get("position_sizing", {}).get("atr", 5.0)),
                                    "shares": int(c.get("position_sizing", {}).get("shares", 10)),
                                    "conviction": int(c.get("conviction_score", 40) // 10)
                                }
                                break
                    except Exception as ex_scan:
                        logger.warning("Institutional scan in heartbeat: %s", str(ex_scan))

                if not target_cand:
                    recs = get_top_buy_recommendations(limit=4)
                    for rec in recs:
                        sym = rec.get("symbol", "")
                        clean_sym = sym.replace(".NS", "").replace("-EQ", "").upper()
                        if clean_sym in existing_syms:
                            continue
                        price = float(rec.get("price", 0.0))
                        conviction = int(rec.get("conviction", 0))
                        if conviction >= 8 and price > 0:
                            target_cand = {
                                "symbol": sym,
                                "clean_symbol": clean_sym,
                                "price": price,
                                "stop_loss": float(rec.get("stop_loss") or price * 0.97),
                                "target_price": float(rec.get("target_price") or price * 1.05),
                                "atr": float(rec.get("atr", price * 0.015)),
                                "shares": 10,
                                "conviction": conviction
                            }
                            break

                if target_cand:
                    clean_sym = target_cand["clean_symbol"]
                    sym = target_cand["symbol"]
                    price = target_cand["price"]
                    conviction = target_cand["conviction"]
                    atr_est = target_cand["atr"]

                    target_qty = max(1, min(target_cand.get("shares", 10), 15))
                    needed_cash = round(price * target_qty, 2)

                    # SELF-FUNDING REBALANCER: If cash is insufficient, recycle capital from overconcentrated holdings
                    if cash < needed_cash:
                        recycler = PortfolioRecycler(max_single_stock_pct=25.0)
                        rebal_plan = recycler.generate_capital_recycling_plan(
                            portfolio_summary=portfolio,
                            required_cash=needed_cash,
                            target_symbol=clean_sym
                        )

                        if rebal_plan.get("status") == "RECYCLING_PLAN_READY":
                            for act in rebal_plan.get("actions_needed", []):
                                trim_sym = act["symbol"]
                                trim_qty = int(act["quantity"])
                                trim_price = float(act["price"])

                                trim_res = angel_client.place_order(
                                    symbol=trim_sym,
                                    quantity=trim_qty,
                                    transaction_type="SELL",
                                    order_type="MARKET",
                                    price=trim_price
                                )
                                if trim_res.get("status"):
                                    rebal_msg = (
                                        f"🔄 *AUTONOMOUS PORTFOLIO REBALANCING EXECUTED*\n\n"
                                        f"• Sold: *{trim_qty} shares of {trim_sym}* @ ₹{trim_price:.2f}\n"
                                        f"• Gross Cash Released: ₹{act['gross_cash_released']:,.2f}\n"
                                        f"• Rationale: {act['rationale']}\n"
                                        f"• Target Setup Funded: *{clean_sym}*\n"
                                        f"• Order ID: `{trim_res.get('order_id')}`\n\n"
                                        f"_Autonomous self-funding successfully generated cash from equity._"
                                    )
                                    send_telegram_text(rebal_msg)
                                    memory_journal.record_entry(
                                        category="REBALANCE",
                                        title=f"Capital Recycling: SOLD {trim_qty}x {trim_sym}",
                                        content=rebal_msg,
                                        metadata=trim_res
                                    )
                                else:
                                    rej_msg = (
                                        f"⚠️ *REBALANCING ORDER REJECTED BY BROKER*\n\n"
                                        f"• Stock: *{trim_sym}* (Sell {trim_qty} shares)\n"
                                        f"• Error: `{trim_res.get('message')}`\n\n"
                                        f"_Action Required: Ensure outbound IP {angel_client.public_ip} is whitelisted in SmartAPI portal._"
                                    )
                                    logger.warning("Rebalance trim rejected: %s", rej_msg)
                                    send_telegram_text(rej_msg)
                            time.sleep(2)
                            portfolio = angel_client.get_portfolio_summary()
                            cash = float(portfolio.get("available_cash", 0.0))

                    # Now execute BUY order if cash covers the trade
                    if cash >= price and price > 0:
                        buy_qty = min(target_qty, int(cash / price))
                        if buy_qty > 0:
                            sl = target_cand["stop_loss"]
                            tp = target_cand["target_price"]

                            val = validate_order_against_constitution(
                                symbol=sym,
                                price=price,
                                stop_loss=sl,
                                target_price=tp,
                                quantity=buy_qty,
                                portfolio_equity=current_equity
                            )
                            if val.get("allowed"):
                                order_res = angel_client.place_order(
                                    symbol=sym,
                                    quantity=buy_qty,
                                    transaction_type="BUY",
                                    order_type="MARKET",
                                    price=price
                                )
                                if order_res.get("status"):
                                    mode = order_res.get("mode", "LIVE")
                                    oid = order_res.get("order_id", "N/A")

                                    fill_price = price
                                    msg = (
                                        f"🤖 *AUTONOMOUS TRADE EXECUTED ({mode})*\n\n"
                                        f"• Stock: *{sym}*\n"
                                        f"• Action: *BUY {buy_qty} shares* @ ₹{fill_price:,.2f}\n"
                                        f"• Stop-Loss: ₹{sl:,.2f} | Target: ₹{tp:,.2f}\n"
                                        f"• Conviction: {conviction}/10\n"
                                        f"• Order ID: `{oid}`\n\n"
                                        f"_Self-funded trade executed automatically._"
                                    )
                                    send_telegram_text(msg)
                                    memory_journal.record_entry(
                                        category="EXECUTION",
                                        title=f"Autonomous Trade: BUY {buy_qty}x {sym}",
                                        content=msg,
                                        metadata=order_res
                                    )
                                    try:
                                        p_data = {}
                                        if os.path.exists(active_file):
                                            with open(active_file, "r", encoding="utf-8") as f:
                                                p_data = json.load(f)
                                        p_data[clean_sym] = {
                                            "symbol": clean_sym,
                                            "quantity": buy_qty,
                                            "entry_price": fill_price,
                                            "stop_loss": sl,
                                            "target_price": tp,
                                            "order_id": oid
                                        }
                                        with open(active_file, "w", encoding="utf-8") as f:
                                            json.dump(p_data, f, indent=2)
                                    except Exception:
                                        pass
                                else:
                                    rej_msg = (
                                        f"⚠️ *BUY ORDER REJECTED BY BROKER*\n\n"
                                        f"• Stock: *{sym}* (Buy {buy_qty} shares)\n"
                                        f"• Error: `{order_res.get('message')}`\n\n"
                                        f"_Action Required: Ensure outbound IP {angel_client.public_ip} is whitelisted in SmartAPI portal._"
                                    )
                                    logger.warning("Target buy rejected: %s", rej_msg)
                                    send_telegram_text(rej_msg)
            except Exception as e:
                self.last_observation += f" | Rebalancer loop warning: {str(e)}"
        return self.get_status()

    async def execute_cycle(self) -> Dict[str, Any]:
        """Runs one full Think -> Act -> Observe cycle non-blockingly in a worker thread."""
        return await asyncio.to_thread(self._execute_cycle_sync)

    async def _loop(self):
        self.is_running = True
        await asyncio.sleep(3)
        while self.is_running:
            try:
                await self.execute_cycle()
            except Exception as e:
                self.last_observation = f"Heartbeat execution error: {str(e)}"
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if not self.is_running or self._task is None:
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "cycle_count": self.cycle_count,
            "last_beat_time": self.last_beat_time,
            "interval_seconds": self.interval_seconds,
            "market_session": self.market_session,
            "survival_tier": self.current_tier if self.current_tier else evaluate_survival_tier(125000.0, 125000.0),
            "last_observation": self.last_observation,
            "constitution_articles": get_constitution_articles()
        }

agent_heartbeat = AutonomousHeartbeat(interval_seconds=60)
