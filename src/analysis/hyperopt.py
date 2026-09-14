import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from src.data.market_data import get_historical_bars, normalize_indian_symbol
from src.analysis.backtester import calculate_indian_trade_charges, calculate_risk_adjusted_ratios
from src.analysis.technical import calculate_rsi


def freqtrade_loss_objective(
    total_return_pct: float,
    max_drawdown_pct: float,
    win_rate_pct: float,
    total_trades: int,
    profit_factor: float
) -> float:
    """
    Freqtrade Hyperopt Loss Function (Calmar / Sortino blended loss).
    Lower score is better.
    Objective: Maximize returns and profit factor while heavily penalizing drawdown
    and small trade sample sizes (< 5 trades).
    """
    if total_trades < 4:
        return 1000.0  # Heavy penalty for statistically insignificant trades

    # Base score: negative return
    score = -1.0 * total_return_pct

    # Drawdown penalty (exponential penalty for drawdowns > 15%)
    if max_drawdown_pct > 15.0:
        score += (max_drawdown_pct - 15.0) * 2.5
    else:
        score += max_drawdown_pct * 0.5

    # Profit factor reward
    if profit_factor > 1.0:
        score -= min(50.0, profit_factor * 8.0)

    # Win rate reward
    score -= (win_rate_pct - 50.0) * 0.5

    return round(float(score), 4)


def simulate_breakout_vectorized(
    df: pd.DataFrame,
    lookback_entry: int,
    lookback_exit: int,
    atr_stop_mult: float,
    target_mult: float,
    rsi_filter: float
) -> Dict[str, Any]:
    """
    Fast, vectorized evaluation of breakout strategy parameters.
    """
    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # Precalculate ATR
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().bfill()

    # Precalculate RSI
    rsi = calculate_rsi(close, 14).bfill()

    # Channels
    high_channel = high.rolling(lookback_entry).max().shift(1)
    low_channel = low.rolling(lookback_exit).min().shift(1)

    trades = []
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    target_price = 0.0
    initial_cap = 100000.0
    capital = initial_cap
    equity_curve = [initial_cap]

    for i in range(max(lookback_entry, lookback_exit) + 1, len(df)):
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        curr_atr = float(atr.iloc[i])
        curr_rsi = float(rsi.iloc[i])
        h_chan = float(high_channel.iloc[i])
        l_chan = float(low_channel.iloc[i])

        if position == 0:
            # Entry condition: New high breakout + RSI filter
            if c > h_chan and curr_rsi >= rsi_filter:
                position = 1
                entry_price = c
                stop_loss = c - (atr_stop_mult * curr_atr)
                target_price = c + (target_mult * curr_atr)
        elif position == 1:
            # Exit condition: Stop loss, target, or breakdown below exit channel
            exit_hit = False
            exit_price = c

            if l <= stop_loss:
                exit_hit = True
                exit_price = stop_loss
            elif h >= target_price:
                exit_hit = True
                exit_price = target_price
            elif c < l_chan:
                exit_hit = True
                exit_price = c

            if exit_hit:
                shares = max(1, int((capital * 0.95) / entry_price))
                buy_val = shares * entry_price
                sell_val = shares * exit_price
                gross_pnl = sell_val - buy_val
                charges = calculate_indian_trade_charges(buy_val, sell_val)
                net_pnl = gross_pnl - charges["total_charges"]
                capital += net_pnl
                equity_curve.append(capital)

                trades.append({
                    "entry": entry_price,
                    "exit": exit_price,
                    "net_pnl": net_pnl,
                    "pnl_pct": (net_pnl / buy_val) * 100.0,
                    "is_win": net_pnl > 0
                })
                position = 0

    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_return_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "total_trades": 0,
            "loss_score": 999.0
        }

    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"]]
    win_rate = (len(wins) / total_trades) * 100.0

    gross_gains = sum([t["net_pnl"] for t in wins])
    gross_losses = abs(sum([t["net_pnl"] for t in losses]))
    profit_factor = round(gross_gains / gross_losses, 2) if gross_losses > 0 else (round(gross_gains, 2) if gross_gains > 0 else 1.0)

    total_return = ((capital - initial_cap) / initial_cap) * 100.0

    # Drawdown
    eq_arr = np.array(equity_curve)
    peaks = np.maximum.accumulate(eq_arr)
    dds = (peaks - eq_arr) / peaks * 100.0
    max_dd = float(np.max(dds))

    loss_score = freqtrade_loss_objective(total_return, max_dd, win_rate, total_trades, profit_factor)

    return {
        "total_return_pct": round(total_return, 2),
        "win_rate_pct": round(win_rate, 1),
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_dd, 2),
        "total_trades": total_trades,
        "loss_score": loss_score
    }


def hyperopt_optimize_symbol(
    symbol: str,
    period: str = "2y",
    max_evals: int = 50
) -> Dict[str, Any]:
    """
    Freqtrade Hyperopt Engine for Indian Stocks.
    Runs In-Sample (70%) parameter optimization and Out-of-Sample (30%) validation.
    """
    norm_symbol = normalize_indian_symbol(symbol)
    df = get_historical_bars(norm_symbol, period=period, interval="1d")
    if len(df) < 80:
        raise ValueError(f"Insufficient historical data for {norm_symbol}")

    # 70% In-Sample (Training) / 30% Out-of-Sample (Validation)
    split_idx = int(len(df) * 0.70)
    in_sample_df = df.iloc[:split_idx].copy()
    out_sample_df = df.iloc[split_idx:].copy()

    # Search Space
    lookback_entries = [15, 20, 25, 30, 40]
    lookback_exits = [7, 10, 14, 20]
    atr_stops = [1.5, 2.0, 2.5]
    targets = [3.5, 4.5, 5.5]
    rsi_filters = [45.0, 50.0, 55.0]

    best_params = None
    best_loss = float("inf")
    best_train_metrics = {}
    history = []

    # Deterministic grid + pseudo-random sampling
    eval_count = 0
    rng = np.random.default_rng(42)

    # Always test standard baseline first
    baseline = (20, 10, 2.0, 4.5, 50.0)
    all_combos = [baseline]

    # Generate candidate space
    for l_entry in lookback_entries:
        for l_exit in lookback_exits:
            for atr_s in atr_stops:
                for tgt in targets:
                    for rsi_f in rsi_filters:
                        combo = (l_entry, l_exit, atr_s, tgt, rsi_f)
                        if combo not in all_combos:
                            all_combos.append(combo)

    # Subsample if exceeds max_evals
    if len(all_combos) > max_evals:
        chosen_indices = [0] + list(rng.choice(range(1, len(all_combos)), size=max_evals - 1, replace=False))
        combos_to_test = [all_combos[idx] for idx in chosen_indices]
    else:
        combos_to_test = all_combos

    for combo in combos_to_test:
        l_entry, l_exit, atr_s, tgt, rsi_f = combo
        res = simulate_breakout_vectorized(
            in_sample_df,
            lookback_entry=l_entry,
            lookback_exit=l_exit,
            atr_stop_mult=atr_s,
            target_mult=tgt,
            rsi_filter=rsi_f
        )
        eval_count += 1
        loss = res["loss_score"]

        if loss < best_loss and res["total_trades"] >= 3:
            best_loss = loss
            best_params = {
                "lookback_entry": l_entry,
                "lookback_exit": l_exit,
                "atr_stop_mult": atr_s,
                "target_mult": tgt,
                "rsi_filter": rsi_f
            }
            best_train_metrics = res

    if best_params is None:
        best_params = {
            "lookback_entry": 20,
            "lookback_exit": 10,
            "atr_stop_mult": 2.0,
            "target_mult": 4.5,
            "rsi_filter": 50.0
        }
        best_train_metrics = simulate_breakout_vectorized(
            in_sample_df, 20, 10, 2.0, 4.5, 50.0
        )

    # Out-of-Sample Validation (The true test of robustness)
    validation_metrics = simulate_breakout_vectorized(
        out_sample_df,
        lookback_entry=best_params["lookback_entry"],
        lookback_exit=best_params["lookback_exit"],
        atr_stop_mult=best_params["atr_stop_mult"],
        target_mult=best_params["target_mult"],
        rsi_filter=best_params["rsi_filter"]
    )

    # Overfitting Check: Is validation performance consistent with training?
    train_pf = best_train_metrics.get("profit_factor", 1.0)
    val_pf = validation_metrics.get("profit_factor", 1.0)
    is_robust = (validation_metrics.get("total_return_pct", 0) >= 0) and (val_pf >= 1.0 or val_pf >= train_pf * 0.5)

    return {
        "symbol": norm_symbol,
        "total_evaluations": eval_count,
        "best_hyperparameters": best_params,
        "in_sample_training": best_train_metrics,
        "out_of_sample_validation": validation_metrics,
        "model_verdict": "ROBUST_STRATEGY" if is_robust else "POTENTIAL_OVERFIT",
        "training_window_bars": len(in_sample_df),
        "validation_window_bars": len(out_sample_df)
    }
