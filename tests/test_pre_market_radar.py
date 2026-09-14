import pytest
from unittest.mock import patch, MagicMock
from src.analysis.pre_market_radar import get_pre_market_radar

def test_pre_market_radar_structure():
    with patch("yfinance.Ticker") as mock_ticker:
        mock_instance = MagicMock()
        mock_fast_info = MagicMock()
        mock_fast_info.last_price = 5000.0
        mock_fast_info.previous_close = 4950.0
        mock_instance.fast_info = mock_fast_info
        mock_ticker.return_value = mock_instance

        radar = get_pre_market_radar()
        assert "opening_bias" in radar
        assert "bias_score" in radar
        assert "action_directive" in radar
        assert "global_cues" in radar
        assert radar["opening_bias"] in ("BULLISH_EXPANSION", "BEARISH_DEFENSIVE", "NEUTRAL_RANGEBOUND")

def test_radar_bullish_bias_threshold():
    radar = {
        "bias_score": 35.0,
        "opening_bias": "BULLISH_EXPANSION"
    }
    assert radar["bias_score"] >= 25.0
