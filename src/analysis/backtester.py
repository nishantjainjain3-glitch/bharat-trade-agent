import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.data.market_data import get_historical_bars, normalize_indian_symbol
from src.analysis.technical import calculate_rsi, calculate_macd

def backtest_strategy(
    symbol: str, 
    strategy_name: str = "EMA_CROSS", 
    period: str = "2y", 
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Executes a vectorized backtest on historical daily bars for Indian stocks.
    Supported strategies:
    - 'EMA_CROSS': 20 EMA crosses 50 EMA (Classic Trend Following)
    - 'RSI_REVERSAL': Buy when RSI < 35, Exit when RSI > 65 (Mean Reversion)
    - 'BREAKOUT': 20-day High Breakout with 10-day Low Exit
    """
    norm_symbol = normalize_indian_symbol(symbol)
    df = get_historical_bars(norm_symbol, period=period, interval="1d")
    if len(df) < 60:
        raise ValueError(f"Insufficient historical data for {norm_symbol} ({len(df)} bars)")

    df['Close'] = df['Close'].astype(float)
    df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
    close = df['Close']

    # Generate signals
    df['Signal'] = 0  # 1 = Long, 0 = Flat

    if strategy_name == "EMA_CROSS":
        df['EMA_Fast'] = close.ewm(span=20, adjust=False).mean()
        df['EMA_Slow'] = close.ewm(span=50, adjust=False).mean()
        df['Signal'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, 0)

    elif strategy_name == "RSI_REVERSAL":
        df['RSI'] = calculate_rsi(close, period=14)
        # Position holds between oversold trigger and overbought exit
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

    # Calculate returns (shift signal by 1 day to prevent lookahead bias)
    df['Position'] = df['Signal'].shift(1).fillna(0)
    df['Market_Pct_Change'] = df['Close'].pct_change().fillna(0)
    df['Strategy_Pct_Change'] = df['Position'] * df['Market_Pct_Change']

    # Compounding Equity Curve
    df['Equity'] = initial_capital * (1.0 + df['Strategy_Pct_Change']).cumprod()
    df['Benchmark_Equity'] = initial_capital * (1.0 + df['Market_Pct_Change']).cumprod()

    # Max Drawdown Calculation
    df['Peak'] = df['Equity'].cummax()
    df['Drawdown'] = (df['Equity'] - df['Peak']) / df['Peak']
    max_drawdown_pct = round(abs(float(df['Drawdown'].min())) * 100.0, 2)

    # Trade extraction
    trades: List[Dict[str, Any]] = []
    in_trade = False
    entry_price = 0.0
    entry_date = ""

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
            pnl_pct = round(((price - entry_price) / entry_price) * 100.0, 2)
            trades.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": entry_price,
                "exit_price": price,
                "pnl_pct": pnl_pct,
                "is_win": pnl_pct > 0
            })
            in_trade = False

    total_trades = len(trades)
    winning_trades = len([t for t in trades if t["is_win"]])
    win_rate_pct = round((winning_trades / total_trades * 100.0), 1) if total_trades > 0 else 0.0

    final_capital = round(float(df['Equity'].iloc[-1]), 2)
    total_return_pct = round(((final_capital - initial_capital) / initial_capital) * 100.0, 2)
    
    benchmark_final = round(float(df['Benchmark_Equity'].iloc[-1]), 2)
    benchmark_return_pct = round(((benchmark_final - initial_capital) / initial_capital) * 100.0, 2)

    # Profit Factor
    gains = sum([t["pnl_pct"] for t in trades if t["is_win"]])
    losses = abs(sum([t["pnl_pct"] for t in trades if not t["is_win"]]))
    profit_factor = round(gains / losses, 2) if losses > 0 else (round(gains, 2) if gains > 0 else 1.0)

    # Chart data (downsampled for fast mobile rendering)
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
        "final_capital": final_capital,
        "total_return_pct": total_return_pct,
        "benchmark_return_pct": benchmark_return_pct,
        "outperformance_pct": round(total_return_pct - benchmark_return_pct, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": total_trades - winning_trades,
        "profit_factor": profit_factor,
        "recent_trades": trades[-8:],
        "equity_curve": chart_series
    }
