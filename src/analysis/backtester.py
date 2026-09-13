import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.data.market_data import get_historical_bars, normalize_indian_symbol
from src.analysis.technical import calculate_rsi, calculate_macd

def calculate_indian_trade_charges(
    buy_value: float, 
    sell_value: float, 
    slippage_pct: float = 0.0005
) -> Dict[str, float]:
    """
    Calculates realistic statutory Indian equity charges and slippage:
    - Brokerage: flat INR 20 per leg (max INR 40 roundtrip) or 0.05%
    - STT: 0.1% on buy + 0.1% on sell (equity delivery)
    - Exchange Turnover Fee (NSE): 0.00325% of turnover
    - SEBI Turnover Fee: 0.0001% of turnover
    - Stamp Duty: 0.015% on buy value
    - GST: 18% on (brokerage + exchange fee + SEBI fee)
    - Execution Slippage: 0.05% per leg
    """
    turnover = buy_value + sell_value
    slippage_cost = turnover * slippage_pct
    brokerage = min(20.0, buy_value * 0.0005) + min(20.0, sell_value * 0.0005)
    stt = turnover * 0.001
    exchange_fee = turnover * 0.0000325
    sebi_fee = turnover * 0.000001
    stamp_duty = buy_value * 0.00015
    gst = (brokerage + exchange_fee + sebi_fee) * 0.18
    total_charges = slippage_cost + brokerage + stt + exchange_fee + sebi_fee + stamp_duty + gst
    
    return {
        "turnover": round(turnover, 2),
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_fees": round(exchange_fee, 2),
        "sebi_charges": round(sebi_fee, 2),
        "stamp_duty": round(stamp_duty, 2),
        "gst": round(gst, 2),
        "slippage": round(slippage_cost, 2),
        "total_charges": round(total_charges, 2)
    }

def calculate_risk_adjusted_ratios(
    daily_returns: pd.Series, 
    risk_free_rate_annual: float = 0.07
) -> Dict[str, float]:
    """
    Computes annualized Sharpe Ratio, Sortino Ratio, and Volatility
    benchmarked against the 10Y Indian Government Bond yield (~7.0%).
    """
    clean_returns = daily_returns.dropna()
    if len(clean_returns) < 10 or float(clean_returns.std()) == 0.0:
        return {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "annualized_volatility_pct": 0.0
        }
    
    ann_return = float(clean_returns.mean()) * 252.0
    ann_vol = float(clean_returns.std()) * np.sqrt(252.0)
    sharpe = (ann_return - risk_free_rate_annual) / ann_vol if ann_vol > 0 else 0.0
    
    # Downside deviation for Sortino ratio
    rf_daily = risk_free_rate_annual / 252.0
    downside_returns = clean_returns[clean_returns < rf_daily] - rf_daily
    if len(downside_returns) > 0 and float(downside_returns.var()) > 0:
        downside_vol = float(np.sqrt(np.mean(downside_returns ** 2))) * np.sqrt(252.0)
        sortino = (ann_return - risk_free_rate_annual) / downside_vol if downside_vol > 0 else 0.0
    else:
        sortino = sharpe if sharpe > 0 else 0.0

    return {
        "sharpe_ratio": round(float(sharpe), 2),
        "sortino_ratio": round(float(sortino), 2),
        "annualized_volatility_pct": round(float(ann_vol * 100.0), 2)
    }

def run_monte_carlo_simulation(
    trades_pnl_pct: List[float], 
    initial_capital: float = 100000.0, 
    runs: int = 500
) -> Dict[str, Any]:
    """
    Shuffles trade return sequence across 500 permutations to model
    path-dependent risk, 95% worst-case drawdown, and risk of ruin (>20% loss).
    """
    if len(trades_pnl_pct) < 3:
        return {
            "median_drawdown_pct": 0.0,
            "var_95_drawdown_pct": 0.0,
            "risk_of_ruin_pct": 0.0,
            "simulated_runs_count": 0
        }
    
    rng = np.random.default_rng(seed=42)
    pnl_array = np.array(trades_pnl_pct) / 100.0
    drawdowns = []
    ruin_count = 0
    
    for _ in range(runs):
        shuffled = rng.permutation(pnl_array)
        equity = initial_capital * np.cumprod(1.0 + shuffled)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak
        max_dd = float(np.max(dd)) * 100.0
        drawdowns.append(max_dd)
        if max_dd >= 20.0:
            ruin_count += 1
            
    drawdowns = np.sort(drawdowns)
    median_dd = float(np.median(drawdowns))
    var_95_dd = float(np.percentile(drawdowns, 95))
    risk_of_ruin = (ruin_count / runs) * 100.0
    
    return {
        "median_drawdown_pct": round(median_dd, 2),
        "var_95_drawdown_pct": round(var_95_dd, 2),
        "risk_of_ruin_pct": round(risk_of_ruin, 1),
        "simulated_runs_count": runs
    }

def backtest_strategy(
    symbol: str, 
    strategy_name: str = "EMA_CROSS", 
    period: str = "2y", 
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    norm_symbol = normalize_indian_symbol(symbol)
    df = get_historical_bars(norm_symbol, period=period, interval="1d")
    if len(df) < 60:
        raise ValueError(f"Insufficient historical data for {norm_symbol} ({len(df)} bars)")

    df['Close'] = df['Close'].astype(float)
    df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
    close = df['Close']

    df['Signal'] = 0

    if strategy_name == "EMA_CROSS":
        df['EMA_Fast'] = close.ewm(span=20, adjust=False).mean()
        df['EMA_Slow'] = close.ewm(span=50, adjust=False).mean()
        df['Signal'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, 0)

    elif strategy_name == "RSI_REVERSAL":
        df['RSI'] = calculate_rsi(close, period=14)
        position = 0
        signals = []
        for rsi in df['RSI']:
            if rsi < 35:
                position = 1
            elif rsi > 65:
                position = 0
            signals.append(position)
        df['Signal'] = signals

    elif strategy_name == "BREAKOUT":
        df['High_20'] = df['High'].rolling(20).max().shift(1)
        df['Low_10'] = df['Low'].rolling(10).min().shift(1)
        position = 0
        signals = []
        for i in range(len(df)):
            c = df['Close'].iloc[i]
            h = df['High_20'].iloc[i]
            l = df['Low_10'].iloc[i]
            if not np.isnan(h) and c > h:
                position = 1
            elif not np.isnan(l) and c < l:
                position = 0
            signals.append(position)
        df['Signal'] = signals
    elif strategy_name in ("POWER_OF_STOCKS_5EMA", "5EMA"):
        # Subasish Pani (Power of Stocks) 5 EMA Strategy
        # Alert candle: High < 5 EMA (bullish setup for long equity swing)
        # Entry trigger: when price breaks above alert candle high within 3 bars
        # Stop loss: Alert candle low
        # Target: 1:3 Reward to Risk (or close below 5 EMA)
        ema5 = close.ewm(span=5, adjust=False).mean()
        high = df['High'].astype(float)
        low = df['Low'].astype(float)

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        position = 0
        signals = []
        alert_high = 0.0
        alert_low = 0.0
        alert_bar = -99
        stop_loss = 0.0
        target_price = 0.0

        for i in range(len(df)):
            curr_c = float(close.iloc[i])
            curr_h = float(high.iloc[i])
            curr_l = float(low.iloc[i])
            curr_ema = float(ema5.iloc[i])
            curr_atr = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else (curr_h - curr_l)

            # Bullish Alert Candle: High < 5 EMA and candle size <= 2.2 * ATR
            if curr_h < curr_ema and (curr_h - curr_l) <= 2.2 * curr_atr:
                alert_high = curr_h
                alert_low = curr_l
                alert_bar = i

            if position == 0:
                if (i - alert_bar) <= 3 and alert_high > 0 and curr_h > alert_high:
                    position = 1
                    entry_est = alert_high
                    stop_loss = alert_low
                    risk = entry_est - stop_loss
                    if risk <= 0:
                        risk = curr_atr if curr_atr > 0 else 1.0
                        stop_loss = entry_est - risk
                    target_price = entry_est + (3.0 * risk)
            elif position == 1:
                # Exit on hitting stop-loss, achieving 1:3 RR target, or close breaking back below 5 EMA
                if curr_l <= stop_loss or curr_h >= target_price or curr_c < curr_ema:
                    position = 0
                    alert_high = 0.0

            signals.append(position)
        df['Signal'] = signals
    elif strategy_name in ("PATRICK_NILL_PBD", "PBD_MODEL", "PBD"):
        # Patrick Nill PBD Model Counter-Trend Swing Strategy
        # Identifies P-structure (bullish impulse followed by range) or B-structure (bearish impulse followed by range)
        # Playbook 1: Boundary Ping-Pong (Buy Range Low, Target POC / Range High)
        # Playbook 2: Breakout Continuation
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        position = 0
        signals = []
        stop_loss = 0.0
        target_price = 0.0

        for i in range(len(df)):
            if i < 20:
                signals.append(0)
                continue

            curr_c = float(close.iloc[i])
            curr_h = float(high.iloc[i])
            curr_l = float(low.iloc[i])
            curr_atr = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else (curr_h - curr_l)

            # Lookback consolidation window: 10 bars
            # Lookback impulse window: 8 bars preceding consolidation
            cons_low = float(low.iloc[i-10:i].min())
            cons_high = float(high.iloc[i-10:i].max())
            cons_mid = (cons_high + cons_low) / 2.0
            imp_start = float(close.iloc[i-18])
            imp_end = float(close.iloc[i-10])
            imp_move = (imp_end - imp_start) / imp_start * 100.0 if imp_start > 0 else 0.0

            if position == 0:
                # Setup A: Buy at Range Low in a B-Structure or P-Structure (Ping-Pong)
                if curr_l <= cons_low * 1.005 and curr_c > cons_low:
                    position = 1
                    entry_est = curr_c
                    stop_loss = cons_low - (0.5 * curr_atr)
                    risk = entry_est - stop_loss
                    if risk <= 0:
                        risk = curr_atr if curr_atr > 0 else 1.0
                        stop_loss = entry_est - risk
                    target_price = cons_high
                # Setup B: Bullish Breakout Continuation above Range High in P-Structure
                elif imp_move >= 2.0 and curr_c > cons_high:
                    position = 1
                    entry_est = curr_c
                    stop_loss = cons_mid
                    risk = entry_est - stop_loss
                    target_price = entry_est + (2.5 * risk)
            elif position == 1:
                # Exit conditions: Stop loss hit, target hit
                if curr_l <= stop_loss or curr_h >= target_price:
                    position = 0

            signals.append(position)
        df['Signal'] = signals
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    # Calculate returns (shifted 1 day to prevent lookahead bias)
    df['Position'] = df['Signal'].shift(1).fillna(0)
    df['Market_Pct_Change'] = df['Close'].pct_change().fillna(0)
    df['Strategy_Pct_Change'] = df['Position'] * df['Market_Pct_Change']

    # Compounding Equity Curve (Gross)
    df['Equity'] = initial_capital * (1.0 + df['Strategy_Pct_Change']).cumprod()
    df['Benchmark_Equity'] = initial_capital * (1.0 + df['Market_Pct_Change']).cumprod()

    # Max Drawdown Calculation
    df['Peak'] = df['Equity'].cummax()
    df['Drawdown'] = (df['Equity'] - df['Peak']) / df['Peak']
    max_drawdown_pct = round(abs(float(df['Drawdown'].min())) * 100.0, 2)

    # Trade extraction with realistic Indian taxation & brokerage modeling
    trades: List[Dict[str, Any]] = []
    in_trade = False
    entry_price = 0.0
    entry_date = ""
    current_portfolio = initial_capital
    total_taxes_and_charges = 0.0

    for i in range(1, len(df)):
        prev_pos = df['Position'].iloc[i-1]
        curr_pos = df['Position'].iloc[i]
        date = df['DateStr'].iloc[i]
        price = round(float(df['Close'].iloc[i]), 2)

        # Enter Long
        if prev_pos == 0 and curr_pos == 1:
            in_trade = True
            entry_price = price
            entry_date = date
        # Exit Long
        elif prev_pos == 1 and curr_pos == 0 and in_trade:
            # Model trade size based on current compounding capital
            trade_allocation = current_portfolio * 0.95
            shares = max(1, int(trade_allocation / entry_price))
            buy_val = shares * entry_price
            sell_val = shares * price
            gross_pnl = sell_val - buy_val
            gross_pnl_pct = round(((price - entry_price) / entry_price) * 100.0, 2)

            charges = calculate_indian_trade_charges(buy_val, sell_val)
            net_pnl = gross_pnl - charges["total_charges"]
            net_pnl_pct = round((net_pnl / buy_val) * 100.0, 2)
            total_taxes_and_charges += charges["total_charges"]
            current_portfolio += net_pnl

            trades.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": entry_price,
                "exit_price": price,
                "shares": shares,
                "gross_pnl_pct": gross_pnl_pct,
                "net_pnl_pct": net_pnl_pct,
                "pnl_pct": net_pnl_pct, # Used for consistency
                "gross_pnl_inr": round(gross_pnl, 2),
                "net_pnl_inr": round(net_pnl, 2),
                "charges_inr": charges["total_charges"],
                "charges_breakdown": charges,
                "is_win": net_pnl > 0
            })
            in_trade = False

    total_trades = len(trades)
    winning_trades = len([t for t in trades if t["is_win"]])
    win_rate_pct = round((winning_trades / total_trades * 100.0), 1) if total_trades > 0 else 0.0

    final_gross_capital = round(float(df['Equity'].iloc[-1]), 2)
    gross_return_pct = round(((final_gross_capital - initial_capital) / initial_capital) * 100.0, 2)

    final_net_capital = round(current_portfolio, 2)
    net_return_pct = round(((final_net_capital - initial_capital) / initial_capital) * 100.0, 2)
    tax_drag_pct = round(gross_return_pct - net_return_pct, 2)
    
    benchmark_final = round(float(df['Benchmark_Equity'].iloc[-1]), 2)
    benchmark_return_pct = round(((benchmark_final - initial_capital) / initial_capital) * 100.0, 2)

    # Profit Factor (Net)
    net_gains = sum([t["net_pnl_inr"] for t in trades if t["is_win"]])
    net_losses = abs(sum([t["net_pnl_inr"] for t in trades if not t["is_win"]]))
    profit_factor = round(net_gains / net_losses, 2) if net_losses > 0 else (round(net_gains, 2) if net_gains > 0 else 1.0)

    # Trade Expectancy & Edge Calculation (Freqtrade Expectancy Model)
    win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
    losing_trades = total_trades - winning_trades
    loss_rate = (losing_trades / total_trades) if total_trades > 0 else 0.0
    avg_win_inr = round(net_gains / winning_trades, 2) if winning_trades > 0 else 0.0
    avg_loss_inr = round(net_losses / losing_trades, 2) if losing_trades > 0 else 0.0
    
    trade_expectancy_inr = round((win_rate * avg_win_inr) - (loss_rate * avg_loss_inr), 2)
    expectancy_ratio = round(trade_expectancy_inr / avg_loss_inr, 2) if avg_loss_inr > 0 else (1.0 if trade_expectancy_inr > 0 else 0.0)
    edge_status = "POSITIVE_EDGE" if trade_expectancy_inr > 0 else "NEGATIVE_EDGE"

    # Risk-Adjusted Ratios (Sharpe & Sortino)
    risk_ratios = calculate_risk_adjusted_ratios(df['Strategy_Pct_Change'], risk_free_rate_annual=0.07)

    # Monte Carlo Stress-Testing
    trade_pnls = [t["net_pnl_pct"] for t in trades]
    monte_carlo = run_monte_carlo_simulation(trade_pnls, initial_capital=initial_capital, runs=500)

    # Downsampled chart series for fast rendering
    step = max(1, len(df) // 60)
    chart_series = []
    for i in range(0, len(df), step):
        chart_series.append({
            "date": df['DateStr'].iloc[i],
            "strategy": round(float(df['Equity'].iloc[i]), 2),
            "benchmark": round(float(df['Benchmark_Equity'].iloc[i]), 2)
        })

    return {
        "symbol": norm_symbol,
        "strategy": strategy_name,
        "period": period,
        "initial_capital": initial_capital,
        "final_capital": final_net_capital,
        "gross_final_capital": final_gross_capital,
        "total_return_pct": net_return_pct,
        "gross_return_pct": gross_return_pct,
        "tax_drag_pct": tax_drag_pct,
        "total_taxes_and_charges": round(total_taxes_and_charges, 2),
        "benchmark_return_pct": benchmark_return_pct,
        "outperformance_pct": round(net_return_pct - benchmark_return_pct, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "profit_factor": profit_factor,
        "trade_expectancy_inr": trade_expectancy_inr,
        "expectancy_ratio": expectancy_ratio,
        "edge_status": edge_status,
        "avg_win_inr": avg_win_inr,
        "avg_loss_inr": avg_loss_inr,
        "sharpe_ratio": risk_ratios["sharpe_ratio"],
        "sortino_ratio": risk_ratios["sortino_ratio"],
        "annualized_volatility_pct": risk_ratios["annualized_volatility_pct"],
        "monte_carlo": monte_carlo,
        "recent_trades": trades[-8:],
        "equity_curve": chart_series
    }

def run_parameter_sweep(symbol: str, period: str = "6mo", initial_capital: float = 100000.0) -> Dict[str, Any]:
    norm_symbol = normalize_indian_symbol(symbol)
    df = get_historical_bars(norm_symbol, period=period, interval="1d")
    
    if len(df) < 35:
        raise ValueError("Insufficient historical bars for parameter optimization (minimum 35 required)")

    # 70% In-Sample (Optimization) and 30% Out-of-Sample (Validation)
    split_idx = max(25, int(len(df) * 0.70))
    in_sample_df = df.iloc[:split_idx].copy()
    out_sample_df = df.iloc[split_idx:].copy()

    close_is = in_sample_df['Close']
    close_pct_change_is = close_is.pct_change().fillna(0)

    fast_periods = [9, 15, 20]
    slow_periods = [30, 50, 100]

    grid_results = []

    def simulate_ema_strategy(data_df, fast, slow, capital):
        close_s = data_df['Close']
        pct_change_s = close_s.pct_change().fillna(0)
        ema_fast = close_s.ewm(span=fast, adjust=False).mean()
        ema_slow = close_s.ewm(span=slow, adjust=False).mean()
        signal = np.where(ema_fast > ema_slow, 1, 0)
        position = pd.Series(signal, index=data_df.index).shift(1).fillna(0)
        strat_returns = position * pct_change_s

        in_trade = False
        entry_price = 0.0
        shares = 0
        trades_count = 0
        wins = 0
        current_portfolio = capital

        for i in range(len(data_df)):
            pos = position.iloc[i]
            price = float(close_s.iloc[i])

            if pos == 1 and not in_trade:
                in_trade = True
                entry_price = price
                shares = int(current_portfolio / price) if price > 0 else 0
            elif pos == 0 and in_trade:
                trades_count += 1
                buy_val = shares * entry_price
                sell_val = shares * price
                gross_pnl = sell_val - buy_val
                charges = calculate_indian_trade_charges(buy_val, sell_val, slippage_pct=0.0005)
                net_pnl = gross_pnl - charges["total_charges"]
                if net_pnl > 0:
                    wins += 1
                current_portfolio += net_pnl
                in_trade = False

        win_rate = round((wins / trades_count) * 100.0, 1) if trades_count > 0 else 0.0
        net_ret_pct = round(((current_portfolio - capital) / capital) * 100.0, 2)
        risk_metrics = calculate_risk_adjusted_ratios(strat_returns, risk_free_rate_annual=0.07)
        sharpe = risk_metrics.get("sharpe_ratio", 0.0)

        return {
            "net_return_pct": net_ret_pct,
            "win_rate_pct": win_rate,
            "total_trades": trades_count,
            "sharpe_ratio": sharpe,
            "final_portfolio": round(current_portfolio, 2)
        }

    # In-Sample Parameter Grid Sweep
    for fast in fast_periods:
        for slow in slow_periods:
            if slow <= fast:
                continue
            res_is = simulate_ema_strategy(in_sample_df, fast, slow, initial_capital)
            grid_results.append({
                "fast_ema": fast,
                "slow_ema": slow,
                "combo_label": f"{fast} / {slow} EMA",
                "net_return_pct": res_is["net_return_pct"],
                "win_rate_pct": res_is["win_rate_pct"],
                "total_trades": res_is["total_trades"],
                "sharpe_ratio": res_is["sharpe_ratio"]
            })

    # Sort grid by Sharpe descending, then net return
    grid_results.sort(key=lambda x: (x["sharpe_ratio"], x["net_return_pct"]), reverse=True)
    best = grid_results[0] if grid_results else {}

    # Out-of-Sample Validation on unseen data
    best_fast = best.get("fast_ema", 9)
    best_slow = best.get("slow_ema", 30)
    oos_res = simulate_ema_strategy(out_sample_df, best_fast, best_slow, initial_capital) if len(out_sample_df) >= 10 else {}

    is_ret = best.get("net_return_pct", 0.0)
    oos_ret = oos_res.get("net_return_pct", 0.0)

    if is_ret > 0:
        robustness_ratio = round(oos_ret / is_ret, 2)
    else:
        robustness_ratio = 1.0 if oos_ret >= 0 else 0.0

    if oos_ret > 0 and robustness_ratio >= 0.5:
        wf_verdict = "ROBUST (Strategy maintains edge on unseen data)"
    elif oos_ret > 0:
        wf_verdict = "MODERATE (Profitable out-of-sample with performance decay)"
    else:
        wf_verdict = "OVERFITTED (Strategy degraded into losses on unseen test data)"

    walk_forward = {
        "in_sample_period_bars": len(in_sample_df),
        "out_of_sample_period_bars": len(out_sample_df),
        "in_sample_return_pct": is_ret,
        "out_of_sample_return_pct": oos_ret,
        "out_of_sample_win_rate_pct": oos_res.get("win_rate_pct", 0.0),
        "out_of_sample_trades": oos_res.get("total_trades", 0),
        "robustness_ratio": robustness_ratio,
        "verdict": wf_verdict,
        "walk_forward_verdict": "ROBUST" if "ROBUST" in wf_verdict else ("MODERATE" if "MODERATE" in wf_verdict else "OVERFITTED"),
        "slippage_per_leg_pct": 0.05,
        "summary": f"In-sample return: {is_ret}%, Out-of-sample return: {oos_ret}%. Status: {wf_verdict}."
    }

    return {
        "symbol": norm_symbol,
        "period": period,
        "initial_capital": initial_capital,
        "total_combinations_tested": len(grid_results),
        "best_combination": best,
        "walk_forward_validation": walk_forward,
        "grid_results": grid_results,
        "summary": f"Optimal parameter set for {norm_symbol}: {best.get('combo_label')} delivering {best.get('net_return_pct')}% in-sample return and {oos_ret}% out-of-sample return. Status: {wf_verdict}."
    }

