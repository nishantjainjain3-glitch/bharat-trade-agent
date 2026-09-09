import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.market_data import get_stock_quote, get_historical_bars, get_company_fundamentals
from src.data.macro_data import get_indian_macro_indicators
from src.data.news_data import get_indian_stock_news
from src.analysis.technical import analyze_technical_indicators
from src.analysis.fundamental import evaluate_fundamentals
from src.agents.research_team import run_multi_agent_research
from src.broker.angel_one import angel_client

def test_pipeline():
    print(">>> 1. Testing Live Macro Indicators (USD/INR, Crude, Nifty) ...")
    macro = get_indian_macro_indicators()
    assert "USDINR" in macro and "NIFTY" in macro
    print(f"    SUCCESS: USD/INR={macro['USDINR']['price']}, Nifty={macro['NIFTY']['price']}, Brent Crude={macro['CRUDE_OIL']['price']}")

    print("\n>>> 2. Testing Live Stock News Fetch for RELIANCE ...")
    news = get_indian_stock_news("RELIANCE", "Reliance Industries")
    assert len(news) > 0
    print(f"    SUCCESS: Fetched {len(news)} live headlines. Top: '{news[0]['title'][:60]}...'")

    print("\n>>> 3. Testing Technical & Fundamental Pipeline ...")
    quote = get_stock_quote("RELIANCE")
    df = get_historical_bars("RELIANCE", period="6mo", interval="1d")
    technicals = analyze_technical_indicators(df)
    funds = evaluate_fundamentals(get_company_fundamentals("RELIANCE"))
    print(f"    SUCCESS: RSI={technicals['rsi']}, Trend={technicals['trend']}, Verdict={funds['verdict']}")

    print("\n>>> 4. Testing Multi-Agent Research with Live News Injected ...")
    research = run_multi_agent_research(quote, technicals, funds, news)
    assert "verdict" in research
    print(f"    SUCCESS: Decision={research['verdict']}, Conviction={research['conviction']}/10")
    print(f"    Entry: {research.get('entry_range')}, Target: {research.get('target_price')}, SL: {research.get('stop_loss')}")

    print("\n>>> 5. Testing Angel One Module ...")
    portfolio = angel_client.get_portfolio_summary()
    assert "holdings" in portfolio
    print(f"    SUCCESS: Mode={portfolio['mode']}, Margin=INR {portfolio.get('available_cash')}")

    print("\n" + "="*55)
    print("ALL TESTS PASSED! FULL SYSTEM WITH MACRO & NEWS IS VERIFIED.")
    print("="*55)

if __name__ == "__main__":
    test_pipeline()
