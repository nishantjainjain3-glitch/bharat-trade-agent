import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from src.data.nifty500 import (
    get_nifty_500_constituents,
    get_nifty_500_symbols,
    get_symbols_by_industry
)
from src.analysis.nifty500_scanner import scan_nifty500_breakouts


class TestNifty500Scanner(unittest.TestCase):
    def test_get_nifty_500_constituents(self):
        constituents = get_nifty_500_constituents()
        self.assertGreaterEqual(len(constituents), 400)
        first = constituents[0]
        self.assertIn("symbol", first)
        self.assertIn("name", first)
        self.assertIn("industry", first)

    def test_get_nifty_500_symbols(self):
        symbols = get_nifty_500_symbols(limit=10)
        self.assertEqual(len(symbols), 10)
        self.assertTrue(all(isinstance(s, str) for s in symbols))

    def test_get_symbols_by_industry(self):
        financials = get_symbols_by_industry("Financial Services")
        self.assertGreater(len(financials), 10)

    @patch("yfinance.download")
    def test_scan_nifty500_breakouts_with_mock_data(self, mock_yf_download):
        # Create mock multi-ticker dataframe
        n = 25
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        
        # Build multi-index columns for RELIANCE.NS and TCS.NS
        tickers = ["RELIANCE.NS", "TCS.NS"]
        cols = pd.MultiIndex.from_product([tickers, ["Open", "High", "Low", "Close", "Volume"]])
        data_vals = np.ones((n, len(cols))) * 2000.0
        df_mock = pd.DataFrame(data_vals, index=dates, columns=cols)
        
        # Inject breakout on RELIANCE.NS using .loc
        df_mock.loc[dates[-1], ("RELIANCE.NS", "Close")] = 2500.0
        df_mock.loc[dates[-1], ("RELIANCE.NS", "High")] = 2520.0
        df_mock.loc[dates[-1], ("RELIANCE.NS", "Volume")] = 5000000.0
        df_mock.loc[dates[:-1], ("RELIANCE.NS", "Volume")] = 1000000.0

        mock_yf_download.return_value = df_mock

        res = scan_nifty500_breakouts(limit_stocks=2, account_equity=125000.0)
        self.assertIn("timestamp", res)
        self.assertIn("universe_size", res)
        self.assertIn("scanned_count", res)
        self.assertIn("opportunities", res)


if __name__ == "__main__":
    unittest.main()