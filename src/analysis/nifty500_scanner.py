import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.data.nifty500 import get_nifty_500_constituents, get_symbols_by_industry
from src.analysis.technical import calculate_rsi, calculate_bollinger_bands
from src.analysis.order_flow import analyze_order_flow
from src.analysis.volatility_regimes import analyze_volatility_regime
from src.engine.position_sizer import calculate_volatility_parity_position, calculate_atr
from src.engine.constitution import validate_order_against_constitution

logger = logging.getLogger(__name__)


def scan_nifty500_breakouts(
    limit_stocks: int = 50,
    sector_filter: Optional[str] = None,
    account_equity: float = 125000.0,
    available_cash: Optional[float] = None,
    tier_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    Two-stage high performance scanner across Nifty 500 equities.
    
    Stage 1: Multi-threaded batch download and vectorized pre-filter
             identifies volume surges (>= 1.35x) and 20-period price breakouts.
    Stage 2: Quant deep dive on candidates (Smart Money FVGs, TTM Squeeze,
             1% ATR Volatility-Parity sizing, and Constitution validation).
    """
    # 1. Fetch Universe
    constituents = get_nifty_500_constituents()
    if sector_filter:
        sec_lower = sector_filter.lower()
        candidates = [c for c in constituents if sec_lower in c.get("industry", "").lower()]
    else:
        candidates = constituents

    if not candidates:
        return {
            "timestamp": datetime.now().isoformat(),
            "universe_size": 0,
            "scanned_count": 0,
            "opportunities_found": 0,
            "opportunities": []
        }

    selected_cohort = candidates[:limit_stocks]
    symbol_map = {f"{c['symbol']}.NS": c for c in selected_cohort}
    tickers = list(symbol_map.keys())

    # 2. Stage 1: Batch Download
    logger.info(f"Scanning {len(tickers)} Nifty 500 stocks in multi-threaded batch...")
    try:
        data = yf.download(
            " ".join(tickers),
            period="1mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True
        )
    except Exception as e:
        logger.error(f"Failed batch download for Nifty 500: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "universe_size": len(constituents),
            "scanned_count": 0,
            "error": str(e),
            "opportunities": []
        }

    stage1_hits = []

    # Process each ticker from batch multi-index dataframe
    for ticker_ns, meta in symbol_map.items():
        try:
            if ticker_ns in data.columns.levels[0]:
                df_ticker = data[ticker_ns].dropna().copy()
            else:
                continue

            if len(df_ticker) < 15:
                continue

            closes = df_ticker["Close"]
            highs = df_ticker["High"]
            volumes = df_ticker["Volume"]

            curr_price = round(float(closes.iloc[-1]), 2)
            prev_close = float(closes.iloc[-2])
            day_chg_pct = round(((curr_price - prev_close) / prev_close) * 100.0, 2)

            # 20-period highest high
            prev_high = float(highs.iloc[:-1].max())
            vol_sma = float(volumes.iloc[:-1].mean())
            curr_vol = float(volumes.iloc[-1])

            vol_surge = round(curr_vol / vol_sma, 2) if vol_sma > 0 else 1.0
            is_breakout = curr_price >= (prev_high * 0.995)
            is_vol_strong = vol_surge >= 1.25

            # Stage 1 filter: Breakout or significant volume expansion
            if (is_breakout or vol_surge >= 1.6) and day_chg_pct > 0.2:
                stage1_hits.append({
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "industry": meta["industry"],
                    "price": curr_price,
                    "day_chg_pct": day_chg_pct,
                    "vol_surge": vol_surge,
                    "df": df_ticker
                })
        except Exception:
            continue

    # 3. Stage 2: Deep Quant Analysis on passing candidates
    opportunities = []
    for hit in stage1_hits:
        sym = hit["symbol"]
        df_k = hit["df"]
        price = hit["price"]

        try:
            # Indicator math
            rsi_series = calculate_rsi(df_k["Close"], period=14)
            curr_rsi = round(float(rsi_series.iloc[-1]), 2)
            atr_val = calculate_atr(df_k, period=14)
            if atr_val <= 0:
                atr_val = round(price * 0.02, 2)

            # Smart Money Order Flow
            of_analysis = analyze_order_flow(df_k)
            bos_detected = of_analysis.get("market_structure", {}).get("bos_detected", False)
            fvg_list = of_analysis.get("fair_value_gaps", [])
            fvg_nearby = any(abs(price - f.get("bottom", 0)) / price < 0.03 for f in fvg_list)

            # Volatility Regimes
            vol_analysis = analyze_volatility_regime(df_k)
            ttm_fired = vol_analysis.get("ttm_squeeze", {}).get("squeeze_fired", False)

            # Conviction calculation (1 - 10)
            conviction = 6
            if hit["vol_surge"] >= 1.75:
                conviction += 1
            if 50.0 <= curr_rsi <= 72.0:
                conviction += 1
            if bos_detected or fvg_nearby:
                conviction += 1
            if ttm_fired:
                conviction += 1
            conviction = min(10, conviction)

            # 1% ATR Volatility-Parity Position Sizing
            stop_distance = round(atr_val * 2.0, 2)
            sl = round(max(0.05, price - stop_distance), 2)
            tp = round(price + (stop_distance * 2.0), 2)

            sizing = calculate_volatility_parity_position(
                account_equity=account_equity,
                current_price=price,
                atr=atr_val,
                risk_pct=0.01,
                atr_stop_multiple=2.0,
                target_rr_ratio=2.0,
                tier_multiplier=tier_multiplier,
                available_cash=available_cash,
                max_allocation_pct=0.35
            )

            # Constitutional validation
            val = validate_order_against_constitution(
                symbol=sym,
                price=price,
                stop_loss=sl,
                target_price=tp,
                quantity=sizing.get("quantity", 1),
                portfolio_equity=account_equity
            )

            opportunities.append({
                "symbol": sym,
                "name": hit["name"],
                "industry": hit["industry"],
                "price": price,
                "day_chg_pct": hit["day_chg_pct"],
                "vol_surge": hit["vol_surge"],
                "rsi": curr_rsi,
                "atr": atr_val,
                "stop_loss": sl,
                "target_price": tp,
                "conviction": conviction,
                "bos_confirmed": bos_detected,
                "fvg_support": fvg_nearby,
                "ttm_squeeze_fired": ttm_fired,
                "position_sizing": sizing,
                "constitution_approved": val.get("allowed", False),
                "rationale": (
                    f"Nifty 500 Breakout: {hit['name']} (+{hit['day_chg_pct']}%) with {hit['vol_surge']}x volume surge. "
                    f"RSI: {curr_rsi}, 2x ATR SL ₹{sl} | TP ₹{tp} (2:1 RR). Conviction: {conviction}/10."
                )
            })
        except Exception as e:
            logger.debug(f"Stage 2 error on {sym}: {e}")

    # Rank by conviction descending
    opportunities.sort(key=lambda x: (x.get("conviction", 0), x.get("vol_surge", 0)), reverse=True)

    return {
        "timestamp": datetime.now().isoformat(),
        "universe_size": len(constituents),
        "scanned_count": len(selected_cohort),
        "stage1_passed": len(stage1_hits),
        "opportunities_found": len(opportunities),
        "opportunities": opportunities
    }