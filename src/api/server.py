import socket
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.data.market_data import (
    get_stock_quote, 
    get_historical_bars, 
    get_company_fundamentals, 
    get_watchlist_snapshots,
    normalize_indian_symbol,
    get_corporate_financial_history
)
from src.data.macro_data import (
    get_indian_macro_indicators, 
    get_nse_sector_heatmap,
    get_indian_macro_event_probabilities
)
from src.analysis.screener import (
    get_top_buy_recommendations, 
    get_preset_screener_recommendations,
    get_high_momentum_breakouts
)
from src.analysis.backtester import backtest_strategy, run_parameter_sweep
from src.notifications.telegram import send_telegram_trade_alert, send_telegram_text
from src.analysis.technical import analyze_technical_indicators
from src.analysis.fundamental import evaluate_fundamentals
from src.analysis.personas import evaluate_all_investor_personas
from src.analysis.battle_plan import generate_tactical_battle_plan
from src.agents.research_team import run_multi_agent_research, get_llm_client
from src.broker.angel_one import angel_client
from src.engine import (
    agent_heartbeat,
    evaluate_survival_tier,
    SurvivalTier,
    validate_order_against_constitution,
    get_constitution_articles,
    memory_journal
)
from src.engine.exit_manager import get_default_exit_rules
from src.analysis.order_flow import analyze_order_flow
from src.analysis.volatility_regimes import analyze_volatility_regime
from src.broker.execution_algos import execution_engine
from src.notifications.telegram_listener import telegram_listener
from src.notifications.daily_briefings import (
    daily_briefing_scheduler,
    send_morning_briefing,
    send_evening_report,
    build_morning_briefing,
    build_evening_report
)
from src.analysis.multi_asset_scanner import scan_multi_asset_opportunities
from src.analysis.nifty500_scanner import scan_nifty500_breakouts
from src.analysis.screener import scan_vcp_candidates, scan_momentum_rotation, scan_donchian_breakouts, scan_5ema_setups, scan_pbd_setups
from src.analysis.pbd_model import evaluate_patrick_nill_setup, detect_pbd_structure
from src.analysis.frvp import get_frvp_analysis
from src.analysis.order_flow import detect_ict_order_blocks, get_ict_killzone_status
from src.analysis.technical import calculate_india_vix_regime, calculate_5ema_setup
from src.data.macro_data import get_indian_macro_indicators as _get_macro
from src.agents.adversarial_council import adversarial_council
from src.data.research_vault import research_vault

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_heartbeat.start()
    asyncio.create_task(agent_heartbeat.execute_cycle())
    if telegram_listener.is_configured():
        asyncio.create_task(telegram_listener.start())
        asyncio.create_task(daily_briefing_scheduler.start())
    yield
    agent_heartbeat.stop()
    telegram_listener.stop()
    daily_briefing_scheduler.stop()

app = FastAPI(title="Bharat Trade Agent", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_local_network_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class AnalyzeRequest(BaseModel):
    symbol: str

class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "EMA_CROSS"
    period: str = "2y"
    initial_capital: float = 100000.0

class OptimizeRequest(BaseModel):
    symbol: str
    period: str = "6mo"
    initial_capital: float = 100000.0

class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    transaction_type: str = "BUY"
    order_type: str = "MARKET"
    price: Optional[float] = 0.0
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None

class TelegramAlertRequest(BaseModel):
    trade_data: Dict[str, Any]

class WebhookTradeAlert(BaseModel):
    ticker: Optional[str] = None
    symbol: Optional[str] = None
    action: str = "BUY"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    target: Optional[float] = None
    quantity: Optional[int] = None
    strategy: Optional[str] = "TradingView Alert"
    timeframe: Optional[str] = "15m"
    message: Optional[str] = None

class AdversarialAuditRequest(BaseModel):
    symbol: str
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    technicals: Optional[Dict[str, Any]] = None
    fundamentals: Optional[Dict[str, Any]] = None
    news_headlines: Optional[List[str]] = None

class VaultSaveRequest(BaseModel):
    symbol: str
    research: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
@app.get("/api/health")
def get_health_status():
    return {
        "status": "ok",
        "service": "bharat-trade-agent",
        "version": "2.0.0"
    }

@app.get("/api/status")
def get_system_status():
    provider, _ = get_llm_client()
    local_ip = get_local_network_ip()
    hb = agent_heartbeat.get_status()
    return {
        "status": "online",
        "local_ip": local_ip,
        "mobile_access_url": f"http://{local_ip}:8000",
        "llm_provider": provider or "rule_based_engine",
        "angel_one_mode": angel_client.mode,
        "angel_one_configured": angel_client.is_configured,
        "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")),
        "survival_tier": hb.get("survival_tier", {}).get("tier", "NORMAL"),
        "market_session": hb.get("market_session", "UNKNOWN"),
        "autotrade_enabled": os.getenv("AUTOTRADE_ENABLED", "true").lower() in ("true", "1"),
        "live_execution_enabled": os.getenv("LIVE_EXECUTION_ENABLED", "true").lower() in ("true", "1"),
        "trade_execution_locked": angel_client.is_trade_locked()
    }

@app.get("/api/agent/state")
def get_agent_state():
    status = agent_heartbeat.get_status()
    return {
        "heartbeat": status,
        "survival_tier": status.get("survival_tier"),
        "constitution": get_constitution_articles(),
        "recent_journal": memory_journal.get_recent_entries(limit=10)
    }

@app.get("/api/agent/outbound-ip")
def get_outbound_ip_status():
    import requests
    direct_ip = "unknown"
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        direct_ip = r.json().get("ip", "unknown")
    except Exception as e:
        direct_ip = f"error: {str(e)}"

    proxy_configured = bool(angel_client.proxy_url)
    proxy_ip = "not configured"
    proxy_status = "disabled"
    if proxy_configured:
        try:
            r = requests.get("https://api.ipify.org?format=json", proxies=angel_client.proxies, timeout=8)
            proxy_ip = r.json().get("ip", "unknown")
            proxy_status = "connected"
        except Exception as e:
            proxy_ip = f"error: {str(e)}"
            proxy_status = "failed"

    effective_ip = proxy_ip if proxy_configured else direct_ip
    whitelisted_ip = angel_client.public_ip
    return {
        "direct_ip": direct_ip,
        "proxy_configured": proxy_configured,
        "proxy_status": proxy_status,
        "proxy_ip": proxy_ip,
        "effective_outbound_ip": effective_ip,
        "angel_whitelisted_ip": whitelisted_ip,
        "ip_matches_whitelist": (effective_ip == whitelisted_ip)
    }

@app.post("/api/agent/heartbeat/trigger")
async def trigger_heartbeat():
    res = await agent_heartbeat.execute_cycle()
    return res

@app.post("/api/agent/constitution/validate")
def validate_trade_setup(data: Dict[str, Any]):
    portfolio = angel_client.get_portfolio_summary()
    equity = portfolio.get("net_liquidation_value", 125000.0)
    return validate_order_against_constitution(
        symbol=data.get("symbol", ""),
        price=float(data.get("price", 0.0)),
        stop_loss=float(data.get("stop_loss", 0.0)) if data.get("stop_loss") else None,
        target_price=float(data.get("target_price", 0.0)) if data.get("target_price") else None,
        quantity=int(data.get("quantity", 1)),
        portfolio_equity=equity
    )

@app.get("/api/agent/exit-rules")
def get_exit_rules():
    return get_default_exit_rules()

@app.get("/api/recommendations")
def get_recommendations(preset: str = "ALL"):
    return get_preset_screener_recommendations(preset=preset, limit=4)

@app.get("/api/screener/top-buys")
def get_screener_top_buys(preset: str = "ALL"):
    return get_preset_screener_recommendations(preset=preset, limit=4)

@app.get("/api/screener/momentum-breakouts")
def get_screener_momentum_breakouts(limit: int = 5, target_pct: float = 5.5, stop_pct: float = 2.5):
    return get_high_momentum_breakouts(limit=limit, target_pct=target_pct, stop_pct=stop_pct)

@app.get("/api/sectors/rotation")
def get_sectors_rotation():
    return get_nifty_sector_rotation()

@app.get("/api/macro")
def get_macro():
    return get_indian_macro_indicators()

@app.get("/api/macro/catalysts")
def get_macro_catalysts():
    return get_indian_macro_event_probabilities()

@app.get("/api/news/{symbol}")
def get_news(symbol: str):
    return get_indian_stock_news(symbol)

@app.get("/api/watchlist")
def get_watchlist():
    return get_watchlist_snapshots()

@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    try:
        return get_stock_quote(symbol)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/history/{symbol}")
def get_history(symbol: str, period: str = "6mo", interval: str = "1d"):
    try:
        df = get_historical_bars(symbol, period=period, interval=interval)
        df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
        bars = []
        for _, row in df.iterrows():
            bars.append({
                "time": row['DateStr'],
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row.get('Volume', 0))
            })
        return {"symbol": normalize_indian_symbol(symbol), "bars": bars}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sectors")
def get_sectors():
    return get_nse_sector_heatmap()

@app.get("/api/financials/{symbol}")
def get_financials(symbol: str):
    return get_corporate_financial_history(symbol)

@app.post("/api/analyze")
def analyze_stock(req: AnalyzeRequest):
    try:
        quote = get_stock_quote(req.symbol)
        df = get_historical_bars(req.symbol, period="6mo", interval="1d")
        technicals = analyze_technical_indicators(df)
        raw_fundamentals = get_company_fundamentals(req.symbol)
        fundamentals = evaluate_fundamentals(raw_fundamentals)
        news = get_indian_stock_news(req.symbol, quote.get("name", ""))
        order_flow = analyze_order_flow(df)
        research = run_multi_agent_research(quote, technicals, fundamentals, news)
        personas = evaluate_all_investor_personas(quote, fundamentals, technicals=technicals, order_flow=order_flow)
        financials = get_corporate_financial_history(req.symbol)
        hb_status = agent_heartbeat.get_status()
        tier_name = hb_status.get("survival_tier", {}).get("tier", "NORMAL")
        battle_plan = generate_tactical_battle_plan(quote, technicals, fundamentals, research, survival_tier=tier_name)
        
        return {
            "quote": quote,
            "technicals": technicals,
            "fundamentals": fundamentals,
            "news": news,
            "order_flow": order_flow,
            "research": research,
            "personas": personas,
            "financials": financials,
            "battle_plan": battle_plan
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/playbook/creators")
def get_creator_playbook():
    return {
        "status": "success",
        "creators": {
            "ray_fu": {
                "handle": "@raycfu",
                "name": "Ray Fu",
                "title": "Quantitative Trading Bot & Loop Engineering",
                "core_concepts": [
                    {
                        "name": "1% ATR Volatility Sizing",
                        "description": "Calculates position sizing so that the distance between entry and stop-loss (1.5x - 2.0x daily ATR) risks strictly 1.0% of portfolio equity.",
                        "rule": "Position Size = (Portfolio Equity * 0.01) / (2.0 * ATR)"
                    },
                    {
                        "name": "Multi-Instrument Quant Regimes",
                        "description": "Index mean-reversion in sideways compression, trend-following when ADX > 25, and momentum breakouts on Bollinger Band expansion.",
                        "rule": "Regime gating dictates strategy activation without style drift."
                    },
                    {
                        "name": "10% Maximum Drawdown Circuit Breaker",
                        "description": "Portfolio automatically freezes new allocations if peak-to-trough drawdown reaches 10%, cutting size by 50% at 2% drawdown.",
                        "rule": "Implemented in agent survival tiers (Normal -> Defensive -> Critical -> Circuit Breaker)."
                    },
                    {
                        "name": "Maker-Checker Adversarial Loop",
                        "description": "An independent validation pass that recalculates all mathematics, verifies source citations, and marks unverified figures as [UNVERIFIED].",
                        "rule": "Every research synthesis is audited before trade execution."
                    },
                    {
                        "name": "Loop Engineering & IC Scoring",
                        "description": "Evaluates signal persistence with Information Coefficient (IC > 0.5 is strong, < 0.3 is noise) and enforces a 5-day signal half-life decay filter.",
                        "rule": "Discard 1-bar blips; only execute on persistent statistical edges."
                    }
                ]
            },
            "day_trading_guruji": {
                "handle": "@daytradingguruji",
                "name": "Hardik Sharma",
                "title": "Intraday Price Action & Retail Reality Check",
                "backtested_results": [
                    {"strategy": "5 EMA Strategy (Subasish Pani)", "timeframe": "5m / 15m", "net_return": "-5.19%", "win_rate": "23.5%", "max_drawdown": "8.7%", "verdict": "FAIL (Choppy Whipsaws)"},
                    {"strategy": "9 & 15 EMA Scalp (The Trade Room)", "timeframe": "5m", "net_return": "Negative", "win_rate": "<30%", "max_drawdown": "11.2%", "verdict": "FAIL (Lagging Moving Average Crossover)"},
                    {"strategy": "Brahmastra Strategy (Pushkar Raj Thakur)", "timeframe": "5m", "net_return": "-0.09%", "win_rate": "41.5%", "max_drawdown": "3.5%", "verdict": "FAIL (Overfitted Multi-Indicator Lag)"},
                    {"strategy": "Liquidity Sweep & Zone Re-Entry (Hardik Sharma)", "timeframe": "5m / 15m", "net_return": "+18.0%", "win_rate": "62.0%", "max_drawdown": "4.0%", "verdict": "PROFITABLE (Institutional Absorption)"}
                ],
                "core_concepts": [
                    {
                        "name": "Institutional Liquidity Sweep Setup",
                        "description": "Wait for price to punch below an established support/demand level by 1-2%, flushing retail stop losses, then take entry only when a candle closes back above the level with surge volume.",
                        "rule": "Entry on close back inside zone. Hard stop under the sweep wick. Minimum 1:2 to 1:3 RR."
                    },
                    {
                        "name": "Central Pivot Range (CPR) Width Filter",
                        "description": "Narrow CPR (width <= 0.35%) flags high directional breakout probability. Wide CPR (>= 0.90%) signals range-bound consolidation day.",
                        "rule": "Trending breakout trades only on narrow CPR; fade extremes on wide CPR."
                    },
                    {
                        "name": "Time-of-Day Discipline",
                        "description": "Avoid placing mechanical entries in the first 30 minutes (9:15 - 9:45 AM) to let institutional opening balance form.",
                        "rule": "High-probability entries occur post 9:45 AM and 10:45 AM."
                    }
                ]
            },
            "minervini": {
                "handle": "@markminervini",
                "name": "Mark Minervini",
                "title": "SEPA Volatility Contraction Pattern (VCP)",
                "core_concepts": [
                    {
                        "name": "Trend Template Filter",
                        "description": "Stock price must be above 50 EMA, 150 SMA, and 200 SMA, with all three moving averages in ascending order.",
                        "rule": "No entry unless Trend Template is fully verified."
                    },
                    {
                        "name": "Progressive Volatility Contraction (VCP)",
                        "description": "Each successive price correction in the base must be 30-50% shallower than the prior one (e.g. 20% -> 10% -> 4%).",
                        "rule": "Volume must dry up dramatically during final contraction before breakout."
                    }
                ]
            },
            "turtle_dennis": {
                "handle": "Turtle Traders",
                "name": "Richard Dennis & Ed Seykota",
                "title": "Trend Following & Donchian Breakouts",
                "core_concepts": [
                    {
                        "name": "20-Day Donchian Breakout",
                        "description": "Enter on a breakout of the 20-day high with ADX confirming trend strength (> 20).",
                        "rule": "Stop loss strictly set at 2.0x ATR below entry price."
                    },
                    {
                        "name": "Fixed Volatility Unit Sizing",
                        "description": "Position size is computed so that 2 ATRs equals exactly 1.0% of portfolio equity.",
                        "rule": "Scale up to 4 units at every 0.5 ATR favorable move."
                    }
                ]
            },
            "frvp_booming_bulls": {
                "handle": "@algotrader.sahil / Booming Bulls",
                "name": "Anish Singh Thakur (Algorithmic FRVP)",
                "title": "Fixed Range Volume Profile VAH/VAL Strategy",
                "core_concepts": [
                    {
                        "name": "Value Area Boundaries (70% Volume)",
                        "description": "Value Area Low (VAL) and Value Area High (VAH) define institutional boundaries.",
                        "rule": "Buy at VAL discount rejection; short at VAH premium rejection; target POC then opposite extreme."
                    },
                    {
                        "name": "Volume-Confirmed Breakout Retest",
                        "description": "A breakout past VAH with 2x average volume converts VAH into rock-solid support on retest.",
                        "rule": "Enter on retest of VAH targeting equal range extension."
                    }
                ]
            },
            "pr_sundar": {
                "handle": "@PRSundar64",
                "name": "PR Sundar",
                "title": "Non-Directional Options Selling & VIX Regimes",
                "core_concepts": [
                    {
                        "name": "VIX Regime Filter",
                        "description": "India VIX determines whether to sell options and which delta strikes to choose.",
                        "rule": "VIX 13-18 is optimal for 0.20-0.25 delta strangles; reduce size if VIX > 18; avoid if VIX < 13."
                    }
                ]
            },
            "alok_jain": {
                "handle": "@WeekendInvestng",
                "name": "Alok Jain (Weekend Investing)",
                "title": "12-1 Month Momentum Rotation",
                "core_concepts": [
                    {
                        "name": "12-1 Momentum Formula",
                        "description": "Rank Nifty 500 stocks by 12-month return skipping the most recent month to avoid mean reversion.",
                        "rule": "Hold top 20 ranked stocks with weekly rebalancing."
                    }
                ]
            },
            "notebooklm_pipeline": {
                "title": "NotebookLM Strategy Extraction & Backtest Pipeline",
                "steps": [
                    "Step 1: Paste any YouTube URL or research PDF into Google NotebookLM (notebooklm.google.com).",
                    "Step 2: Prompt NotebookLM: 'Extract the complete trading rules from the above source: indicators, timeframes, long/short entry triggers, stop-loss calculation, and profit targets.'",
                    "Step 3: Copy extracted rules and prompt LLM: 'Convert the following trading rules into a modular Python strategy / TradingView Pine Script with walk-forward validation and slippage.'",
                    "Step 4: Feed generated code directly into our Agent Strategy Backtester (/api/backtest) or TradingView Pine Editor."
                ],
                "notebooklm_prompt": "Act as a senior quantitative researcher. Extract all trading rules from this source: 1. Asset class and recommended timeframe. 2. Indicator parameters (periods, types). 3. Exact Long entry conditions. 4. Exact Short entry conditions. 5. Hard stop loss level. 6. Profit targets and risk-to-reward ratio. 7. Invalidation / exit rules. Format as a numbered rulebook.",
                "codegen_prompt": "You are a Pine Script v5 and Python quantitative developer. Convert these exact trading rules into an error-free TradingView strategy and Python backtest logic with 1% ATR position sizing and 0.1% slippage per leg."
            }
        }
    }

@app.post("/api/backtest")
def run_backtest_endpoint(req: BacktestRequest):
    try:
        return backtest_strategy(
            symbol=req.symbol,
            strategy_name=req.strategy,
            period=req.period,
            initial_capital=req.initial_capital
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/backtest/optimize")
def optimize_backtest_endpoint(req: OptimizeRequest):
    try:
        return run_parameter_sweep(
            symbol=req.symbol,
            period=req.period,
            initial_capital=req.initial_capital
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/notify/telegram")
def notify_telegram(req: TelegramAlertRequest):
    return send_telegram_trade_alert(req.trade_data)

@app.get("/api/portfolio")
def get_portfolio():
    return angel_client.get_portfolio_summary()

@app.post("/api/order")
def place_order(order: OrderRequest):
    tier_info = agent_heartbeat.get_status().get("survival_tier", {})
    if order.transaction_type == "BUY" and not tier_info.get("trading_allowed", True):
        raise HTTPException(
            status_code=403, 
            detail=f"Order blocked by Survival Tier [{tier_info.get('tier')}]: {tier_info.get('description')}"
        )
        
    portfolio = angel_client.get_portfolio_summary()
    equity = portfolio.get("net_liquidation_value", 125000.0)
    
    order_price = order.price or 0.0
    if order_price <= 0:
        try:
            q = get_stock_quote(order.symbol)
            order_price = float(q.get("price", 0.0))
        except Exception:
            order_price = 100.0

    if order.transaction_type == "BUY" and order.stop_loss is not None:
        val_res = validate_order_against_constitution(
            symbol=order.symbol,
            price=order_price,
            stop_loss=order.stop_loss,
            target_price=order.target_price,
            quantity=order.quantity,
            portfolio_equity=equity
        )
        if not val_res["allowed"]:
            raise HTTPException(
                status_code=400,
                detail={"message": "Order violates Trading Constitution", "violations": val_res["violations"]}
            )

    res = angel_client.place_order(
        symbol=order.symbol,
        quantity=order.quantity,
        transaction_type=order.transaction_type,
        order_type=order.order_type,
        price=order_price
    )
    
    memory_journal.record_entry(
        category="EXECUTION",
        title=f"Order Executed: {order.transaction_type} {order.quantity}x {order.symbol}",
        content=f"Executed at INR {order_price:.2f}. Status: {res.get('status', 'OK')}.",
        metadata={"symbol": order.symbol, "qty": order.quantity, "type": order.transaction_type, "price": order_price}
    )
    return res

@app.post("/api/webhook/trade")
@app.post("/api/webhook/tradingview")
def receive_webhook_trade(alert: WebhookTradeAlert):
    raw_sym = alert.ticker or alert.symbol or ""
    if not raw_sym:
        raise HTTPException(status_code=400, detail="Missing symbol or ticker in webhook payload")
    
    clean_sym = normalize_indian_symbol(raw_sym)
    action = alert.action.upper()
    if action not in ["BUY", "SELL"]:
        action = "BUY"
        
    portfolio = angel_client.get_portfolio_summary()
    equity = float(portfolio.get("total_portfolio_value", portfolio.get("net_liquidation_value", 50000.0)))
    cash = float(portfolio.get("available_cash", 50000.0))
    
    ref_price = alert.price or 0.0
    if ref_price <= 0:
        try:
            q = get_stock_quote(clean_sym)
            ref_price = float(q.get("price", 0.0))
        except Exception:
            ref_price = 100.0

    sl = alert.stop_loss
    tgt = alert.target_price or alert.target
    qty = alert.quantity
    
    if not qty or qty <= 0:
        try:
            from src.engine.position_sizer import calculate_volatility_parity_position_size
            from src.analysis.technical import calculate_atr
            df = get_historical_bars(clean_sym, period="1mo", interval="1d")
            atr_val = float(calculate_atr(df, 14).iloc[-1])
            sizing = calculate_volatility_parity_position_size(
                stock_price=ref_price,
                atr_14=atr_val,
                account_equity=equity,
                available_cash=cash,
                risk_pct=0.01
            )
            qty = max(1, sizing.get("quantity", 1))
            if not sl:
                sl = sizing.get("stop_loss")
            if not tgt:
                tgt = sizing.get("target")
        except Exception:
            qty = 1

    if action == "BUY" and sl is not None:
        val = validate_order_against_constitution(
            symbol=clean_sym,
            price=ref_price,
            stop_loss=sl,
            target_price=tgt,
            quantity=qty,
            portfolio_equity=equity
        )
        if not val.get("allowed", True):
            violations = val.get("violations", [])
            msg = f"⚠️ *WEBHOOK ALERT BLOCKED BY CONSTITUTION*\nSymbol: `{clean_sym}`\nReason: {', '.join(violations)}"
            send_telegram_text(msg)
            return {
                "status": "BLOCKED",
                "symbol": clean_sym,
                "violations": violations
            }

    order_res = angel_client.place_order(
        symbol=clean_sym,
        quantity=qty,
        transaction_type=action,
        order_type="MARKET",
        price=ref_price
    )
    
    strat = alert.strategy or "Webhook Signal"
    is_locked = angel_client.is_trade_locked()
    paper_tag = "[PAPER SIMULATION] " if is_locked else "[LIVE] "
    sl_str = f"₹{sl:.2f}" if sl else "N/A"
    tgt_str = f"₹{tgt:.2f}" if tgt else "N/A"
    telegram_msg = (
        f"🎯 *{paper_tag}WEBHOOK SIGNAL*\n"
        f"Strategy: *{strat}* ({alert.timeframe})\n"
        f"Action: *{action} {qty}x {clean_sym}*\n"
        f"Price: ₹{ref_price:.2f} | SL: {sl_str} | Tgt: {tgt_str}\n"
        f"Order Result: {order_res.get('message', 'Processed')}"
    )
    send_telegram_text(telegram_msg)
    
    memory_journal.record_entry(
        category="WEBHOOK_SIGNAL",
        title=f"Webhook Alert: {action} {qty}x {clean_sym} [{strat}]",
        content=f"Price: ₹{ref_price:.2f}, SL: {sl_str}, Target: {tgt_str}. Result: {order_res.get('status')}",
        metadata={"symbol": clean_sym, "qty": qty, "price": ref_price, "strategy": strat, "result": order_res}
    )
    
    return {
        "status": "SUCCESS",
        "symbol": clean_sym,
        "action": action,
        "quantity": qty,
        "price": ref_price,
        "stop_loss": sl,
        "target": tgt,
        "strategy": strat,
        "execution": order_res
    }

class AlgoOrderRequest(BaseModel):
    symbol: str
    quantity: int
    transaction_type: str = "BUY"
    duration_minutes: int = 60
    slice_interval_minutes: int = 5
    max_slippage_pct: float = 0.50

@app.get("/api/analysis/order-flow/{symbol}")
def get_order_flow_endpoint(symbol: str):
    try:
        df = get_historical_bars(symbol, period="6mo", interval="1d")
        return {"symbol": normalize_indian_symbol(symbol), "order_flow": analyze_order_flow(df)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/analysis/volatility/{symbol}")
def get_volatility_endpoint(symbol: str):
    try:
        df = get_historical_bars(symbol, period="6mo", interval="1d")
        return {"symbol": normalize_indian_symbol(symbol), "volatility": analyze_volatility_regime(df)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/order/twap")
def execute_twap_endpoint(req: AlgoOrderRequest):
    try:
        q = get_stock_quote(req.symbol)
        ref_price = float(q.get("price", 100.0))
        slices = execution_engine.generate_twap_schedule(
            total_quantity=req.quantity,
            duration_minutes=req.duration_minutes,
            slice_interval_minutes=req.slice_interval_minutes
        )
        res = execution_engine.simulate_execution(
            symbol=req.symbol,
            transaction_type=req.transaction_type,
            slices=slices,
            reference_price=ref_price,
            max_slippage_pct=req.max_slippage_pct
        )
        memory_journal.record_entry(
            category="ALGO_EXECUTION",
            title=f"TWAP Slicing: {req.transaction_type} {req.quantity}x {req.symbol}",
            content=f"Filled: {res.get('total_filled_qty')}/{req.quantity} @ ₹{res.get('average_execution_price')}. Slippage: {res.get('slippage_basis_points')} bps.",
            metadata=res
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/order/vwap")
def execute_vwap_endpoint(req: AlgoOrderRequest):
    try:
        q = get_stock_quote(req.symbol)
        ref_price = float(q.get("price", 100.0))
        num_sl = max(4, min(12, req.duration_minutes // 15))
        slices = execution_engine.generate_vwap_schedule(
            total_quantity=req.quantity,
            num_slices=num_sl
        )
        res = execution_engine.simulate_execution(
            symbol=req.symbol,
            transaction_type=req.transaction_type,
            slices=slices,
            reference_price=ref_price,
            max_slippage_pct=req.max_slippage_pct
        )
        memory_journal.record_entry(
            category="ALGO_EXECUTION",
            title=f"VWAP Slicing: {req.transaction_type} {req.quantity}x {req.symbol}",
            content=f"Filled: {res.get('total_filled_qty')}/{req.quantity} @ ₹{res.get('average_execution_price')}. Slippage: {res.get('slippage_basis_points')} bps.",
            metadata=res
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/multi-asset/scan")
def multi_asset_scan_endpoint():
    try:
        portfolio = angel_client.get_portfolio_summary()
        tot_val = float(portfolio.get("total_portfolio_value", 125000.0))
        cash = float(portfolio.get("available_cash", 125000.0))
        hb = agent_heartbeat.get_status()
        tier_mult = float(hb.get("survival_tier", {}).get("position_size_multiplier", 1.0))
        return scan_multi_asset_opportunities(
            account_equity=tot_val,
            available_cash=cash,
            tier_multiplier=tier_mult
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/briefing/morning")
def morning_briefing_endpoint(dispatch: bool = False):
    try:
        if dispatch:
            return send_morning_briefing()
        return {"briefing": build_morning_briefing()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/briefing/evening")
def evening_report_endpoint(dispatch: bool = False):
    try:
        if dispatch:
            return send_evening_report()
        return {"report": build_evening_report()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/nifty500")
def nifty500_screener_endpoint(limit: int = 50, sector: Optional[str] = None):
    try:
        portfolio = angel_client.get_portfolio_summary()
        tot_val = float(portfolio.get("total_portfolio_value", 125000.0))
        cash = float(portfolio.get("available_cash", 125000.0))
        hb = agent_heartbeat.get_status()
        tier_mult = float(hb.get("survival_tier", {}).get("position_size_multiplier", 1.0))
        return scan_nifty500_breakouts(
            limit_stocks=min(limit, 100),
            sector_filter=sector,
            account_equity=tot_val,
            available_cash=cash,
            tier_multiplier=tier_mult
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/options/vix-regime")
def get_vix_regime_endpoint(vix: Optional[float] = None):
    try:
        if vix is None or vix <= 0:
            macro = _get_macro()
            vix = float(macro.get("INDIA_VIX", {}).get("value", 14.5))
        return calculate_india_vix_regime(vix)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/vcp")
def get_vcp_screener_endpoint(limit: int = 10):
    try:
        return scan_vcp_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/momentum-rotation")
def get_momentum_rotation_endpoint(limit: int = 20):
    try:
        return scan_momentum_rotation(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/donchian")
def get_donchian_breakouts_endpoint(period: int = 20, limit: int = 10):
    try:
        return scan_donchian_breakouts(period=period, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/frvp/{symbol}")
def get_frvp_endpoint(symbol: str, lookback: int = 30):
    try:
        df = get_historical_bars(symbol, period="6mo", interval="1d")
        res = get_frvp_analysis(df, lookback_bars=lookback)
        res["symbol"] = normalize_indian_symbol(symbol)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/analysis/ict/{symbol}")
def get_ict_order_blocks_endpoint(symbol: str):
    try:
        df = get_historical_bars(symbol, period="6mo", interval="1d")
        obs = detect_ict_order_blocks(df)
        obs["symbol"] = normalize_indian_symbol(symbol)
        obs["killzone_status"] = get_ict_killzone_status()
        return obs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/ict/killzones")
def get_killzones_endpoint():
    return get_ict_killzone_status()

@app.get("/api/portfolio/allocation-audit")
def get_portfolio_allocation_audit():
    try:
        from src.engine.portfolio_recycler import portfolio_recycler
        summary = angel_client.get_portfolio_summary()
        return portfolio_recycler.audit_portfolio_allocation(summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/recycling-plan")
def get_portfolio_recycling_plan(required_cash: float = 14200.0, target_symbol: str = "BHEL"):
    try:
        from src.engine.portfolio_recycler import portfolio_recycler
        summary = angel_client.get_portfolio_summary()
        return portfolio_recycler.generate_capital_recycling_plan(
            portfolio_summary=summary,
            required_cash=required_cash,
            target_symbol=target_symbol
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research/adversarial-audit")
def post_adversarial_audit(req: AdversarialAuditRequest):
    try:
        symbol = normalize_indian_symbol(req.symbol)
        price = req.price
        technicals = req.technicals
        fundamentals = req.fundamentals
        news_headlines = req.news_headlines or []

        if price is None or price <= 0:
            quote = get_stock_quote(symbol)
            price = quote.get("price", 0.0)

        if technicals is None:
            df = get_historical_bars(symbol, period="6mo", interval="1d")
            technicals = analyze_technical_indicators(df)

        if fundamentals is None:
            raw_fund = get_company_fundamentals(symbol)
            fundamentals = evaluate_fundamentals(raw_fund)

        if not news_headlines:
            from src.data.news_data import get_indian_stock_news
            raw_news = get_indian_stock_news(symbol, limit=4)
            news_headlines = [n.get("title", "") for n in raw_news if n.get("title")]

        levels = technicals.get("levels", {})
        atr = levels.get("atr", price * 0.025)
        stop_loss = req.stop_loss if req.stop_loss and req.stop_loss > 0 else round(price - (1.5 * atr), 2)
        target_price = req.target_price if req.target_price and req.target_price > 0 else round(price + (2.5 * atr), 2)

        audit_res = adversarial_council.audit_trade_proposal(
            symbol=symbol,
            price=price,
            stop_loss=stop_loss,
            target_price=target_price,
            technicals=technicals,
            fundamentals=fundamentals,
            news_headlines=news_headlines
        )
        return audit_res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/vault/list")
def get_vault_list(q: Optional[str] = None):
    try:
        if q:
            return research_vault.search_vault(q)
        return research_vault.list_dossiers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vault/{symbol}")
def get_vault_dossier(symbol: str, auto_generate: bool = True):
    try:
        norm_sym = normalize_indian_symbol(symbol)
        dossier = research_vault.get_dossier(norm_sym)
        if dossier:
            return dossier
        
        if not auto_generate:
            raise HTTPException(status_code=404, detail=f"Dossier for {norm_sym} not found in research vault.")

        quote = get_stock_quote(norm_sym)
        df = get_historical_bars(norm_sym, period="6mo", interval="1d")
        technicals = analyze_technical_indicators(df)
        raw_fund = get_company_fundamentals(norm_sym)
        fundamentals = evaluate_fundamentals(raw_fund)
        from src.data.news_data import get_indian_stock_news
        news = get_indian_stock_news(norm_sym, limit=4)
        
        research = run_multi_agent_research(quote, technicals, fundamentals, news)
        research_vault.save_dossier(norm_sym, research)
        return research_vault.get_dossier(norm_sym)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vault/{symbol}/markdown")
def get_vault_dossier_markdown(symbol: str):
    try:
        norm_sym = normalize_indian_symbol(symbol)
        md = research_vault.get_dossier_markdown(norm_sym)
        if not md:
            dossier = research_vault.get_dossier(norm_sym)
            if not dossier:
                raise HTTPException(status_code=404, detail=f"Dossier for {norm_sym} not found.")
            md = research_vault._render_markdown_dossier(dossier)
        return {"symbol": norm_sym, "markdown": md}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vault/save")
def save_vault_dossier_endpoint(req: VaultSaveRequest):
    try:
        norm_sym = normalize_indian_symbol(req.symbol)
        if req.research:
            saved = research_vault.save_dossier(norm_sym, req.research, extra_metadata=req.extra_metadata)
        else:
            quote = get_stock_quote(norm_sym)
            df = get_historical_bars(norm_sym, period="6mo", interval="1d")
            technicals = analyze_technical_indicators(df)
            raw_fund = get_company_fundamentals(norm_sym)
            fundamentals = evaluate_fundamentals(raw_fund)
            from src.data.news_data import get_indian_stock_news
            news = get_indian_stock_news(norm_sym, limit=4)
            research = run_multi_agent_research(quote, technicals, fundamentals, news)
            saved = research_vault.save_dossier(norm_sym, research, extra_metadata=req.extra_metadata)
        return saved
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/analysis/friction")
def get_statutory_friction(
    symbol: str = "BHEL",
    price: float = 431.0,
    quantity: int = 33,
    action: str = "BUY",
    trade_type: str = "DELIVERY"
):
    try:
        from src.broker.execution_microstructure import calculate_statutory_friction
        return calculate_statutory_friction(
            symbol=normalize_indian_symbol(symbol),
            action=action,
            price=price,
            quantity=quantity,
            trade_type=trade_type
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/broker/order-book")
def get_broker_order_book():
    try:
        return angel_client.get_order_book()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/verify-order/{order_id}")
def verify_broker_order(order_id: str):
    try:
        return angel_client.verify_order_settlement(order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/5ema/{symbol}")
def get_5ema_analysis_endpoint(symbol: str, period: str = "1mo", interval: str = "1d"):
    try:
        norm_sym = normalize_indian_symbol(symbol)
        df = get_historical_bars(norm_sym, period=period, interval=interval)
        res = calculate_5ema_setup(df)
        res["symbol"] = norm_sym
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/screener/5ema")
def get_5ema_screener_endpoint(limit: int = 10, period: str = "1mo", interval: str = "1d"):
    try:
        return scan_5ema_setups(limit=limit, period=period, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/pbd/{symbol}")
def get_pbd_analysis_endpoint(symbol: str, period: str = "3mo", interval: str = "1d", equity: float = 100000.0):
    try:
        norm_sym = normalize_indian_symbol(symbol)
        df = get_historical_bars(norm_sym, period=period, interval=interval)
        res = evaluate_patrick_nill_setup(df, account_equity=equity)
        res["symbol"] = norm_sym
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/screener/pbd")
def get_pbd_screener_endpoint(limit: int = 10, period: str = "3mo", interval: str = "1d"):
    try:
        portfolio = angel_client.get_portfolio_summary()
        tot_val = float(portfolio.get("total_portfolio_value", 100000.0))
        return scan_pbd_setups(limit=limit, period=period, interval=interval, account_equity=tot_val)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/screener/5pillar")
def get_5pillar_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_king_5pillar_candidates
        return scan_king_5pillar_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/supply-demand")
def get_supply_demand_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_supply_demand_candidates
        return scan_supply_demand_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/dark-pool")
def get_dark_pool_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_dark_pool_candidates
        return scan_dark_pool_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/nifty-pivots")
def get_nifty_pivots_screener_endpoint():
    try:
        from src.analysis.screener import scan_nifty_pivot_candidates
        return scan_nifty_pivot_candidates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/social-all/{symbol}")
def get_social_all_analysis_endpoint(symbol: str, period: str = "6mo", interval: str = "1d"):
    try:
        norm_sym = normalize_indian_symbol(symbol)
        df = get_historical_bars(norm_sym, period=period, interval=interval)
        from src.analysis.social_strategies import (
            calculate_king_research_5pillar,
            calculate_trading_geek_snd,
            calculate_dark_pool_absorption,
            calculate_mandeep_pivot_9ema,
            calculate_mamba_fx_setup,
            calculate_stock_burner_9_20,
            calculate_tradeiq_9_21_ema
        )
        return {
            "symbol": norm_sym,
            "king_5pillar": calculate_king_research_5pillar(df),
            "trading_geek_snd": calculate_trading_geek_snd(df),
            "dark_pool": calculate_dark_pool_absorption(df),
            "mandeep_pivot": calculate_mandeep_pivot_9ema(df),
            "mamba_fx": calculate_mamba_fx_setup(df),
            "stock_burner": calculate_stock_burner_9_20(df),
            "tradeiq_ema": calculate_tradeiq_9_21_ema(df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/screener/cpr-regime")
def get_cpr_regime_screener_endpoint():
    try:
        from src.analysis.screener import scan_cpr_regimes
        return scan_cpr_regimes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/inside-bar")
def get_inside_bar_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_inside_bar_breakouts
        return scan_inside_bar_breakouts(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/multibaggers")
def get_multibaggers_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_multibagger_candidates
        return scan_multibagger_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/rsi-divergence")
def get_rsi_divergence_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_rsi_divergence_candidates
        return scan_rsi_divergence_candidates(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/screener/connors-rsi")
def get_connors_rsi_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_connors_rsi2_dips
        return scan_connors_rsi2_dips(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/camarilla")
def get_camarilla_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_camarilla_breakouts
        return scan_camarilla_breakouts(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/vip")
def get_vip_screener_endpoint(limit: int = 15):
    try:
        from src.analysis.screener import scan_kunal_saraogi_vip
        return scan_kunal_saraogi_vip(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
