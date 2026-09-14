"""
Official National Stock Exchange of India (NSE) & BSE Trading Holiday Calendar.
Ensures the trading bot never evaluates market sessions as OPEN or attempts to place
orders during official market closures.
"""
from datetime import datetime, date, timezone, timedelta
from typing import Tuple, Optional, Dict, List, Any, Union

IST = timezone(timedelta(hours=5, minutes=30))

# Official NSE Trading Holidays (Equity & Derivatives segments)
NSE_TRADING_HOLIDAYS: Dict[str, str] = {
    # 2024
    "2024-01-22": "Special Holiday (Ayodhya Ram Mandir)",
    "2024-01-26": "Republic Day",
    "2024-03-08": "Mahashivratri",
    "2024-03-25": "Holi",
    "2024-03-29": "Good Friday",
    "2024-04-11": "Id-Ul-Fitr (Ramzan Id)",
    "2024-04-17": "Shri Ram Navami",
    "2024-05-01": "Maharashtra Day",
    "2024-05-20": "General Parliamentary Elections (Mumbai)",
    "2024-06-17": "Bakri Id",
    "2024-07-17": "Muharram",
    "2024-08-15": "Independence Day",
    "2024-10-02": "Mahatma Gandhi Jayanti",
    "2024-11-01": "Diwali Laxmi Pujan",
    "2024-11-15": "Prakash Gurpurb Sri Guru Nanak Dev",
    "2024-11-20": "Maharashtra Assembly Elections",
    "2024-12-25": "Christmas",

    # 2025
    "2025-02-26": "Mahashivratri",
    "2025-03-14": "Holi",
    "2025-03-31": "Id-Ul-Fitr (Ramzan Id)",
    "2025-04-10": "Shri Mahavir Jayanti",
    "2025-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2025-04-18": "Good Friday",
    "2025-05-01": "Maharashtra Day",
    "2025-06-07": "Bakri Id",
    "2025-08-15": "Independence Day",
    "2025-08-27": "Ganesh Chaturthi",
    "2025-10-02": "Mahatma Gandhi Jayanti / Dussehra",
    "2025-10-21": "Diwali-Laxmi Pujan",
    "2025-10-22": "Diwali-Balipratipada",
    "2025-11-05": "Prakash Gurpurb Sri Guru Nanak Dev",
    "2025-12-25": "Christmas",

    # 2026
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-26": "Shri Ram Navami",
    "2026-03-31": "Shri Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-28": "Bakri Id",
    "2026-08-15": "Independence Day",
    "2026-09-14": "Ganesh Chaturthi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-10": "Diwali-Balipratipada",
    "2026-11-24": "Prakash Gurpurb Sri Guru Nanak Dev",
    "2026-12-25": "Christmas",
}


def is_nse_holiday(check_date: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
    """
    Checks if a given date is an official NSE trading holiday.
    check_date: datetime, date, or "YYYY-MM-DD" string. Defaults to current date in IST.
    Returns: (is_holiday, holiday_name_or_None)
    """
    if check_date is None:
        d = datetime.now(IST).date()
    elif isinstance(check_date, datetime):
        d = check_date.date()
    elif isinstance(check_date, date):
        d = check_date
    elif isinstance(check_date, str):
        try:
            d = datetime.strptime(check_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return False, None
    else:
        return False, None

    date_str = d.strftime("%Y-%m-%d")
    if date_str in NSE_TRADING_HOLIDAYS:
        return True, NSE_TRADING_HOLIDAYS[date_str]

    return False, None


def get_next_trading_day(from_date: Optional[Union[date, datetime, str]] = None) -> date:
    """Calculates the next calendar date that is neither a weekend nor an NSE holiday."""
    if from_date is None:
        curr = datetime.now(IST).date()
    elif isinstance(from_date, datetime):
        curr = from_date.date()
    elif isinstance(from_date, date):
        curr = from_date
    elif isinstance(from_date, str):
        curr = datetime.strptime(from_date[:10], "%Y-%m-%d").date()
    else:
        curr = datetime.now(IST).date()

    curr = curr + timedelta(days=1)
    while True:
        # Check weekend: 5 = Saturday, 6 = Sunday
        if curr.weekday() in (5, 6):
            curr += timedelta(days=1)
            continue
        # Check NSE holiday
        holiday, _ = is_nse_holiday(curr)
        if holiday:
            curr += timedelta(days=1)
            continue
        return curr
