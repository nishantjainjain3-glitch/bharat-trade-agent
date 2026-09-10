import os
import io
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "nifty500.csv")
NSE_NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

_CACHED_CONSTITUENTS: Optional[List[Dict[str, Any]]] = None


def get_nifty_500_constituents(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Returns the complete list of 500 companies in the Nifty 500 universe.
    Caches to disk and memory for high performance.
    """
    global _CACHED_CONSTITUENTS
    if _CACHED_CONSTITUENTS is not None and not force_refresh:
        return _CACHED_CONSTITUENTS

    # 1. Try local CSV cache first
    if os.path.exists(CACHE_PATH) and not force_refresh:
        try:
            df = pd.read_csv(CACHE_PATH)
            _CACHED_CONSTITUENTS = _parse_df_to_constituents(df)
            if len(_CACHED_CONSTITUENTS) >= 400:
                return _CACHED_CONSTITUENTS
        except Exception as e:
            logger.warning(f"Error reading local Nifty 500 cache: {e}")

    # 2. Fetch fresh from NSE archives
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(NSE_NIFTY500_URL, headers=headers, timeout=12)
        if res.status_code == 200:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                f.write(res.text)
            df = pd.read_csv(io.StringIO(res.text))
            _CACHED_CONSTITUENTS = _parse_df_to_constituents(df)
            return _CACHED_CONSTITUENTS
    except Exception as e:
        logger.warning(f"Failed to fetch fresh Nifty 500 list from NSE: {e}")

    # 3. Fallback to top liquid stocks if offline
    if os.path.exists(CACHE_PATH):
        df = pd.read_csv(CACHE_PATH)
        _CACHED_CONSTITUENTS = _parse_df_to_constituents(df)
        return _CACHED_CONSTITUENTS

    return []


def _parse_df_to_constituents(df: pd.DataFrame) -> List[Dict[str, Any]]:
    constituents = []
    for _, row in df.iterrows():
        sym = str(row.get("Symbol", "")).strip()
        if sym and sym != "nan":
            constituents.append({
                "symbol": sym,
                "name": str(row.get("Company Name", sym)).strip(),
                "industry": str(row.get("Industry", "General")).strip(),
                "isin": str(row.get("ISIN Code", "")).strip()
            })
    return constituents


def get_nifty_500_symbols(limit: Optional[int] = None) -> List[str]:
    """Returns clean ticker symbols for the Nifty 500."""
    items = get_nifty_500_constituents()
    symbols = [x["symbol"] for x in items if x.get("symbol")]
    return symbols[:limit] if limit else symbols


def get_symbols_by_industry(industry: str) -> List[str]:
    """Filters Nifty 500 stocks by sector / industry."""
    items = get_nifty_500_constituents()
    ind_lower = industry.lower()
    return [x["symbol"] for x in items if ind_lower in x.get("industry", "").lower()]