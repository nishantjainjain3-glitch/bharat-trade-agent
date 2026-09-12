import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api.server import app
from src.analysis.screener import get_high_momentum_breakouts

client = TestClient(app)

def test_get_high_momentum_breakouts_structure():
    with patch("src.broker.angel_one.angel_client.get_market_gainers") as mock_gainers, \
         patch("src.broker.angel_one.angel_client.get_batch_quotes") as mock_quotes:
        
        mock_gainers.return_value = [
            {"tradingSymbol": "PINELABS24SEPFUT", "percentChange": 14.5}
        ]
        mock_quotes.return_value = [
            {
                "tradingSymbol": "PINELABS-EQ",
                "ltp": 202.0,
                "percentChange": 14.5,
                "tradeVolume": 25000000,
                "high": 206.0,
                "low": 170.0
            },
            {
                "tradingSymbol": "INDUSTOWER-EQ",
                "ltp": 388.0,
                "percentChange": 4.2,
                "tradeVolume": 8000000,
                "high": 391.0,
                "low": 372.0
            }
        ]

        results = get_high_momentum_breakouts(limit=5, target_pct=5.5, stop_pct=2.5)
        assert len(results) >= 2
        
        first = results[0]
        assert first["symbol"] == "PINELABS"
        assert first["day_change_pct"] == 14.5
        assert first["setup_type"] == "VOLUME_SPIKE_BREAKOUT"
        assert first["event_type"] == "TRIGGERED"
        assert first["conviction"] == 10
        assert first["target_return_pct"] == 5.5
        assert first["stop_loss_pct"] == 2.5
        assert first["target_price"] > first["price"]
        assert first["stop_loss"] < first["price"]
        assert "catalyst_summary" in first

def test_momentum_breakouts_api_endpoint():
    with patch("src.api.server.get_high_momentum_breakouts") as mock_fn:
        mock_fn.return_value = [
            {
                "symbol": "PINELABS",
                "name": "PINELABS",
                "price": 202.0,
                "day_change_pct": 14.5,
                "volume": 25000000,
                "rvol": 5.0,
                "day_high": 206.0,
                "day_low": 170.0,
                "target_price": 213.11,
                "target_return_pct": 5.5,
                "stop_loss": 196.95,
                "stop_loss_pct": 2.5,
                "risk_reward_ratio": 2.2,
                "expected_hold": "Same day to 2 days",
                "conviction": 10,
                "setup_type": "VOLUME_SPIKE_BREAKOUT",
                "event_type": "TRIGGERED",
                "strategy": "High-Volume Real-Time Breakout",
                "catalyst_summary": "Massive volume expansion with explosive price breakout."
            }
        ]

        response = client.get("/api/screener/momentum-breakouts?limit=5&target_pct=5.5&stop_pct=2.5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "PINELABS"
        assert data[0]["setup_type"] == "VOLUME_SPIKE_BREAKOUT"
        assert data[0]["target_return_pct"] == 5.5
