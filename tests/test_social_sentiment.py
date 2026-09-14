import pytest
from unittest.mock import patch, MagicMock
from src.data.social_sentiment import (
    _score_text,
    calculate_social_velocity,
    get_stock_social_sentiment,
    get_watchlist_social_sentiment
)

def test_score_text_bullish_and_bearish():
    bull_score = _score_text("Massive breakout and rally with huge contract order")
    assert bull_score > 0

    bear_score = _score_text("Stock in breakdown after SEBI investigation and penalty notice")
    assert bear_score < 0

    neutral_score = _score_text("Company will hold AGM on Friday")
    assert neutral_score == 0

def test_calculate_social_velocity_empty():
    res = calculate_social_velocity([])
    assert res["sentiment_score"] == 0.0
    assert res["sentiment_label"] == "NEUTRAL"
    assert res["total_mentions"] == 0
    assert res["velocity_spike"] is False

def test_calculate_social_velocity_bullish():
    posts = [
        {"title": "BHEL targets fresh high on contract surge", "snippet": "Strong order book expansion"},
        {"title": "Breakout confirmed on BHEL with FII buying", "snippet": "Target raised"},
        {"title": "Accumulate on dips", "snippet": "Support holding"}
    ]
    res = calculate_social_velocity(posts)
    assert res["sentiment_score"] > 0
    assert res["sentiment_label"] == "BULLISH"
    assert res["total_mentions"] == 3

def test_calculate_social_velocity_surge():
    # 7 posts with strong bearish sentiment should trigger velocity_spike
    posts = [
        {"title": f"Panic dump breakdown {i}", "snippet": "SEBI probe crash"}
        for i in range(7)
    ]
    res = calculate_social_velocity(posts)
    assert res["sentiment_score"] < -25.0
    assert res["sentiment_label"] == "BEARISH"
    assert res["velocity_spike"] is True
    assert res["velocity_status"] == "ACCELERATING_BEARISH"

@patch("src.data.social_sentiment.fetch_twitter_cli_posts")
@patch("src.data.social_sentiment.fetch_tavily_social_posts")
@patch("src.data.social_sentiment.fetch_reddit_trading_posts")
def test_get_stock_social_sentiment_mocked(mock_reddit, mock_tavily, mock_twitter):
    mock_twitter.return_value = [{"title": "Twitter breakout", "url": "", "source": "x_twitter_cli"}]
    mock_tavily.return_value = [{"title": "Tavily news order win", "snippet": "", "url": "", "source": "tavily"}]
    mock_reddit.return_value = [{"title": "Reddit IndianStreetBets buy", "url": "", "source": "reddit"}]

    res = get_stock_social_sentiment("BHEL.NS")
    assert res["symbol"] == "BHEL.NS"
    assert len(res["sources_used"]) == 3
    assert res["metrics"]["total_mentions"] == 3
    assert "timestamp_ist" in res

def test_get_watchlist_social_sentiment_batch():
    with patch("src.data.social_sentiment.get_stock_social_sentiment") as mock_get:
        mock_get.return_value = {
            "symbol": "TEST.NS",
            "metrics": {"sentiment_score": 50.0, "sentiment_label": "BULLISH", "velocity_spike": False, "total_mentions": 5},
            "sources_used": ["tavily"],
            "sample_posts": []
        }
        res = get_watchlist_social_sentiment(["BHEL.NS", "CUB.NS"])
        assert res["analyzed_count"] == 2
        assert "BHEL.NS" in res["watchlist_sentiment"]
        assert "CUB.NS" in res["watchlist_sentiment"]
