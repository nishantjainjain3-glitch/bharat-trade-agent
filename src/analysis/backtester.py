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
        "losing_trades": total_trades - winning_trades,
        "profit_factor": profit_factor,
        "sharpe_ratio": risk_ratios["sharpe_ratio"],
        "sortino_ratio": risk_ratios["sortino_ratio"],
        "annualized_volatility_pct": risk_ratios["annualized_volatility_pct"],
        "monte_carlo": monte_carlo,
        "recent_trades": trades[-8:],
        "equity_curve": chart_series
    }
