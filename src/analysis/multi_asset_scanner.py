import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.data.market_data import get_historical_bars, get_stock_quote
from src.analysis.technical import calculate_rsi, calculate_bollinger_bands
from src.engine.position_sizer import calculate_volatility_parity_position, calculate_atr

logger = logging.getLogger(__name__)

# Default asset universes mapped to NSE instruments
INDEX_ETFS = {
    "NIFTYBEES": {"std_dev": 1.5, "name": "Nifty 50 ETF"},
    "BANKBEES": {"std_dev": 1.8, "name": "Bank Nifty ETF"}
}

COMMODITY_ETFS = {
    "GOLDBEES": {"name": "Gold ETF"},
    "SILVERBEES": {"name": "Silver ETF"}
}

MOMENTUM_EQUITIES = [
    "RELIANCE", "TCS", "INFY", "ICICIBANK", "BHARTIARTL", "HDFCBANK"
]


def check_correlation_regime(
    nifty_df: Optional[pd.DataFrame] = None,
    india_vix: Optional[float] = None
) -> Dict[str, Any]:
    """Multi-asset correlation and overbought filter."""
    momentum_allowed = True
    reasons = []
    nifty_rsi = 50.0
    vix_val = india_vix if india_vix is not None else 14.5

    if nifty_df is not None and len(nifty_df) >= 20:
        rsi_series = calculate_rsi(nifty_df["Close"])
        nifty_rsi = round(float(rsi_series.iloc[-1]), 2)
        if nifty_rsi > 72.0:
            momentum_allowed = False
            reasons.append(f"Nifty 50 is extremely overbought (RSI: {nifty_rsi} > 72)")

        upper, sma, _ = calculate_bollinger_bands(nifty_df["Close"], 20, 2.5)
        if float(nifty_df["Close"].iloc[-1]) > float(upper.iloc[-1]):
            momentum_allowed = False
            reasons.append("Nifty 50 price > 2.5x standard deviation above 20 SMA")

    if vix_val >= 24.0:
        momentum_allowed = False
        reasons.append(f"India VIX elevated ({vix_val} >= 24.0): High macro panic")

    return {
        "momentum_allowed": momentum_allowed,
        "nifty_rsi": nifty_rsi,
        "india_vix": vix_val,
        "status": "PASSED" if momentum_allowed else "BLOCKED",
        "reason": " | ".join(reasons) if reasons else "Market correlation regime healthy."
    }


def evaluate_index_mean_reversion(
    symbol: str,
    df: pd.DataFrame,
    std_dev: float = 1.5
) -> Optional[Dict[str, Any]]:
    """Strategy 1: Index Mean Reversion (Intraday 15-min Candles)."""
    if df is None or len(df) < 25:
        return None

    closes = df["Close"]
    current_price = round(float(closes.iloc[-1]), 2)

    upper, sma, lower = calculate_bollinger_bands(closes, period=20, std_dev=std_dev)
    rsi_series = calculate_rsi(closes, period=14)
    atr_val = calculate_atr(df, period=14)

    curr_sma = round(float(sma.iloc[-1]), 2)
    curr_lower = round(float(lower.iloc[-1]), 2)
    curr_upper = round(float(upper.iloc[-1]), 2)
    curr_rsi = round(float(rsi_series.iloc[-1]), 2)

    if current_price <= curr_lower and curr_rsi <= 42.0:
        stop_distance = round(max(atr_val * 1.5, current_price * 0.005), 2)
        sl = round(max(0.05, current_price - stop_distance), 2)
        tp = curr_sma
        projected_reward = tp - current_price

        if projected_reward >= stop_distance * 1.3:
            rr_ratio = round(projected_reward / stop_distance, 2)
            return {
                "strategy_type": "INDEX_MEAN_REVERSION",
                "symbol": symbol,
                "asset_class": "INDEX_ETF",
                "timeframe": "15m",
                "direction": "BUY",
                "entry_price": current_price,
                "stop_loss": sl,
                "target_price": tp,
                "atr": atr_val,
                "risk_per_share": stop_distance,
                "risk_reward_ratio": rr_ratio,
                "conviction": 8 if curr_rsi <= 35 else 7,
                "rationale": (
                    f"Oversold mean reversion setup: Price (₹{current_price}) <= {std_dev}x lower band (₹{curr_lower}) "
                    f"with RSI {curr_rsi}. Targeting 20 SMA mean (₹{curr_sma})."
                )
            }

    return None


def evaluate_commodity_trend(
    symbol: str,
    df: pd.DataFrame
) -> Optional[Dict[str, Any]]:
    """Strategy 2: Commodity Trend Following (Higher Timeframe 4h/1d Candles)."""
    if df is None or len(df) < 70:
        return None

    closes = df["Close"]
    current_price = round(float(closes.iloc[-1]), 2)

    ema_50 = closes.ewm(span=50, adjust=False).mean()
    ema_200 = closes.ewm(span=200, adjust=False).mean()
    atr_val = calculate_atr(df, period=14)

    curr_50 = round(float(ema_50.iloc[-1]), 2)
    curr_200 = round(float(ema_200.iloc[-1]), 2)

    ema_50_slope = curr_50 - float(ema_50.iloc[-6])
    golden_cross = curr_50 > curr_200

    is_pullback = (current_price >= curr_50 * 0.98) and (current_price <= curr_50 * 1.025)

    if golden_cross and ema_50_slope > 0 and is_pullback:
        stop_distance = round(max(atr_val * 3.0, current_price * 0.01), 2)
        sl = round(max(0.05, current_price - stop_distance), 2)
        tp = round(current_price + (stop_distance * 2.0), 2)

        return {
            "strategy_type": "COMMODITY_TREND",
            "symbol": symbol,
            "asset_class": "COMMODITY_ETF",
            "timeframe": "4h",
            "direction": "BUY",
            "entry_price": current_price,
            "stop_loss": sl,
            "target_price": tp,
            "atr": atr_val,
            "risk_per_share": stop_distance,
            "risk_reward_ratio": 2.0,
            "conviction": 8,
            "rationale": (
                f"Commodity uptrend pullback: 50 EMA (₹{curr_50}) above 200 EMA (₹{curr_200}). "
                f"Price near 50 EMA support with 3x ATR (₹{stop_distance}) trailing stop."
            )
        }

    return None


def evaluate_momentum_breakout(
    symbol: str,
    df: pd.DataFrame
) -> Optional[Dict[str, Any]]:
    """Strategy 3: Equity Momentum Breakout (1-hour Candles)."""
    if df is None or len(df) < 25:
        return None

    closes = df["Close"]
    highs = df["High"]
    volumes = df["volume"] if "volume" in df.columns else df["Volume"]
    current_price = round(float(closes.iloc[-1]), 2)

    prev_20_high = float(highs.iloc[-21:-1].max())
    vol_sma_20 = float(volumes.iloc[-21:-1].mean())
    curr_vol = float(volumes.iloc[-1])

    rsi_series = calculate_rsi(closes, period=14)
    atr_val = calculate_atr(df, period=14)
    curr_rsi = round(float(rsi_series.iloc[-1]), 2)

    vol_surge = round(curr_vol / vol_sma_20, 2) if vol_sma_20 > 0 else 1.0
    is_breakout = current_price >= prev_20_high
    is_vol_confirmed = vol_surge >= 1.3
    in_momentum_zone = 54.0 <= curr_rsi <= 74.0

    if is_breakout and is_vol_confirmed and in_momentum_zone:
        stop_distance = round(max(atr_val * 2.0, current_price * 0.005), 2)
        sl = round(max(0.05, current_price - stop_distance), 2)
        tp = round(current_price + (stop_distance * 2.0), 2)

        return {
            "strategy_type": "MOMENTUM_BREAKOUT",
            "symbol": symbol,
            "asset_class": "MOMENTUM_STOCK",
            "timeframe": "1h",
            "direction": "BUY",
            "entry_price": current_price,
            "stop_loss": sl,
            "target_price": tp,
            "atr": atr_val,
            "risk_per_share": stop_distance,
            "risk_reward_ratio": 2.0,
            "conviction": 8 if vol_surge >= 1.7 else 7,
            "rationale": (
                f"Momentum breakout: Price ₹{current_price} broke above 20-period high (₹{prev_20_high}) "
                f"with {vol_surge}x volume surge and RSI {curr_rsi}."
            )
        }

    return None


def scan_multi_asset_opportunities(
    account_equity: float = 125000.0,
    available_cash: Optional[float] = None,
    tier_multiplier: float = 1.0,
    nifty_df_override: Optional[pd.DataFrame] = None,
    india_vix_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Scans NSE across all three asset classes:
    1. Index Mean Reversion (NIFTYBEES, BANKBEES)
    2. Commodity Trend Following (GOLDBEES, SILVERBEES)
    3. Equity Momentum Breakout (High-beta NSE leaders)
    Applies multi-asset correlation filter & 1% ATR volatility-parity sizing.
    """
    nifty_df = nifty_df_override
    if nifty_df is None:
        try:
            nifty_df = get_historical_bars("NIFTYBEES", period="1mo", interval="1d")
        except Exception:
            pass

    correlation_result = check_correlation_regime(nifty_df, india_vix_override)
    allow_momentum = correlation_result["momentum_allowed"]

    opportunities = []

    # 1. Scan Index ETFs (Mean Reversion)
    for sym, meta in INDEX_ETFS.items():
        try:
            df = get_historical_bars(sym, period="5d", interval="15m")
            sig = evaluate_index_mean_reversion(sym, df, std_dev=meta["std_dev"])
            if sig:
                sizing = calculate_volatility_parity_position(
                    account_equity=account_equity,
                    current_price=sig["entry_price"],
                    atr=sig["atr"],
                    risk_pct=0.01,
                    atr_stop_multiple=1.5,
                    target_rr_ratio=sig["risk_reward_ratio"],
                    tier_multiplier=tier_multiplier,
                    available_cash=available_cash
                )
                sig["position_sizing"] = sizing
                sig["correlation_status"] = "PASSED"
                opportunities.append(sig)
        except Exception as e:
            logger.debug(f"Index scan skipped for {sym}: {e}")

    # 2. Scan Commodity ETFs (Trend Following)
    for sym, meta in COMMODITY_ETFS.items():
        try:
            df = get_historical_bars(sym, period="3mo", interval="1d")
            sig = evaluate_commodity_trend(sym, df)
            if sig:
                sizing = calculate_volatility_parity_position(
                    account_equity=account_equity,
                    current_price=sig["entry_price"],
                    atr=sig["atr"],
                    risk_pct=0.01,
                    atr_stop_multiple=3.0,
                    target_rr_ratio=2.0,
                    tier_multiplier=tier_multiplier,
                    available_cash=available_cash
                )
                sig["position_sizing"] = sizing
                sig["correlation_status"] = "PASSED"
                opportunities.append(sig)
        except Exception as e:
            logger.debug(f"Commodity scan skipped for {sym}: {e}")

    # 3. Scan Momentum Equities (Breakouts)
    for sym in MOMENTUM_EQUITIES:
        try:
            df = get_historical_bars(sym, period="1mo", interval="60m")
            sig = evaluate_momentum_breakout(sym, df)
            if sig:
                if not allow_momentum:
                    sig["correlation_status"] = "BLOCKED"
                    sig["rationale"] += f" [BLOCKED by Market Correlation Filter: {correlation_result['reason']}]"
                else:
                    sig["correlation_status"] = "PASSED"
                    sizing = calculate_volatility_parity_position(
                        account_equity=account_equity,
                        current_price=sig["entry_price"],
                        atr=sig["atr"],
                        risk_pct=0.01,
                        atr_stop_multiple=2.0,
                        target_rr_ratio=2.0,
                        tier_multiplier=tier_multiplier,
                        available_cash=available_cash
                    )
                    sig["position_sizing"] = sizing
                opportunities.append(sig)
        except Exception as e:
            logger.debug(f"Momentum scan skipped for {sym}: {e}")

    opportunities.sort(key=lambda x: x.get("conviction", 0), reverse=True)

    return {
        "timestamp": datetime.now().isoformat(),
        "correlation_filter": correlation_result,
        "opportunities_found": len(opportunities),
        "actionable_count": len([x for x in opportunities if x.get("correlation_status") == "PASSED"]),
        "opportunities": opportunities
    }