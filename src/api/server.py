import socket
import os
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
from src.notifications.telegram import send_telegram_trade_alert
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_heartbeat.start()
    asyncio.create_task(agent_heartbeat.execute_cycle())
    yield
    agent_heartbeat.stop()

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
        "market_session": hb.get("market_session", "UNKNOWN")
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

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
