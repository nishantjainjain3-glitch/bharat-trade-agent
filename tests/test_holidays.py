import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.data.holidays import is_nse_holiday, get_next_trading_day, NSE_TRADING_HOLIDAYS
from src.engine.heartbeat import AutonomousHeartbeat
from src.notifications.daily_briefings import build_holiday_briefing

IST = timezone(timedelta(hours=5, minutes=30))


def test_today_ganesh_chaturthi_detected():
    """Verify that September 14, 2026 is recognized as Ganesh Chaturthi."""
    is_hol, hol_name = is_nse_holiday("2026-09-14")
    assert is_hol is True
    assert hol_name == "Ganesh Chaturthi"

    # Also test date object
    is_hol, hol_name = is_nse_holiday(date(2026, 9, 14))
    assert is_hol is True
    assert hol_name == "Ganesh Chaturthi"


def test_regular_trading_day_not_holiday():
    """Verify that a normal trading day is not marked as a holiday."""
    is_hol, hol_name = is_nse_holiday("2026-09-15")
    assert is_hol is False
    assert hol_name is None


def test_other_holidays_2026():
    """Verify key 2026 national and financial holidays."""
    assert is_nse_holiday("2026-01-26")[0] is True  # Republic Day
    assert is_nse_holiday("2026-08-15")[0] is True  # Independence Day
    assert is_nse_holiday("2026-10-02")[0] is True  # Mahatma Gandhi Jayanti
    assert is_nse_holiday("2026-11-10")[0] is True  # Diwali-Balipratipada


def test_next_trading_day_from_holiday():
    """From Monday holiday 2026-09-14, next trading day should be Tuesday 2026-09-15."""
    next_day = get_next_trading_day("2026-09-14")
    assert next_day == date(2026, 9, 15)


def test_next_trading_day_skips_weekend():
    """From Friday 2026-09-18, next trading day should be Monday 2026-09-21."""
    next_day = get_next_trading_day("2026-09-18")
    assert next_day == date(2026, 9, 21)


def test_heartbeat_market_session_on_holiday():
    """Verify that heartbeat reports HOLIDAY_CLOSED on a holiday."""
    hb = AutonomousHeartbeat()
    with patch("src.engine.heartbeat.is_nse_holiday") as mock_hol:
        mock_hol.return_value = (True, "Ganesh Chaturthi")
        session = hb.get_market_session()
        assert session == "HOLIDAY_CLOSED (Ganesh Chaturthi)"


def test_build_holiday_briefing_content():
    """Verify that the holiday briefing contains relevant closure details."""
    briefing = build_holiday_briefing("Ganesh Chaturthi")
    assert "MARKET HOLIDAY NOTICE" in briefing
    assert "Ganesh Chaturthi" in briefing
    assert "Standby Mode" in briefing


def test_heartbeat_fallback_to_news_closure():
    """Verify that heartbeat catches closures from live macro news if calendar is bypassed."""
    hb = AutonomousHeartbeat()
    with patch("src.engine.heartbeat.is_nse_holiday", return_value=(False, None)):
        with patch("src.data.news_data.get_macro_market_news") as mock_news:
            mock_news.return_value = {
                "market_closure_indicated": True,
                "detected_reason": "Emergency Halt"
            }
            session = hb.get_market_session()
            assert session == "HOLIDAY_CLOSED (Emergency Halt)"
