import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).copy()
    loss = (-delta.where(delta < 0, 0.0)).copy()
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    for i in range(period, len(series)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period
        
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: int = 2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_fibonacci_retracements(high: float, low: float) -> Dict[str, float]:
    diff = high - low
    if diff <= 0:
        return {
            "0.0%": round(high, 2),
            "23.6%": round(low, 2),
            "38.2%": round(low, 2),
            "50.0%": round(low, 2),
            "61.8%": round(low, 2),
            "78.6%": round(low, 2),
            "100.0%": round(low, 2),
            "fib_236": round(low, 2),
            "fib_382": round(low, 2),
            "fib_500": round(low, 2),
            "fib_618": round(low, 2),
            "fib_786": round(low, 2)
        }
    f236 = round(high - (0.236 * diff), 2)
    f382 = round(high - (0.382 * diff), 2)
    f500 = round(high - (0.500 * diff), 2)
    f618 = round(high - (0.618 * diff), 2)
    f786 = round(high - (0.786 * diff), 2)
    return {
        "0.0%": round(high, 2),
        "23.6%": f236,
        "38.2%": f382,
        "50.0%": f500,
        "61.8%": f618,
        "78.6%": f786,
        "100.0%": round(low, 2),
        "fib_236": f236,
        "fib_382": f382,
        "fib_500": f500,
        "fib_618": f618,
        "fib_786": f786
    }


def detect_candlestick_patterns(df: pd.DataFrame) -> List[str]:
    if len(df) < 2 or not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
        return []
        
    patterns = []
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    open_p = float(curr['Open'])
    close_p = float(curr['Close'])
    high_p = float(curr['High'])
    low_p = float(curr['Low'])
    
    body = abs(close_p - open_p)
    candle_range = high_p - low_p
    
    prev_open = float(prev['Open'])
    prev_close = float(prev['Close'])
    prev_body = abs(prev_close - prev_open)
    
    # 1. Hammer: small upper body, lower shadow >= 2x body, small upper shadow
    if candle_range > 0 and body > 0:
        lower_shadow = min(open_p, close_p) - low_p
        upper_shadow = high_p - max(open_p, close_p)
        if lower_shadow >= (1.8 * body) and upper_shadow <= (0.5 * body):
            patterns.append("Hammer (Bullish Reversal)")
            
    # 2. Bullish Engulfing: prior candle red, current candle green and engulfs prior body
    if prev_close < prev_open and close_p > open_p:
        if open_p <= prev_close and close_p >= prev_open and body >= prev_body:
            patterns.append("Bullish Engulfing")
            
    # 3. Doji: body <= 10% of total candle range
    if candle_range > 0 and body <= (0.10 * candle_range):
        patterns.append("Doji (Absorption/Indecision)")
        
    return patterns

def analyze_technical_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < 30:
        raise ValueError("Insufficient data points for technical analysis (need at least 30 bars)")
        
    close = df['Close']
    current_price = float(close.iloc[-1])
    
    # EMAs
    ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    ema_200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else float(close.ewm(span=len(df), adjust=False).mean().iloc[-1])
    
    # RSI
    rsi_series = calculate_rsi(close, 14)
    current_rsi = float(rsi_series.iloc[-1])
    
    # MACD
    macd_line, sig_line, macd_hist = calculate_macd(close)
    current_macd = float(macd_line.iloc[-1])
    current_signal = float(sig_line.iloc[-1])
    current_hist = float(macd_hist.iloc[-1])
    
    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(close, 20, 2)
    current_bb_upper = float(bb_upper.iloc[-1])
    current_bb_mid = float(bb_mid.iloc[-1])
    current_bb_lower = float(bb_lower.iloc[-1])
    
    # ATR
    atr_series = calculate_atr(df, 14)
    current_atr = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else (current_price * 0.02)
    
    # Volume analysis & Relative Volume (RVOL)
    avg_vol_20 = float(df['Volume'].rolling(20).mean().iloc[-1]) if 'Volume' in df and len(df) >= 20 else float(df['Volume'].mean()) if 'Volume' in df else 0.0
    current_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df else 0.0
    rvol_20d = round(current_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0
    
    if rvol_20d >= 2.0:
        volume_status = "SURGE"
        volume_meaning = "High volume surge (> 2.0x 20-day average) indicating institutional activity"
    elif rvol_20d >= 1.3:
        volume_status = "ABOVE_AVERAGE"
        volume_meaning = "Above average volume indicating healthy participation"
    elif rvol_20d >= 0.8:
        volume_status = "NORMAL"
        volume_meaning = "Normal volume matching historical trading baseline"
    else:
        volume_status = "LOW"
        volume_meaning = "Low volume below 20-day average indicating low participation or consolidation"

    volume_surge = rvol_20d >= 1.5
    
    # Pivot points (Support / Resistance from last 20 sessions)
    recent_high = float(df['High'].tail(20).max())
    recent_low = float(df['Low'].tail(20).min())
    pivot = (recent_high + recent_low + current_price) / 3.0
    resistance_1 = (2 * pivot) - recent_low
    support_1 = (2 * pivot) - recent_high
    
    # Signal Scoring
    bullish_factors = []
    bearish_factors = []
    
    if current_price > ema_20:
        bullish_factors.append("Price above 20 EMA (Short-term momentum)")
    else:
        bearish_factors.append("Price below 20 EMA (Short-term weakness)")
        
    if current_price > ema_50:
        bullish_factors.append("Price above 50 EMA (Medium-term uptrend)")
    else:
        bearish_factors.append("Price below 50 EMA (Medium-term downtrend)")
        
    if current_price > ema_200:
        bullish_factors.append("Price above 200 EMA (Long-term bull regime)")
    else:
        bearish_factors.append("Price below 200 EMA (Long-term bear regime)")
        
    if current_rsi < 30:
        bullish_factors.append(f"RSI oversold ({current_rsi:.1f}) - potential reversal")
    elif current_rsi > 70:
        bearish_factors.append(f"RSI overbought ({current_rsi:.1f}) - caution on fresh longs")
    elif current_rsi > 50:
        bullish_factors.append(f"RSI positive momentum ({current_rsi:.1f})")
    else:
        bearish_factors.append(f"RSI sluggish momentum ({current_rsi:.1f})")
        
    if current_hist > 0:
        bullish_factors.append("MACD histogram positive")
    else:
        bearish_factors.append("MACD histogram negative")
        
    if volume_surge:
        bullish_factors.append("Volume surge detected (> 1.5x 20-day average)")
        
    # Candlestick patterns
    candlestick_patterns = detect_candlestick_patterns(df)
    for pat in candlestick_patterns:
        if "Hammer" in pat or "Bullish Engulfing" in pat:
            bullish_factors.append(f"Candlestick reversal signal: {pat}")
            
    # Fibonacci Retracements (from 60-day or available swing)
    lookback_bars = min(len(df), 60)
    swing_high_60d = float(df['High'].tail(lookback_bars).max())
    swing_low_60d = float(df['Low'].tail(lookback_bars).min())
    fib_levels = calculate_fibonacci_retracements(swing_high_60d, swing_low_60d)
    
    # Check if price is within 1.5% of key Fibonacci pullback support
    fib_618 = fib_levels["fib_618"]
    fib_500 = fib_levels["fib_500"]
    if current_price > 0 and abs(current_price - fib_618) / current_price <= 0.018:
        bullish_factors.append(f"Price at Fibonacci 61.8% Golden Pocket support (INR {fib_618})")
    elif current_price > 0 and abs(current_price - fib_500) / current_price <= 0.018:
        bullish_factors.append(f"Price at Fibonacci 50.0% median retracement support (INR {fib_500})")
        
    score = len(bullish_factors) - len(bearish_factors)
    if score >= 2:
        trend = "BULLISH"
    elif score <= -2:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
        
    return {
        "current_price": round(current_price, 2),
        "trend": trend,
        "score": score,
        "rsi": round(current_rsi, 2),
        "macd": {
            "macd": round(current_macd, 2),
            "signal": round(current_signal, 2),
            "histogram": round(current_hist, 2)
        },
        "emas": {
            "ema_20": round(ema_20, 2),
            "ema_50": round(ema_50, 2),
            "ema_200": round(ema_200, 2)
        },
        "bollinger": {
            "upper": round(current_bb_upper, 2),
            "middle": round(current_bb_mid, 2),
            "lower": round(current_bb_lower, 2)
        },
        "levels": {
            "support": round(support_1, 2),
            "resistance": round(resistance_1, 2),
            "recent_high_20d": round(recent_high, 2),
            "recent_low_20d": round(recent_low, 2),
            "swing_high_60d": round(swing_high_60d, 2),
            "swing_low_60d": round(swing_low_60d, 2),
            "atr": round(current_atr, 2)
        },
        "candlestick_patterns": candlestick_patterns,
        "fibonacci": fib_levels,
        "volume": {
            "current_volume": int(current_vol),
            "avg_volume_20d": int(avg_vol_20),
            "rvol_20d": rvol_20d,
            "status": volume_status,
            "meaning": volume_meaning
        },
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors
    }
