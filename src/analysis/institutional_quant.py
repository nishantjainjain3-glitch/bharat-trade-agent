import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_fractional_kelly(
    win_rate: float,
    win_loss_ratio: float,
    kelly_fraction: float = 0.25,
    max_cap: float = 0.10
) -> Dict[str, Any]:
    """
    Fractional Kelly Criterion for optimal capital allocation.
    Full Kelly formula: f* = (W * (R + 1) - 1) / R
    Where:
        W = win rate probability (0.0 to 1.0)
        R = win-to-loss payoff ratio (e.g. 2.0 for 1:2 R:R)
    
    Quarter-Kelly (kelly_fraction = 0.25) is standard institutional practice
    to protect against estimation errors in non-stationary markets.
    """
    if win_rate <= 0.0 or win_loss_ratio <= 0.0:
        return {
            "full_kelly": 0.0,
            "recommended_allocation_pct": 0.0,
            "kelly_fraction": kelly_fraction,
            "is_positive_expectancy": False,
            "edge": 0.0
        }

    edge = (win_rate * win_loss_ratio) - (1.0 - win_rate)
    if edge <= 0.0:
        return {
            "full_kelly": 0.0,
            "recommended_allocation_pct": 0.0,
            "kelly_fraction": kelly_fraction,
            "is_positive_expectancy": False,
            "edge": round(edge, 4)
        }

    full_kelly = ((win_rate * (win_loss_ratio + 1.0)) - 1.0) / win_loss_ratio
    full_kelly = max(0.0, full_kelly)

    fractional = full_kelly * kelly_fraction
    clamped_allocation = min(fractional, max_cap)

    return {
        "full_kelly": round(full_kelly * 100.0, 2),
        "fractional_kelly_pct": round(fractional * 100.0, 2),
        "recommended_allocation_pct": round(clamped_allocation * 100.0, 2),
        "kelly_fraction": kelly_fraction,
        "is_positive_expectancy": True,
        "edge": round(edge, 4),
        "max_cap_pct": round(max_cap * 100.0, 2)
    }


def calculate_volatility_parity_position(
    capital: float,
    risk_pct: float,
    current_price: float,
    atr: float,
    stop_multiplier: float = 1.5,
    target_multiplier: float = 3.0
) -> Dict[str, Any]:
    """
    Volatility-Parity Position Sizing (Risk Budgeting).
    Calculates exact integer shares so that hitting the Stop Loss costs exactly
    (Capital * RiskPct) in currency.
    """
    if capital <= 0 or risk_pct <= 0 or current_price <= 0 or atr <= 0:
        return {
            "shares": 0,
            "position_value": 0.0,
            "dollar_risk": 0.0,
            "risk_pct_actual": 0.0,
            "stop_loss": 0.0,
            "target": 0.0,
            "risk_per_share": 0.0,
            "status": "INVALID_INPUTS"
        }

    dollar_risk_budget = capital * risk_pct
    risk_per_share = round(stop_multiplier * atr, 2)
    
    if risk_per_share <= 0:
        return {
            "shares": 0,
            "position_value": 0.0,
            "dollar_risk": 0.0,
            "risk_pct_actual": 0.0,
            "stop_loss": 0.0,
            "target": 0.0,
            "risk_per_share": 0.0,
            "status": "ZERO_RISK_PER_SHARE"
        }

    raw_shares = dollar_risk_budget / risk_per_share
    shares = int(np.floor(raw_shares))

    if shares == 0 and capital >= current_price:
        shares = 1

    position_value = round(shares * current_price, 2)
    actual_dollar_risk = round(shares * risk_per_share, 2)
    actual_risk_pct = round((actual_dollar_risk / capital) * 100.0, 3) if capital > 0 else 0.0

    stop_loss = round(max(0.01, current_price - risk_per_share), 2)
    target = round(current_price + (target_multiplier * atr), 2)

    return {
        "shares": shares,
        "entry_price": round(current_price, 2),
        "stop_loss": stop_loss,
        "target": target,
        "risk_per_share": risk_per_share,
        "dollar_risk_budget": round(dollar_risk_budget, 2),
        "actual_dollar_risk": actual_dollar_risk,
        "actual_risk_pct": actual_risk_pct,
        "position_value": position_value,
        "portfolio_weight_pct": round((position_value / capital) * 100.0, 2) if capital > 0 else 0.0,
        "risk_reward_ratio": round(target_multiplier / stop_multiplier, 2),
        "status": "CALCULATED"
    }


def calculate_hurst_exponent(
    df: pd.DataFrame,
    min_window: int = 10,
    max_window: int = 100
) -> Dict[str, Any]:
    """
    Hurst Exponent (H) via Rescaled Range (R/S) Analysis.
    Classifies the time series market regime:
        H > 0.55: Persistent (Trending). Trend systems favorable.
        0.45 <= H <= 0.55: Random Walk (Brownian Motion). Breakouts prone to fail.
        H < 0.45: Anti-Persistent (Mean-Reverting). Mean-reversion systems favorable.
    """
    if len(df) < 35 or 'Close' not in df.columns:
        return {
            "hurst_exponent": 0.50,
            "regime": "INSUFFICIENT_DATA",
            "recommended_strategy": "NEUTRAL",
            "is_trending": False,
            "is_mean_reverting": False
        }

    prices = df['Close'].values.astype(float)
    returns = np.diff(np.log(prices))

    if len(returns) < 30:
        return {
            "hurst_exponent": 0.50,
            "regime": "INSUFFICIENT_DATA",
            "recommended_strategy": "NEUTRAL",
            "is_trending": False,
            "is_mean_reverting": False
        }

    n_bars = len(returns)
    max_window = min(max_window, n_bars // 2)
    if min_window >= max_window:
        min_window = max(5, max_window // 4)

    window_sizes = np.unique(np.logspace(np.log10(min_window), np.log10(max_window), num=8).astype(int))
    window_sizes = [w for w in window_sizes if w >= 4 and w <= n_bars]

    if len(window_sizes) < 3:
        return {
            "hurst_exponent": 0.50,
            "regime": "INSUFFICIENT_DATA",
            "recommended_strategy": "NEUTRAL",
            "is_trending": False,
            "is_mean_reverting": False
        }

    rs_values = []

    for w in window_sizes:
        n_chunks = n_bars // w
        if n_chunks == 0:
            continue
        chunk_rs = []
        for i in range(n_chunks):
            chunk = returns[i * w:(i + 1) * w]
            mean_chunk = np.mean(chunk)
            dev = chunk - mean_chunk
            cum_dev = np.cumsum(dev)
            r = np.max(cum_dev) - np.min(cum_dev)
            s = np.std(chunk, ddof=1)
            if s > 1e-8:
                chunk_rs.append(r / s)
        if chunk_rs:
            rs_values.append(np.mean(chunk_rs))
        else:
            rs_values.append(1.0)

    log_w = np.log(window_sizes[:len(rs_values)])
    log_rs = np.log(np.maximum(rs_values, 1e-8))

    if len(log_w) < 2:
        h = 0.50
    else:
        try:
            poly = np.polyfit(log_w, log_rs, 1)
            h = float(poly[0])
            h = max(0.05, min(0.95, h))
        except Exception:
            h = 0.50

    h_rounded = round(h, 3)

    if h_rounded > 0.55:
        regime = "PERSISTENT_TREND"
        rec_strat = "FAVOR_TREND_BREAKOUTS (Minervini VCP, 5-Pillar Momentum, Donchian)"
        is_trend = True
        is_mr = False
    elif h_rounded < 0.45:
        regime = "MEAN_REVERTING"
        rec_strat = "FAVOR_MEAN_REVERSION (Connors RSI(2), Camarilla L3 Bounce, Supply/Demand)"
        is_trend = False
        is_mr = True
    else:
        regime = "RANDOM_WALK"
        rec_strat = "CHOPPY_EQUILIBRIUM (Reduce size or trade tight range boundaries only)"
        is_trend = False
        is_mr = False

    return {
        "hurst_exponent": h_rounded,
        "regime": regime,
        "recommended_strategy": rec_strat,
        "is_trending": is_trend,
        "is_mean_reverting": is_mr,
        "sample_size": n_bars
    }


def calculate_order_book_imbalance(
    bids: List[Dict[str, Any]],
    asks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Order Book Imbalance (OBI) from 5-level market depth.
    OBI = (Sum(Bid Volume) - Sum(Ask Volume)) / (Sum(Bid Volume) + Sum(Ask Volume))
    """
    if not bids and not asks:
        return {
            "imbalance_ratio": 0.0,
            "signal": "NO_DEPTH_DATA",
            "bid_volume": 0,
            "ask_volume": 0,
            "weighted_spread": 0.0
        }

    total_bid_vol = sum(float(b.get("quantity", b.get("qty", 0))) for b in bids)
    total_ask_vol = sum(float(a.get("quantity", a.get("qty", 0))) for a in asks)

    total_vol = total_bid_vol + total_ask_vol
    if total_vol == 0:
        return {
            "imbalance_ratio": 0.0,
            "signal": "ZERO_LIQUIDITY",
            "bid_volume": 0,
            "ask_volume": 0,
            "weighted_spread": 0.0
        }

    imbalance = (total_bid_vol - total_ask_vol) / total_vol
    imbalance = round(float(imbalance), 3)

    if imbalance > 0.25:
        signal = "BULLISH_LIQUIDITY_ACCUMULATION"
    elif imbalance < -0.25:
        signal = "BEARISH_SUPPLY_OVERHANG"
    else:
        signal = "BALANCED_DEPTH"

    best_bid = float(bids[0].get("price", 0)) if bids else 0.0
    best_ask = float(asks[0].get("price", 0)) if asks else 0.0
    spread = round(best_ask - best_bid, 2) if (best_ask > 0 and best_bid > 0) else 0.0

    return {
        "imbalance_ratio": imbalance,
        "signal": signal,
        "bid_volume": int(total_bid_vol),
        "ask_volume": int(total_ask_vol),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread
    }


def check_portfolio_correlation_shield(
    candidate_returns: pd.Series,
    holdings_returns: Dict[str, pd.Series],
    correlation_threshold: float = 0.70
) -> Dict[str, Any]:
    """
    Portfolio Correlation Shielding.
    Evaluates whether adding candidate stock creates harmful multi-asset concentration.
    """
    if not holdings_returns or candidate_returns.empty:
        return {
            "shield_pass": True,
            "highest_correlated_symbol": None,
            "highest_correlation": 0.0,
            "correlations": {},
            "recommendation": "SAFE_TO_ALLOCATE"
        }

    correlations = {}
    for symbol, ret_series in holdings_returns.items():
        if ret_series.empty:
            continue
        aligned = pd.concat([candidate_returns, ret_series], axis=1).dropna()
        if len(aligned) >= 15:
            corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
            if not np.isnan(corr):
                correlations[symbol] = round(corr, 3)

    if not correlations:
        return {
            "shield_pass": True,
            "highest_correlated_symbol": None,
            "highest_correlation": 0.0,
            "correlations": {},
            "recommendation": "SAFE_TO_ALLOCATE"
        }

    sorted_corrs = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
    highest_sym, highest_val = sorted_corrs[0]

    shield_pass = highest_val < correlation_threshold

    if not shield_pass:
        rec = f"REJECT_OR_SIZE_DOWN: High correlation ({highest_val}) with existing holding {highest_sym}. Adding creates duplicate risk."
    else:
        rec = "SAFE_TO_ALLOCATE: Portfolio correlation is well diversified."

    return {
        "shield_pass": shield_pass,
        "highest_correlated_symbol": highest_sym,
        "highest_correlation": highest_val,
        "correlations": correlations,
        "threshold": correlation_threshold,
        "recommendation": rec
    }


def calculate_twap_execution_schedule(
    total_shares: int,
    num_slices: int = 4,
    interval_minutes: int = 15
) -> Dict[str, Any]:
    """
    Time-Weighted Average Price (TWAP) Order Slicer.
    """
    if total_shares <= 0 or num_slices <= 0:
        return {
            "total_shares": 0,
            "slices": [],
            "num_slices": 0
        }

    if total_shares < num_slices:
        num_slices = max(1, total_shares)

    base_slice = total_shares // num_slices
    remainder = total_shares % num_slices

    slices = []
    for i in range(num_slices):
        qty = base_slice + (1 if i < remainder else 0)
        slices.append({
            "tranche_number": i + 1,
            "quantity": int(qty),
            "suggested_minute_offset": i * interval_minutes
        })

    return {
        "total_shares": total_shares,
        "num_slices": num_slices,
        "interval_minutes": interval_minutes,
        "slices": slices,
        "strategy": "TWAP_ALGORITHMIC_SLICING"
    }
