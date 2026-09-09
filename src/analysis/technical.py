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
            "atr": round(current_atr, 2)
        },
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
