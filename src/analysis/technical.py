import pandas as pd
import numpy as np
from typing import Dict, Any, List
from src.analysis.order_flow import analyze_order_flow
from src.analysis.volatility_regimes import analyze_volatility_regime

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
    
    if candle_range > 0 and body > 0:
        lower_shadow = min(open_p, close_p) - low_p
        upper_shadow = high_p - max(open_p, close_p)
        
        # 1. Hammer: small upper body, lower shadow >= 1.8x body, small upper shadow
        if lower_shadow >= (1.8 * body) and upper_shadow <= (0.25 * candle_range):
            patterns.append("Hammer (Bullish Reversal)")
            
        # 2. Shooting Star: small lower body, upper shadow >= 1.8x body, small lower shadow
        if upper_shadow >= (1.8 * body) and lower_shadow <= (0.25 * candle_range):
            patterns.append("Shooting Star (Bearish Reversal)")
            
    # 3. Bullish Engulfing: prior red, current green and engulfs prior body
    if prev_close < prev_open and close_p > open_p:
        if open_p <= prev_close and close_p >= prev_open and body >= prev_body:
            patterns.append("Bullish Engulfing")

    # 4. Bearish Engulfing: prior green, current red and engulfs prior body
    if prev_close > prev_open and close_p < open_p:
        if open_p >= prev_close and close_p <= prev_open and body >= prev_body:
            patterns.append("Bearish Engulfing")
            
    # 5. Doji: body <= 10% of total candle range
    if candle_range > 0 and body <= (0.10 * candle_range):
        patterns.append("Doji (Absorption/Indecision)")

    # 6. Multi-bar Morning Star & Evening Star (requires 3 bars)
    if len(df) >= 3:
        bar2_ago = df.iloc[-3]
        b2_open = float(bar2_ago['Open'])
        b2_close = float(bar2_ago['Close'])
        b2_body = abs(b2_close - b2_open)
        
        # Morning Star: large red -> small body -> strong green recovering >= 50% of bar 2
        if b2_close < b2_open and b2_body > 0:
            if prev_body <= (0.4 * b2_body) and close_p > open_p:
                if close_p >= (b2_close + 0.5 * b2_body):
                    patterns.append("Morning Star (Bullish Reversal)")

        # Evening Star: large green -> small body -> strong red piercing >= 50% of bar 2
        if b2_close > b2_open and b2_body > 0:
            if prev_body <= (0.4 * b2_body) and close_p < open_p:
                if close_p <= (b2_close - 0.5 * b2_body):
                    patterns.append("Evening Star (Bearish Reversal)")
        
    return patterns

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    if len(df) < (period * 2):
        return {"adx": 20.0, "plus_di": 20.0, "minus_di": 20.0, "trend_strength": "WEAK", "is_trending": False, "directional_bias": "NEUTRAL"}

    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr_smooth = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_smooth.replace(0, np.nan))
    minus_di = 100.0 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_smooth.replace(0, np.nan))

    dx = 100.0 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().fillna(20.0)

    curr_adx = float(adx.iloc[-1])
    curr_plus_di = float(plus_di.iloc[-1])
    curr_minus_di = float(minus_di.iloc[-1])

    if curr_adx >= 35.0:
        strength = "STRONG_TREND"
    elif curr_adx >= 25.0:
        strength = "TRENDING"
    elif curr_adx >= 20.0:
        strength = "MODERATE"
    else:
        strength = "WEAK_CHOP"

    return {
        "adx": round(curr_adx, 2),
        "plus_di": round(curr_plus_di, 2),
        "minus_di": round(curr_minus_di, 2),
        "trend_strength": strength,
        "is_trending": curr_adx >= 25.0,
        "directional_bias": "BULLISH" if curr_plus_di > curr_minus_di else "BEARISH"
    }

def calculate_cpr(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < 2 or not all(col in df.columns for col in ['High', 'Low', 'Close']):
        return {"pivot": 0.0, "tc": 0.0, "bc": 0.0, "width_pct": 0.0, "regime": "AVERAGE_CPR", "price_position": "INSIDE_CPR"}

    prior = df.iloc[-2]
    p_high = float(prior['High'])
    p_low = float(prior['Low'])
    p_close = float(prior['Close'])

    pivot = (p_high + p_low + p_close) / 3.0
    bc = (p_high + p_low) / 2.0
    tc = (2.0 * pivot) - bc

    top_cpr = max(tc, bc)
    bottom_cpr = min(tc, bc)
    width_pct = abs(tc - bc) / pivot * 100.0 if pivot > 0 else 0.0

    curr_close = float(df['Close'].iloc[-1])

    if width_pct <= 0.35:
        cpr_type = "NARROW_CPR (Breakout Candidate)"
    elif width_pct >= 0.90:
        cpr_type = "WIDE_CPR (Range-bound Day Expected)"
    else:
        cpr_type = "AVERAGE_CPR"

    if curr_close > top_cpr:
        position = "ABOVE_CPR (Bullish Bias)"
    elif curr_close < bottom_cpr:
        position = "BELOW_CPR (Bearish Bias)"
    else:
        position = "INSIDE_CPR (Consolidation Zone)"

    return {
        "pivot": round(pivot, 2),
        "tc": round(top_cpr, 2),
        "bc": round(bottom_cpr, 2),
        "width_pct": round(width_pct, 2),
        "regime": cpr_type,
        "price_position": position
    }

def calculate_stoch_rsi(series: pd.Series, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3) -> Dict[str, Any]:
    rsi = calculate_rsi(series, rsi_period)
    rsi_low = rsi.rolling(window=stoch_period).min()
    rsi_high = rsi.rolling(window=stoch_period).max()

    denom = (rsi_high - rsi_low).replace(0, np.nan)
    stoch = ((rsi - rsi_low) / denom) * 100.0
    stoch = stoch.fillna(50.0)

    k = stoch.rolling(window=k_period).mean().fillna(50.0)
    d = k.rolling(window=d_period).mean().fillna(50.0)

    curr_k = float(k.iloc[-1])
    curr_d = float(d.iloc[-1])

    if curr_k < 25.0 and curr_k > curr_d:
        status = "OVERSOLD_BULLISH_CROSS"
    elif curr_k > 75.0 and curr_k < curr_d:
        status = "OVERBOUGHT_BEARISH_CROSS"
    elif curr_k > 50.0:
        status = "BULLISH_ZONE"
    else:
        status = "BEARISH_ZONE"

    return {
        "k": round(curr_k, 2),
        "d": round(curr_d, 2),
        "status": status
    }

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
        if "Hammer" in pat or "Bullish Engulfing" in pat or "Morning Star" in pat:
            bullish_factors.append(f"Candlestick bullish reversal signal: {pat}")
        elif "Shooting Star" in pat or "Bearish Engulfing" in pat or "Evening Star" in pat:
            bearish_factors.append(f"Candlestick bearish reversal signal: {pat}")
            
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

    # ADX Trend Strength & Directional Movement
    adx_info = calculate_adx(df, 14)
    if adx_info.get("is_trending"):
        if adx_info.get("directional_bias") == "BULLISH":
            bullish_factors.append(f"ADX confirms trend strength ({adx_info['adx']}) with Bullish Directional Bias")
        else:
            bearish_factors.append(f"ADX confirms trend strength ({adx_info['adx']}) with Bearish Directional Bias")
    elif adx_info.get("trend_strength") == "WEAK_CHOP":
        bearish_factors.append(f"ADX signals low momentum chop ({adx_info['adx']}) - consolidation range")

    # Central Pivot Range (CPR)
    cpr_info = calculate_cpr(df)
    if "ABOVE_CPR" in cpr_info.get("price_position", ""):
        bullish_factors.append(f"Price above Central Pivot Range (CPR Pivot: INR {cpr_info['pivot']})")
    elif "BELOW_CPR" in cpr_info.get("price_position", ""):
        bearish_factors.append(f"Price below Central Pivot Range (CPR Pivot: INR {cpr_info['pivot']})")
    
    if "NARROW_CPR" in cpr_info.get("regime", ""):
        bullish_factors.append(f"Narrow CPR detected ({cpr_info['width_pct']}%) - high breakout probability")

    # Stochastic RSI
    stoch_rsi = calculate_stoch_rsi(close, 14, 14, 3, 3)
    if stoch_rsi.get("status") == "OVERSOLD_BULLISH_CROSS":
        bullish_factors.append(f"Stochastic RSI oversold bullish crossover (%K: {stoch_rsi['k']})")
    elif stoch_rsi.get("status") == "OVERBOUGHT_BEARISH_CROSS":
        bearish_factors.append(f"Stochastic RSI overbought bearish crossover (%K: {stoch_rsi['k']})")
        
    # Order Flow & Smart Money Concepts
    order_flow = analyze_order_flow(df)
    volatility_regime = analyze_volatility_regime(df)

    if order_flow.get("verdict") == "ACCUMULATION":
        bullish_factors.append(f"Order Flow: Institutional accumulation detected (Score: {order_flow.get('order_flow_score')}/100)")
    elif order_flow.get("verdict") == "DISTRIBUTION":
        bearish_factors.append(f"Order Flow: Institutional distribution detected (Score: {order_flow.get('order_flow_score')}/100)")

    ttm = volatility_regime.get("ttm_squeeze", {})
    if ttm.get("squeeze_fired"):
        if "BULLISH" in ttm.get("momentum_direction", ""):
            bullish_factors.append("TTM Squeeze FIRED with Bullish Expansion")
        else:
            bearish_factors.append("TTM Squeeze FIRED with Bearish Expansion")
    elif ttm.get("squeeze_on"):
        bullish_factors.append("TTM Squeeze ON (Energy compression coiling)")

    st = volatility_regime.get("supertrend", {})
    if st.get("direction") == "BULLISH":
        bullish_factors.append(f"Supertrend BULLISH (Trailing Stop: INR {st.get('supertrend_price')})")
    elif st.get("direction") == "BEARISH":
        bearish_factors.append(f"Supertrend BEARISH (Resistance: INR {st.get('supertrend_price')})")

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
        "adx": adx_info,
        "cpr": cpr_info,
        "stoch_rsi": stoch_rsi,
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
        "order_flow": order_flow,
        "volatility_regime": volatility_regime,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors
    }

def calculate_donchian_channel(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
    """
    Richard Dennis / Ed Seykota Donchian Channel.
    N-period highest high and lowest low. Breakout above upper = long signal.
    System 1: 20-day. System 2: 55-day.
    """
    if len(df) < period:
        price = float(df['Close'].iloc[-1]) if len(df) > 0 else 0.0
        return {"upper": price, "lower": price, "mid": price, "breakout": "NONE", "channel_width_pct": 0.0}

    upper = float(df['High'].tail(period).max())
    lower = float(df['Low'].tail(period).min())
    mid = round((upper + lower) / 2.0, 2)
    current_price = float(df['Close'].iloc[-1])
    channel_width_pct = round((upper - lower) / mid * 100.0, 2) if mid > 0 else 0.0

    if current_price >= upper * 0.998:
        breakout = "BULLISH_BREAKOUT"
    elif current_price <= lower * 1.002:
        breakout = "BEARISH_BREAKDOWN"
    elif current_price > mid:
        breakout = "UPPER_HALF"
    else:
        breakout = "LOWER_HALF"

    return {
        "upper": round(upper, 2),
        "lower": round(lower, 2),
        "mid": mid,
        "breakout": breakout,
        "channel_width_pct": channel_width_pct,
        "period": period
    }


def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """
    Larry Williams %R oscillator.
    %R = -100 × (Highest High − Close) / (Highest High − Lowest Low)
    Below -80: oversold (potential reversal long). Above -20: overbought (potential reversal short).
    Williams trade rule: enter long when %R crosses above -80 after being below -80 for at least 2 bars.
    """
    if len(df) < period:
        return {"williams_r": -50.0, "status": "NEUTRAL", "signal": "NONE"}

    hh = df['High'].tail(period).max()
    ll = df['Low'].tail(period).min()
    close = float(df['Close'].iloc[-1])

    denom = hh - ll
    wr = -100.0 * (hh - close) / denom if denom > 0 else -50.0
    wr = round(wr, 2)

    # Signal: cross from oversold / overbought
    if len(df) >= period + 1:
        hh_prev = df['High'].iloc[-(period+1):-1].max()
        ll_prev = df['Low'].iloc[-(period+1):-1].min()
        close_prev = float(df['Close'].iloc[-2])
        denom_prev = hh_prev - ll_prev
        wr_prev = -100.0 * (hh_prev - close_prev) / denom_prev if denom_prev > 0 else -50.0
    else:
        wr_prev = wr

    if wr > -80 and wr_prev <= -80:
        signal = "BULLISH_CROSS_OVERSOLD"
    elif wr < -20 and wr_prev >= -20:
        signal = "BEARISH_CROSS_OVERBOUGHT"
    else:
        signal = "NONE"

    if wr <= -80:
        status = "OVERSOLD"
    elif wr >= -20:
        status = "OVERBOUGHT"
    else:
        status = "NEUTRAL"

    return {
        "williams_r": wr,
        "status": status,
        "signal": signal,
        "period": period
    }


def calculate_india_vix_regime(india_vix: float) -> Dict[str, Any]:
    """
    PR Sundar's India VIX regime classifier for options premium selling.
    VIX < 13: Low vol — premiums are thin, avoid selling.
    VIX 13-18: Sweet spot — sell strangles at 0.20-0.25 delta.
    VIX 18-25: Elevated — sell only if IV rank > 50, tighten strikes.
    VIX > 25: Crisis mode — do NOT sell naked options; use defined risk spreads only.
    """
    if india_vix < 13:
        regime = "LOW_VOL"
        action = "AVOID_SELLING — Premiums too thin for worthwhile risk-reward"
        size_multiplier = 0.0
        delta_target = None
    elif india_vix < 18:
        regime = "SWEET_SPOT"
        action = "SELL_STRANGLES — Optimal premium selling zone"
        size_multiplier = 1.0
        delta_target = 0.22
    elif india_vix < 25:
        regime = "ELEVATED"
        action = "REDUCED_SIZE_SELL — Tighten strikes; sell only if IV rank > 50"
        size_multiplier = 0.5
        delta_target = 0.15
    else:
        regime = "CRISIS"
        action = "NO_NAKED_SELLING — Use defined-risk spreads only (Iron Condor / Bull Put Spread)"
        size_multiplier = 0.0
        delta_target = None

    return {
        "india_vix": round(india_vix, 2),
        "regime": regime,
        "recommended_action": action,
        "position_size_multiplier": size_multiplier,
        "recommended_delta": delta_target,
        "target_exit_pct": 0.35 if india_vix < 25 else None
    }


def calculate_5ema_setup(df: pd.DataFrame, target_rr: float = 3.0) -> Dict[str, Any]:
    """
    Subasish Pani (Power of Stocks) 5 EMA Mean-Reversion Strategy.
    Rule 1 (The Non-Touch Alert Candle):
      - Bearish/Short Alert: Candle's Low > 5 EMA (No part of candle touches the 5 EMA from above).
      - Bullish/Long Alert: Candle's High < 5 EMA (No part of candle touches the 5 EMA from below).
    Rule 2 (The Breakout Execution Trigger):
      - Sell Trigger: When the low of the Bearish Alert candle is broken by subsequent candle.
      - Buy Trigger: When the high of the Bullish Alert candle is broken by subsequent candle.
    Rule 3 (Stop-Loss and Target):
      - Stop-Loss: Alert candle's extreme (High for Short, Low for Long).
      - Target: Minimum 1:3 Reward-to-Risk ratio (often runs to 1:4).
    Rule 4 (Candle Size Filter):
      - If Alert Candle range > 2.2x ATR, skip because risk is excessive.
    """
    if len(df) < 10 or not all(c in df.columns for c in ['Open', 'High', 'Low', 'Close']):
        return {
            "strategy": "5_EMA_POWER_OF_STOCKS",
            "status": "INSUFFICIENT_DATA",
            "setup": "NO_SETUP"
        }

    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    ema5 = close.ewm(span=5, adjust=False).mean()
    curr_ema5 = float(ema5.iloc[-1])
    curr_close = float(close.iloc[-1])
    curr_high = float(high.iloc[-1])
    curr_low = float(low.iloc[-1])

    # 14-period ATR for candle size validation
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean()) if len(df) >= 14 else (curr_high - curr_low)

    setup = "NO_SETUP"
    action = "NONE"
    alert_candle = None
    trigger_price = None
    stop_loss = None
    target_1 = None
    target_2 = None
    target_3 = None
    risk = 0.0

    # Scan the previous bar (iloc[-2]) and bar before that (iloc[-3]) for alert candles
    for i in [-2, -3]:
        bar_high = float(high.iloc[i])
        bar_low = float(low.iloc[i])
        bar_ema = float(ema5.iloc[i])
        bar_range = bar_high - bar_low

        # Bearish Alert (Low > 5 EMA)
        if bar_low > bar_ema:
            is_broken = curr_low < bar_low
            is_pending = not is_broken and curr_close < bar_high
            alert_size_ratio = round(bar_range / atr, 2) if atr > 0 else 1.0
            is_valid_size = alert_size_ratio <= 2.2

            if is_broken and is_valid_size:
                setup = "5EMA_BEARISH_BREAKOUT_ACTIVE"
                action = "SELL_SHORT"
                alert_candle = {
                    "bar_offset": i,
                    "high": round(bar_high, 2),
                    "low": round(bar_low, 2),
                    "ema5": round(bar_ema, 2),
                    "size_vs_atr": alert_size_ratio
                }
                trigger_price = round(bar_low - (0.0005 * bar_low), 2)
                stop_loss = round(bar_high, 2)
                risk = round(stop_loss - trigger_price, 2)
                target_1 = round(trigger_price - (2.0 * risk), 2)
                target_2 = round(trigger_price - (3.0 * risk), 2)
                target_3 = round(trigger_price - (4.0 * risk), 2)
                break
            elif is_pending and is_valid_size:
                setup = "5EMA_BEARISH_ALERT_PENDING"
                action = "WATCH_FOR_BREAKDOWN"
                alert_candle = {
                    "bar_offset": i,
                    "high": round(bar_high, 2),
                    "low": round(bar_low, 2),
                    "ema5": round(bar_ema, 2),
                    "size_vs_atr": alert_size_ratio
                }
                trigger_price = round(bar_low, 2)
                stop_loss = round(bar_high, 2)
                risk = round(stop_loss - trigger_price, 2)
                target_1 = round(trigger_price - (2.0 * risk), 2)
                target_2 = round(trigger_price - (3.0 * risk), 2)
                target_3 = round(trigger_price - (4.0 * risk), 2)
                break

        # Bullish Alert (High < 5 EMA)
        elif bar_high < bar_ema:
            is_broken = curr_high > bar_high
            is_pending = not is_broken and curr_close > bar_low
            alert_size_ratio = round(bar_range / atr, 2) if atr > 0 else 1.0
            is_valid_size = alert_size_ratio <= 2.2

            if is_broken and is_valid_size:
                setup = "5EMA_BULLISH_BREAKOUT_ACTIVE"
                action = "BUY_LONG"
                alert_candle = {
                    "bar_offset": i,
                    "high": round(bar_high, 2),
                    "low": round(bar_low, 2),
                    "ema5": round(bar_ema, 2),
                    "size_vs_atr": alert_size_ratio
                }
                trigger_price = round(bar_high + (0.0005 * bar_high), 2)
                stop_loss = round(bar_low, 2)
                risk = round(trigger_price - stop_loss, 2)
                target_1 = round(trigger_price + (2.0 * risk), 2)
                target_2 = round(trigger_price + (3.0 * risk), 2)
                target_3 = round(trigger_price + (4.0 * risk), 2)
                break
            elif is_pending and is_valid_size:
                setup = "5EMA_BULLISH_ALERT_PENDING"
                action = "WATCH_FOR_BREAKOUT"
                alert_candle = {
                    "bar_offset": i,
                    "high": round(bar_high, 2),
                    "low": round(bar_low, 2),
                    "ema5": round(bar_ema, 2),
                    "size_vs_atr": alert_size_ratio
                }
                trigger_price = round(bar_high, 2)
                stop_loss = round(bar_low, 2)
                risk = round(trigger_price - stop_loss, 2)
                target_1 = round(trigger_price + (2.0 * risk), 2)
                target_2 = round(trigger_price + (3.0 * risk), 2)
                target_3 = round(trigger_price + (4.0 * risk), 2)
                break

    # If current candle itself is forming an alert candle (not yet closed)
    if setup == "NO_SETUP":
        if curr_low > curr_ema5:
            setup = "5EMA_FORMING_BEARISH_ALERT"
            action = "WAIT_FOR_CANDLE_CLOSE"
            trigger_price = round(curr_low, 2)
            stop_loss = round(curr_high, 2)
        elif curr_high < curr_ema5:
            setup = "5EMA_FORMING_BULLISH_ALERT"
            action = "WAIT_FOR_CANDLE_CLOSE"
            trigger_price = round(curr_high, 2)
            stop_loss = round(curr_low, 2)

    return {
        "strategy": "5_EMA_POWER_OF_STOCKS",
        "mentor": "Subasish Pani (Power of Stocks)",
        "current_price": round(curr_close, 2),
        "ema_5": round(curr_ema5, 2),
        "atr_14": round(atr, 2),
        "setup": setup,
        "action": action,
        "is_active": "ACTIVE" in setup,
        "is_pending": "PENDING" in setup or "FORMING" in setup,
        "trigger_price": trigger_price,
        "stop_loss": stop_loss,
        "risk_per_share": risk,
        "target_1_2rr": target_1,
        "target_1_3rr": target_2,
        "target_1_4rr": target_3,
        "reward_to_risk": target_rr if risk > 0 else 0.0,
        "alert_candle": alert_candle,
        "rule_summary": (
            "Subasish Pani 5 EMA Setup: Identify candle with zero touch of 5 EMA. "
            "Enter on breakout of alert candle boundary. Target 1:3 minimum RR. Hard SL at opposite extreme."
        )
    }
