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
from typing import Optional, Dict, Any

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
from src.data.news_data import get_indian_stock_news
from src.analysis.screener import get_top_buy_recommendations, get_preset_screener_recommendations
from src.analysis.sector_rotation import get_nifty_sector_rotation
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
        research = run_multi_agent_research(quote, technicals, fundamentals, news)
        personas = evaluate_all_investor_personas(quote, fundamentals)
        financials = get_corporate_financial_history(req.symbol)
        hb_status = agent_heartbeat.get_status()
        tier_name = hb_status.get("survival_tier", {}).get("tier", "NORMAL")
        battle_plan = generate_tactical_battle_plan(quote, technicals, fundamentals, research, survival_tier=tier_name)
        
        return {
            "quote": quote,
            "technicals": technicals,
            "fundamentals": fundamentals,
            "news": news,
            "research": research,
            "personas": personas,
            "financials": financials,
            "battle_plan": battle_plan
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
