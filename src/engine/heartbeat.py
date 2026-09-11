import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from src.engine.risk_tiers import evaluate_survival_tier, SurvivalTier
from src.engine.constitution import get_constitution_articles, validate_order_against_constitution
from src.engine.memory import memory_journal
from src.engine.position_sizer import calculate_volatility_parity_position
from src.data.macro_data import get_indian_macro_indicators
from src.analysis.screener import get_top_buy_recommendations
from src.broker.angel_one import angel_client
from src.notifications.telegram import send_telegram_text

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
        
        current_minute = now.hour * 60 + now.minute
        # 09:00 - 09:15 = Pre-market
        if 9 * 60 <= current_minute < 9 * 60 + 15:
            return "PRE_MARKET"
        # 09:15 - 15:30 = Regular Trading Hours
        elif 9 * 60 + 15 <= current_minute <= 15 * 60 + 30:
            return "MARKET_OPEN"
        else:
            return "MARKET_CLOSED"

    async def execute_cycle(self) -> Dict[str, Any]:
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
                    ltp = 0.0
                    for h in portfolio.get("holdings", []):
                        h_sym = str(h.get("tradingsymbol", "")).replace("-EQ", "").replace(".NS", "").upper()
                        if h_sym == sym:
                            ltp = float(h.get("ltp") or 0.0)
                            break
                    
                    if ltp <= 0.0:
                        continue

                    sl = float(pos_data.get("stop_loss", 0.0))
                    tp = float(pos_data.get("target_price", 0.0))
                    qty = int(pos_data.get("quantity", 0))

                    if sl > 0 and ltp <= sl:
                        sell_res = angel_client.place_order(
                            symbol=sym,
                            quantity=qty,
                            transaction_type="SELL",
                            order_type="MARKET",
                            price=ltp
                        )
                        if sell_res.get("status"):
                            msg = (
                                f"🔴 *STOP-LOSS TRIGGERED & EXECUTED*\n\n"
                                f"• Stock: *{sym}*\n"
                                f"• Action: *SELL {qty} shares* @ ₹{ltp:.2f}\n"
                                f"• Stop-Loss Level: ₹{sl:.2f}\n"
                                f"• Order ID: `{sell_res.get('order_id')}`\n\n"
                                f"_Capital preservation discipline strictly enforced._"
                            )
                            send_telegram_text(msg)
                            memory_journal.record_entry(
                                category="EXIT",
                                title=f"Stop-Loss Hit: SELL {qty}x {sym}",
                                content=msg,
                                metadata=sell_res
                            )
                            updated_pos.pop(sym, None)

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

        # 4. ACT: Autonomous opportunistic order placement (if AUTOTRADE_ENABLED=true and not locked)
        autotrade_enabled = os.getenv("AUTOTRADE_ENABLED", "true").lower() in ("true", "1")
        trade_locked = os.getenv("TRADE_EXECUTION_LOCKED", "false").lower() in ("true", "1")
        if autotrade_enabled and not trade_locked and self.market_session == "MARKET_OPEN" and self.current_tier.get("trading_allowed", True):
            cash = float(portfolio.get("available_cash", 0.0))
            if cash >= 50.0:
                try:
                    existing_syms = [
                        str(h.get("tradingsymbol", "")).replace("-EQ", "").replace(".NS", "").upper()
                        for h in portfolio.get("holdings", [])
                    ]
                    recs = get_top_buy_recommendations(limit=4)
                    for rec in recs:
                        sym = rec.get("symbol", "")
                        clean_sym = sym.replace(".NS", "").replace("-EQ", "").upper()
                        if clean_sym in existing_syms:
                            continue
                        price = float(rec.get("price", 0.0))
                        conviction = int(rec.get("conviction", 0))

                        if conviction >= 8 and 0 < price <= cash:
                            def _parse_num(v, fallback):
                                try:
                                    if v is None:
                                        return fallback
                                    s = str(v).replace("INR", "").replace("₹", "").replace(",", "").strip()
                                    return float(s)
                                except (ValueError, TypeError):
                                    return fallback

                            raw_sl = _parse_num(rec.get("stop_loss"), price * 0.97)
                            atr_est = float(rec.get("atr", abs(price - raw_sl) / 2.0 if raw_sl else price * 0.015))
                            tier_mult = float(self.current_tier.get("position_size_multiplier", 1.0))

                            pos_plan = calculate_volatility_parity_position(
                                account_equity=current_equity,
                                current_price=price,
                                atr=atr_est,
                                risk_pct=0.01,
                                atr_stop_multiple=2.0,
                                target_rr_ratio=2.0,
                                tier_multiplier=tier_mult,
                                available_cash=cash,
                                max_allocation_pct=0.35
                            )

                            if not pos_plan.get("allowed") or pos_plan.get("quantity", 0) <= 0:
                                continue

                            qty = pos_plan["quantity"]
                            sl = pos_plan["stop_loss"]
                            tp = pos_plan["target_price"]

                            val = validate_order_against_constitution(
                                symbol=sym,
                                price=price,
                                stop_loss=sl,
                                target_price=tp,
                                quantity=qty,
                                portfolio_equity=current_equity
                            )
                            if val.get("allowed"):
                                order_res = angel_client.place_order(
                                    symbol=sym,
                                    quantity=qty,
                                    transaction_type="BUY",
                                    order_type="MARKET",
                                    price=price
                                )
                                if order_res.get("status"):
                                    mode = order_res.get("mode", "LIVE")
                                    oid = order_res.get("order_id", "N/A")
                                    msg = (
                                        f"🤖 *AUTONOMOUS TRADE EXECUTED ({mode})*\n\n"
                                        f"• Stock: *{sym}*\n"
                                        f"• Action: *BUY {qty} shares* @ ₹{price:,.2f}\n"
                                        f"• Stop-Loss: ₹{sl:,.2f} | Target: ₹{tp:,.2f}\n"
                                        f"• Conviction: {conviction}/10\n"
                                        f"• Order ID: `{oid}`\n\n"
                                        f"_Validated by Constitution & Risk Tier: {self.current_tier.get('tier', 'NORMAL')}_"
                                    )
                                    send_telegram_text(msg)
                                    memory_journal.record_entry(
                                        category="EXECUTION",
                                        title=f"Autonomous Trade: BUY {qty}x {sym}",
                                        content=msg,
                                        metadata=order_res
                                    )
                                    # Register for automated stop-loss and profit target exit monitoring
                                    try:
                                        p_data = {}
                                        if os.path.exists(active_file):
                                            with open(active_file, "r", encoding="utf-8") as f:
                                                p_data = json.load(f)
                                        p_data[clean_sym] = {
                                            "symbol": clean_sym,
                                            "quantity": qty,
                                            "entry_price": price,
                                            "stop_loss": sl,
                                            "target_price": tp,
                                            "order_id": oid
                                        }
                                        with open(active_file, "w", encoding="utf-8") as f:
                                            json.dump(p_data, f, indent=2)
                                    except Exception:
                                        pass
                                    break
                except Exception as e:
                    self.last_observation += f" | Order loop warning: {str(e)}"

        return self.get_status()

    async def _loop(self):
        self.is_running = True
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
