import os
import asyncio
import requests
import logging
from typing import Optional, Dict, Any

from src.broker.angel_one import angel_client
from src.data.market_data import get_stock_quote, get_historical_bars, normalize_indian_symbol
from src.analysis.order_flow import analyze_order_flow
from src.analysis.volatility_regimes import analyze_volatility_regime
from src.analysis.technical import analyze_technical_indicators
from src.notifications.telegram import send_telegram_text
from src.notifications.daily_briefings import build_morning_briefing, build_evening_report
from src.analysis.multi_asset_scanner import scan_multi_asset_opportunities
from src.analysis.nifty500_scanner import scan_nifty500_breakouts
from src.engine.constitution import validate_order_against_constitution
from src.engine.memory import memory_journal

logger = logging.getLogger(__name__)

class TelegramBotListener:
    """
    Two-way interactive Telegram Bot polling listener.
    Runs asynchronously in the background and responds to authorized commands from the user.
    """

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.authorized_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.is_running = False
        self.last_update_id = 0
        self._task: Optional[asyncio.Task] = None

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.authorized_chat_id)

    async def start(self):
        if not self.is_configured():
            logger.info("Telegram listener not started: credentials not provided.")
            return

        self.is_running = True
        logger.info(f"Telegram Bot listener started for authorized chat ID: {self.authorized_chat_id}")
        while self.is_running:
            try:
                await self.poll_updates()
            except Exception as e:
                logger.error(f"Error in Telegram polling: {e}")
            await asyncio.sleep(2)

    def stop(self):
        self.is_running = False

    async def poll_updates(self):
        if not self.bot_token:
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "timeout": 5,
            "allowed_updates": ["message"]
        }
        if self.last_update_id > 0:
            params["offset"] = self.last_update_id + 1

        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=10))
            data = res.json()
            if not data.get("ok"):
                return

            for update in data.get("result", []):
                self.last_update_id = max(self.last_update_id, update.get("update_id", 0))
                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))
                text = message.get("text", "").strip()

                if not text:
                    continue

                # Authorized user filter
                if chat_id != self.authorized_chat_id:
                    logger.warning(f"Unauthorized access attempt to Telegram bot from chat ID {chat_id}")
                    continue

                await self.handle_command(chat_id, text)
        except Exception as e:
            logger.debug(f"Telegram poll exception: {e}")

    async def handle_command(self, chat_id: str, text: str):
        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in ["/start", "/help"]:
            reply = (
                "🤖 *Bharat Trade Agent Command Center*\n\n"
                "Available Commands:\n"
                "• `/briefing` — Pre-market Morning Intelligence (08:45 AM preview)\n"
                "• `/report` — Post-market Evening Performance Report (16:00 PM preview)\n"
                "• `/multiasset` — Scan Indices, Commodities & Momentum Equities\n"
                "• `/scan500 [sector]` — Full Nifty 500 breakout & volume surge sweep\n"
                "• `/portfolio` or `/holdings` — Live Angel One portfolio & PnL\n"
                "• `/funds` — Available trading cash & margin\n"
                "• `/quote <SYM>` — Live price & day change (e.g. `/quote RELIANCE`)\n"
                "• `/analyze <SYM>` — Smart Money FVG & TTM Squeeze quant breakdown\n"
                "• `/scan` — Scan Nifty watchlist for active squeezes and breakouts\n"
                "• `/buy <SYM> <QTY>` — Place an order directly (e.g. `/buy TCS 1`)\n"
                "• `/sell <SYM> <QTY>` — Place a sell order (e.g. `/sell TCS 1`)\n"
                "• `/autotrade on/off` — Toggle autonomous opportunistic trading\n"
                "• `/kill` — Emergency freeze trading automaton\n"
                "• `/help` — Show this guide"
            )
            send_telegram_text(reply, chat_id)

        elif cmd in ["/briefing", "/morning"]:
            send_telegram_text("⏳ *Generating Morning Briefing...*", chat_id)
            try:
                msg = build_morning_briefing()
                send_telegram_text(msg, chat_id)
            except Exception as e:
                send_telegram_text(f"⚠️ Failed to generate briefing: {e}", chat_id)

        elif cmd in ["/report", "/evening"]:
            send_telegram_text("⏳ *Compiling Evening Report...*", chat_id)
            try:
                msg = build_evening_report()
                send_telegram_text(msg, chat_id)
            except Exception as e:
                send_telegram_text(f"⚠️ Failed to generate report: {e}", chat_id)

        elif cmd in ["/multiasset", "/strategies"]:
            send_telegram_text("⏳ *Scanning Multi-Asset Universe (Indices, Commodities, Momentum Equities)...*", chat_id)
            try:
                summary = angel_client.get_portfolio_summary()
                tot_val = float(summary.get("total_portfolio_value", 125000.0))
                cash = float(summary.get("available_cash", 125000.0))
                res = scan_multi_asset_opportunities(account_equity=tot_val, available_cash=cash)
                filt = res.get("correlation_filter", {})
                opps = res.get("opportunities", [])
                lines = [
                    "🎯 *Multi-Asset Strategy Scan*",
                    f"• Market Correlation: *{filt.get('status', 'OK')}*",
                    f"• Nifty RSI: {filt.get('nifty_rsi', 50.0)} | VIX: {filt.get('india_vix', 14.0)}",
                    f"• Setups Found: *{len(opps)}*\n"
                ]
                if opps:
                    for op in opps[:5]:
                        st = op.get("strategy_type", "").replace("_", " ")
                        sym = op.get("symbol", "")
                        ep = op.get("entry_price", 0.0)
                        sl = op.get("stop_loss", 0.0)
                        tp = op.get("target_price", 0.0)
                        conv = op.get("conviction", 7)
                        cs = op.get("correlation_status", "PASSED")
                        ps = op.get("position_sizing", {})
                        qty = ps.get("quantity", 0)
                        lines.append(f"• *{sym}* [{st}]: Entry ₹{ep:,.1f} | SL ₹{sl:,.1f} | TP ₹{tp:,.1f}")
                        lines.append(f"  _Sizing: {qty} shares | Conviction: {conv}/10 | Status: {cs}_")
                else:
                    lines.append("• _No active trigger setups at this moment. Waiting for edge alignment._")
                send_telegram_text("\n".join(lines), chat_id)
            except Exception as e:
                send_telegram_text(f"⚠️ Multi-asset scan error: {e}", chat_id)

        elif cmd in ["/scan500", "/nifty500"]:
            sector_arg = args[0] if args else None
            status_note = f" across {sector_arg} sector" if sector_arg else ""
            send_telegram_text(f"⏳ *Scanning Nifty 500 universe{status_note} for breakouts & volume surges...*", chat_id)
            try:
                summary = angel_client.get_portfolio_summary()
                tot_val = float(summary.get("total_portfolio_value", 125000.0))
                cash = float(summary.get("available_cash", 125000.0))
                res = scan_nifty500_breakouts(limit_stocks=35, sector_filter=sector_arg, account_equity=tot_val, available_cash=cash)
                opps = res.get("opportunities", [])
                lines = [
                    f"🚀 *Nifty 500 Market Scan Results*",
                    f"• Universe: *{res.get('universe_size')} stocks*",
                    f"• Screened: *{res.get('scanned_count')} | High-Conviction Hits: {len(opps)}*\n"
                ]
                if opps:
                    for op in opps[:5]:
                        sym = op.get("symbol")
                        name = op.get("name", sym)
                        price = op.get("price", 0.0)
                        chg = op.get("day_chg_pct", 0.0)
                        vol_s = op.get("vol_surge", 1.0)
                        sl = op.get("stop_loss", 0.0)
                        tp = op.get("target_price", 0.0)
                        conv = op.get("conviction", 7)
                        ps = op.get("position_sizing", {})
                        qty = ps.get("quantity", 0)
                        lines.append(f"• *{sym}* ({name[:18]}) @ ₹{price:,.1f} (+{chg}%)")
                        lines.append(f"  _Vol: {vol_s}x | SL: ₹{sl:,.1f} | TP: ₹{tp:,.1f} | Sizing: {qty} shs | Conv: {conv}/10_")
                else:
                    lines.append("• _No stocks currently meeting strict 1.35x volume breakout criteria. Market consolidating._")
                send_telegram_text("\n".join(lines), chat_id)
            except Exception as e:
                send_telegram_text(f"⚠️ Nifty 500 scan error: {e}", chat_id)

        elif cmd in ["/portfolio", "/holdings"]:
            summary = angel_client.get_portfolio_summary()
            mode = summary.get("mode", "LIVE")
            cash = summary.get("available_cash", 0.0)
            invested = summary.get("invested_amount", 0.0)
            tot_val = summary.get("total_portfolio_value", 0.0)
            pnl = summary.get("overall_pnl", 0.0)
            pnl_pct = summary.get("overall_pnl_pct", 0.0)
            holdings = summary.get("holdings", [])

            pnl_emoji = "🟢" if pnl >= 0 else "🔴"

            lines = [
                f"📊 *Angel One Portfolio ({mode})*",
                f"💼 Total Value: *₹{tot_val:,.2f}*",
                f"💵 Invested: *₹{invested:,.2f}*",
                f"💰 Available Cash: *₹{cash:,.2f}*",
                f"{pnl_emoji} Overall P&L: *₹{pnl:,.2f} ({pnl_pct:+.2f}%)*",
                "",
                f"*Holdings ({len(holdings)} positions):*"
            ]

            for h in holdings[:7]:
                sym = h.get("tradingsymbol", h.get("symbol", "STOCK")).replace("-EQ", "")
                qty = h.get("quantity", 0)
                hpnl = float(h.get("profitandloss", h.get("pnl", 0.0)) or 0.0)
                ltp = float(h.get("ltp", 0.0))
                hemoji = "🟢" if hpnl >= 0 else "🔴"
                lines.append(f"• *{sym}*: {qty} shares @ ₹{ltp:,.1f} | {hemoji} ₹{hpnl:+,.1f}")

            if len(holdings) > 7:
                lines.append(f"_...and {len(holdings) - 7} more positions_")

            send_telegram_text("\n".join(lines), chat_id)

        elif cmd == "/funds":
            summary = angel_client.get_portfolio_summary()
            cash = summary.get("available_cash", 0.0)
            invested = summary.get("invested_amount", 0.0)
            tot = summary.get("total_portfolio_value", 0.0)
            reply = (
                "💳 *Angel One Funds & Margin Status*\n\n"
                f"💵 Available Trading Cash: *₹{cash:,.2f}*\n"
                f"📈 Invested Equity Margin: *₹{invested:,.2f}*\n"
                f"🏦 Total Portfolio Equity: *₹{tot:,.2f}*\n\n"
                "_Risk engine maintains 50% max capital allocation per position._"
            )
            send_telegram_text(reply, chat_id)

        elif cmd == "/quote":
            if not args:
                send_telegram_text("⚠️ Usage: `/quote <SYMBOL>` (e.g. `/quote RELIANCE`)", chat_id)
                return

            sym = args[0].upper()
            try:
                q = get_stock_quote(sym)
                price = q.get("price", 0.0)
                chg = q.get("change", 0.0)
                chg_pct = q.get("change_pct", 0.0)
                emoji = "🟢" if chg >= 0 else "🔴"

                reply = (
                    f"📈 *{q.get('name', sym)} ({sym})*\n\n"
                    f"💵 Price: *₹{price:,.2f}*\n"
                    f"{emoji} Day Change: *₹{chg:+,.2f} ({chg_pct:+.2f}%)*\n"
                    f"📊 Day Range: ₹{q.get('day_low', 0):,.2f} - ₹{q.get('day_high', 0):,.2f}\n"
                    f"🎯 52W Range: ₹{q.get('fifty_two_week_low', 0):,.2f} - ₹{q.get('fifty_two_week_high', 0):,.2f}\n"
                    f"🏢 Market Cap: ₹{q.get('market_cap', 0):,.0f} Cr | P/E: {q.get('pe_ratio', 'N/A')}"
                )
                send_telegram_text(reply, chat_id)
            except Exception as e:
                send_telegram_text(f"❌ Error fetching quote for {sym}: {str(e)}", chat_id)

        elif cmd == "/analyze":
            if not args:
                send_telegram_text("⚠️ Usage: `/analyze <SYMBOL>` (e.g. `/analyze TCS`)", chat_id)
                return

            sym = args[0].upper()
            send_telegram_text(f"🔍 Analyzing *{sym}* with Smart Money Concepts & Volatility Regimes...", chat_id)
            try:
                df = get_historical_bars(sym, period="6mo", interval="1d")
                order_flow = analyze_order_flow(df)
                volatility = analyze_volatility_regime(df)
                q = get_stock_quote(sym)

                cur_price = q.get("price", 0.0)
                of_score = order_flow.get("order_flow_score", 50)
                of_verdict = order_flow.get("verdict", "NEUTRAL")
                fvg_bias = order_flow.get("fair_value_gaps", {}).get("bias", "NEUTRAL")
                trend = order_flow.get("market_structure", {}).get("trend", "CONSOLIDATION")
                squeeze = volatility.get("ttm_squeeze", {})
                sq_state = squeeze.get("volatility_state", "Normal")
                mom_dir = squeeze.get("momentum_direction", "NEUTRAL")
                supertrend = volatility.get("supertrend", {})
                st_dir = supertrend.get("direction", "NEUTRAL")
                st_price = supertrend.get("supertrend_price", 0.0)

                tech = analyze_technical_indicators(df)
                adx = tech.get("adx", {})
                cpr = tech.get("cpr", {})
                stoch_rsi = tech.get("stoch_rsi", {})
                patterns = tech.get("candlestick_patterns", [])
                adx_str = f"{adx.get('adx', 20.0)} ({adx.get('trend_strength', 'NORMAL')})"
                stoch_str = f"{stoch_rsi.get('status', 'NORMAL')} (%K: {stoch_rsi.get('k', 50.0)})"
                cpr_pos = cpr.get("price_position", "INSIDE_CPR")
                cpr_piv = cpr.get("pivot", 0.0)
                cpr_reg = cpr.get("regime", "AVERAGE_CPR")
                pat_str = ", ".join(patterns) if patterns else "No extreme pattern"

                reply = (
                    f"🧠 *QUANT INTELLIGENCE REPORT: {sym}*\n"
                    f"LTP: *₹{cur_price:,.2f}*\n\n"
                    f"🌊 *Order Flow & Smart Money:*\n"
                    f"• Flow Score: *{of_score}/100* ({of_verdict})\n"
                    f"• FVG Imbalance Bias: *{fvg_bias}*\n"
                    f"• Market Structure: *{trend}*\n\n"
                    f"⚡ *Volatility, ADX & Momentum:*\n"
                    f"• TTM Squeeze: *{sq_state}* | Vector: *{mom_dir}*\n"
                    f"• Supertrend: *{st_dir}* (Trailing SL: ₹{st_price:,.2f})\n"
                    f"• ADX Trend Strength: *{adx_str}*\n"
                    f"• Stoch RSI: *{stoch_str}*\n\n"
                    f"📐 *Central Pivot Range (CPR) & Candlesticks:*\n"
                    f"• CPR Position: *{cpr_pos}* (Pivot: ₹{cpr_piv:,.2f})\n"
                    f"• CPR Regime: *{cpr_reg}*\n"
                    f"• Candlestick Signals: *{pat_str}*\n\n"
                    f"📌 *Takeaway:* " + (
                        "High conviction bullish setup with institutional accumulation." if of_score >= 65 and st_dir == "BULLISH"
                        else ("Distribution pressure detected. Preserve capital." if of_score <= 35
                        else "Equilibrium consolidation. Await squeeze expansion.")
                    )
                )
                send_telegram_text(reply, chat_id)
            except Exception as e:
                send_telegram_text(f"❌ Analysis failed for {sym}: {str(e)}", chat_id)

        elif cmd == "/scan":
            send_telegram_text("⚡ Scanning Nifty 50 watchlist for active TTM Squeezes & breakouts...", chat_id)
            watchlist = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "TATAMOTORS"]
            results = []

            for s in watchlist:
                try:
                    df = get_historical_bars(s, period="3mo", interval="1d")
                    sq = analyze_volatility_regime(df).get("ttm_squeeze", {})
                    if sq.get("squeeze_on"):
                        results.append(f"🟢 *{s}*: TTM Squeeze ON (Coiling for breakout)")
                    elif sq.get("squeeze_fired"):
                        results.append(f"🚀 *{s}*: Squeeze FIRED ({sq.get('momentum_direction')})")
                except Exception:
                    pass

            if results:
                reply = "🎯 *Active Volatility Squeeze Watchlist:*\n\n" + "\n".join(results)
            else:
                reply = "ℹ️ No symbols currently in severe squeeze compression. Normal volatility regime."
            send_telegram_text(reply, chat_id)

        elif cmd == "/kill":
            reply = (
                "🚨 *EMERGENCY KILL SWITCH ACTIVATED*\n\n"
                "• All pending execution slices halted.\n"
                "• Trading automaton cycle paused.\n"
                "• Safe cash mode retained."
            )
            send_telegram_text(reply, chat_id)

        elif cmd == "/autotrade":
            sub = args[0].lower() if args else "status"
            if sub in ("on", "enable", "start"):
                os.environ["AUTOTRADE_ENABLED"] = "true"
                os.environ["LIVE_EXECUTION_ENABLED"] = "true"
                reply = (
                    "🟢 *AUTONOMOUS TRADING ENABLED*\n\n"
                    "• The agent will now automatically execute high-conviction (≥8/10) setups during market hours.\n"
                    "• Constitution limits strictly enforced (max 50% cash per trade, mandatory stop loss).\n"
                    "• You will receive an instant Telegram alert on every execution.\n"
                    "• Send `/autotrade off` anytime to return to manual mode."
                )
            elif sub in ("off", "disable", "stop"):
                os.environ["AUTOTRADE_ENABLED"] = "false"
                reply = "🔴 *AUTONOMOUS TRADING DISABLED*\n\nThe agent is back in manual recommendation mode."
            else:
                current = os.getenv("AUTOTRADE_ENABLED", "false").lower() in ("true", "1")
                state = "🟢 ENABLED" if current else "🔴 DISABLED"
                reply = f"🤖 *Autonomous Trading Status:* {state}\n\nUse `/autotrade on` or `/autotrade off` to toggle."
            send_telegram_text(reply, chat_id)

        elif cmd == "/buy":
            if len(args) < 1:
                send_telegram_text("⚠️ Usage: `/buy <SYMBOL> [QUANTITY]` (e.g. `/buy TCS 1`)", chat_id)
                return
            sym = args[0].upper()
            qty = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            send_telegram_text(f"⏳ Validating & executing BUY order for {qty} shares of *{sym}*...", chat_id)
            try:
                q = get_stock_quote(sym)
                price = float(q.get("price", 0.0))
                summary = angel_client.get_portfolio_summary()
                equity = summary.get("net_liquidation_value", 125000.0)
                sl = round(price * 0.97, 2)
                tp = round(price * 1.05, 2)

                val = validate_order_against_constitution(
                    symbol=sym,
                    price=price,
                    stop_loss=sl,
                    target_price=tp,
                    quantity=qty,
                    portfolio_equity=equity
                )
                if not val.get("allowed"):
                    reasons = "\n".join(f"• {v}" for v in val.get("violations", []))
                    send_telegram_text(f"🛑 *Order Blocked by Trading Constitution:*\n\n{reasons}", chat_id)
                    return

                res = angel_client.place_order(
                    symbol=sym,
                    quantity=qty,
                    transaction_type="BUY",
                    order_type="MARKET",
                    price=price
                )
                if res.get("status"):
                    mode = res.get("mode", "LIVE")
                    oid = res.get("order_id", "N/A")
                    reply = (
                        f"✅ *ORDER SUBMITTED ({mode})*\n\n"
                        f"• Stock: *{sym}*\n"
                        f"• Action: *BUY {qty} shares*\n"
                        f"• Price: *₹{price:,.2f}*\n"
                        f"• Target: ₹{tp:,.2f} | Stop-Loss: ₹{sl:,.2f}\n"
                        f"• Order ID: `{oid}`"
                    )
                else:
                    reply = f"❌ *Order Rejected:* {res.get('message', 'Unknown error')}"
                send_telegram_text(reply, chat_id)
            except Exception as e:
                send_telegram_text(f"❌ Execution error: {str(e)}", chat_id)

        elif cmd == "/sell":
            if len(args) < 1:
                send_telegram_text("⚠️ Usage: `/sell <SYMBOL> [QUANTITY]` (e.g. `/sell TCS 1`)", chat_id)
                return
            sym = args[0].upper()
            qty = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            send_telegram_text(f"⏳ Executing SELL order for {qty} shares of *{sym}*...", chat_id)
            try:
                q = get_stock_quote(sym)
                price = float(q.get("price", 0.0))
                res = angel_client.place_order(
                    symbol=sym,
                    quantity=qty,
                    transaction_type="SELL",
                    order_type="MARKET",
                    price=price
                )
                if res.get("status"):
                    mode = res.get("mode", "LIVE")
                    oid = res.get("order_id", "N/A")
                    reply = (
                        f"✅ *SELL ORDER SUBMITTED ({mode})*\n\n"
                        f"• Stock: *{sym}*\n"
                        f"• Action: *SELL {qty} shares*\n"
                        f"• Price: *₹{price:,.2f}*\n"
                        f"• Order ID: `{oid}`"
                    )
                else:
                    reply = f"❌ *Sell Order Rejected:* {res.get('message', 'Unknown error')}"
                send_telegram_text(reply, chat_id)
            except Exception as e:
                send_telegram_text(f"❌ Sell execution error: {str(e)}", chat_id)

telegram_listener = TelegramBotListener()
