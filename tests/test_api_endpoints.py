import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)

def test_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"
    assert r1.json()["service"] == "bharat-trade-agent"

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"

def test_status_endpoint():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "angel_one_mode" in data
    assert "market_session" in data

def test_webhook_trade_missing_symbol():
    r = client.post("/api/webhook/trade", json={"action": "BUY"})
    assert r.status_code == 400
    assert "Missing symbol" in r.json()["detail"]

@patch("src.api.server.send_telegram_text")
@patch("src.api.server.angel_client")
def test_webhook_trade_success(mock_angel, mock_tg):
    mock_angel.get_portfolio_summary.return_value = {
        "total_portfolio_value": 50000.0,
        "available_cash": 25000.0
    }
    mock_angel.is_trade_locked.return_value = True
    mock_angel.place_order.return_value = {
        "status": True,
        "mode": "SIMULATION",
        "order_id": "SIM-TEST1234",
        "message": "Paper simulated BUY 10 shares of RELIANCE at INR 1280.00."
    }
    mock_tg.return_value = {"status": True}

    payload = {
        "ticker": "RELIANCE",
        "action": "BUY",
        "price": 1280.0,
        "quantity": 10,
        "stop_loss": 1250.0,
        "target": 1340.0,
        "strategy": "TradingView Supertrend",
        "timeframe": "15m"
    }

    r = client.post("/api/webhook/trade", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "SUCCESS"
    assert res["symbol"] == "RELIANCE.NS"
    assert res["quantity"] == 10
    assert res["execution"]["status"] is True
    assert mock_tg.called

    r2 = client.post("/api/webhook/tradingview", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "SUCCESS"
