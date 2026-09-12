# Master Trader Knowledge Base

This document captures the complete trading methodology of the world's most successful
traders and India's top educators. Each entry covers trading style, entry/exit rules,
key indicators, Pine Script / Python strategy references, and social handles.

---

## PART 1 — WORLD'S BEST TRADERS

---

### 1. George Soros — Global Macro / Reflexivity

**Country**: Hungary / USA  
**Style**: Global Macro, High-Leverage Asymmetric Bets

**Core Theory — Reflexivity**:
Markets are not efficient because participants' perceptions alter the very fundamentals
they are trying to assess. When a trend reinforces itself through sentiment feedback,
a macro bet can generate outsized returns before reality snaps back.

**Strategy Rules**:
- Identify macro imbalances (currency pegs, credit bubbles, policy distortions).
- Size up when the asymmetry is clear: limited downside, massive upside.
- Do not average into losers. If the thesis is wrong, exit fast.
- Use leverage aggressively during high-conviction phases.

**Classic Trade**: Shorted the British Pound in 1992, made ~$1 billion in a single day
when the Bank of England was forced to withdraw from the ERM.

**Performance**: Quantum Fund averaged ~30% annualised return over multiple decades.

**Pine Script / Python**: No direct scripts. Macro analysis uses fundamental inputs.

**Social**: N/A

---

### 2. Paul Tudor Jones — Contrarian Macro / Elliott Wave

**Country**: USA  
**Style**: Global Macro, Contrarian Swing

**Strategy Rules**:
- 200-day Simple Moving Average is the primary defence line for any position.
  If price is below the 200 SMA, he will not hold long positions.
- Uses Elliott Wave theory to anticipate inflection points in trends.
- "Losers average losers." Never add to a losing position.
- Always knows his exit price before entering. Max loss per trade is defined.
- Preserves capital as the number-one priority.

**Performance**: Predicted and profited from the 1987 crash (+62% in October 1987).

**Key Pine Script**:
```pinescript
//@version=5
indicator("PTJ 200 SMA Defence", overlay=true)
sma200 = ta.sma(close, 200)
plot(sma200, color=color.red, linewidth=2, title="200 SMA Defence")
bgcolor(close < sma200 ? color.new(color.red, 90) : color.new(color.green, 90))
```

**Social**: N/A

---

### 3. Stanley Druckenmiller — Concentrated Macro Momentum

**Country**: USA  
**Style**: Global Macro + Momentum, Trend Following

**Strategy Rules**:
- Top-down macro analysis first. Identify the dominant economic theme
  (Fed policy, credit cycles, commodity supercycles).
- When conviction is extreme, concentrate: size up heavily rather than spreading
  across 20 positions.
- Monitor liquidity: rising central bank liquidity = bull mode; tightening = defensive.
- Reverse quickly when wrong. Ego has no place in position management.
- Entry is often on momentum confirmation, not at bottoms.

**Performance**: ~30% average annual return over 30 years at Duquesne.
Zero down years.

**Key Concept for India**: Apply to RBI rate cycle and FII/DII flow data.
When RBI cuts rates and FII flows turn positive, concentrate longs in rate-sensitive
sectors (banks, real estate, auto).

**Social**: N/A

---

### 4. Mark Minervini — VCP (Volatility Contraction Pattern)

**Country**: USA  
**Style**: Growth Momentum Swing Trading

**SEPA Trend Template (all 4 must be true to consider)**:
1. Price above the 150-day and 200-day SMA.
2. 150-day SMA above the 200-day SMA.
3. 200-day SMA trending up for at least 4–5 months.
4. 50-day SMA above both the 150-day and 200-day SMA.
5. Price at least 25% above its 52-week low.
6. Price within 25% of its 52-week high.

**VCP Entry Rules**:
- After a big up move, stock contracts in price and volume through a series of
  progressively tighter pivots (each contraction 30–50% smaller than the previous).
- Enter on a pivot breakout with volume at least 40–50% above average.
- Stop loss: just below the last pivot low.
- Target: measure the depth of the base and project upward.

**Performance**: US Investing Championship 1997 (+155%), 2021 (+334%).

**Key Pine Script**:
```pinescript
//@version=5
indicator("Minervini Trend Template", overlay=true)
ma50  = ta.sma(close, 50)
ma150 = ta.sma(close, 150)
ma200 = ta.sma(close, 200)
plot(ma50,  color=color.blue,   title="50 SMA")
plot(ma150, color=color.orange, title="150 SMA")
plot(ma200, color=color.red,    title="200 SMA")

trend_template = (close > ma150 and close > ma200 and
  ma150 > ma200 and ma50 > ma150 and ma50 > ma200)
bgcolor(trend_template ? color.new(color.green, 88) : na,
  title="Trend Template Active")
```

**Social**: Twitter: @markminervini

---

### 5. William O'Neil — CAN SLIM Breakout System

**Country**: USA  
**Style**: Growth Trend-Following

**CAN SLIM Criteria**:
- **C** — Current quarterly EPS growth > 25% YoY.
- **A** — Annual EPS growth > 25% for the last 3 years.
- **N** — New product, new management, or new all-time highs.
- **S** — Supply and demand: small float with heavy institutional buying volume.
- **L** — Leader not laggard: Relative Strength (RS) line at new highs.
- **I** — Institutional sponsorship increasing.
- **M** — Market direction: only buy in confirmed uptrend (FTD signal).

**Entry Rule**: Buy "Cup with Handle" breakout above the pivot point on volume
150% above the 50-day average.

**Stop**: 7–8% below purchase price, no exceptions.

**Performance**: Built Investor's Business Daily; personal portfolio massively outperformed.

**Key Pine Script — Cup with Handle Detector**:
```pinescript
//@version=5
indicator("O'Neil RS Line", overlay=false)
sp500 = request.security("SPY", timeframe.period, close)
rs_line = close / sp500
plot(rs_line, color=color.purple, title="RS Line vs SPY")
```

**Social**: N/A (deceased)

---

### 6. Larry Williams — Seasonal Volatility Breakout

**Country**: USA  
**Style**: Short-Term Swing / Commodities / Futures

**Strategy Rules**:
- Use Commitments of Traders (COT) report: follow commercial hedgers when they
  are net long above historical norms.
- Trade seasonal tendencies: specific commodities and indices have statistically
  reliable seasonal windows.
- Williams %R below -80 = oversold buy zone.
- Volatility breakout entry: enter when today's range exceeds yesterday's highest
  high by a factor of X.

**Performance**: Turned $10,000 into $1.1M in the 1987 Robbins World Cup.

**Key Pine Script**:
```pinescript
//@version=5
indicator("Williams %R", overlay=false)
length = input.int(14, title="Length")
highest_high = ta.highest(high, length)
lowest_low   = ta.lowest(low, length)
wr = -100 * (highest_high - close) / (highest_high - lowest_low)
plot(wr, color=color.red, title="Williams %R")
hline(-20, "Overbought", color=color.red)
hline(-80, "Oversold",   color=color.green)
```

**Social**: YouTube: Larry Williams TV

---

### 7. Ed Seykota — Mechanical Trend-Following System

**Country**: USA  
**Style**: Systematic Donchian Trend-Following

**System Rules**:
- Buy on a new N-day channel high (Donchian Breakout).
- Sell on a new N-day channel low.
- Position size = (Risk % × Equity) / (Entry − Stop Loss in ATR units).
- Never override the system. Discipline is the edge.
- Cut losses without emotion. Let profits run without interference.

**Performance**: Documented ~250,000% return from 1972 to 1988 on managed accounts.

**Key Pine Script**:
```pinescript
//@version=5
strategy("Seykota Donchian Trend", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)
length  = input.int(20, "Donchian Period")
ch_high = ta.highest(high, length)[1]
ch_low  = ta.lowest(low,  length)[1]
plot(ch_high, color=color.green, title="Channel High")
plot(ch_low,  color=color.red,   title="Channel Low")
if close > ch_high
    strategy.entry("Long", strategy.long)
if close < ch_low
    strategy.close("Long")
```

**Social**: Trading Tribe platform

---

### 8. Linda Raschke — Holy Grail & Mean Reversion

**Country**: USA  
**Style**: Short-Term Swing / Day Trading

**Holy Grail Setup**:
1. ADX reading above 30 (strong trend confirmed).
2. Price pulls back to the 20-period EMA.
3. Entry: buy on the first reversal candle off the EMA (candle closes back above EMA).
4. Stop: below the pullback low.
5. Target: previous swing high.

**Turtle Soup Setup (Reversal)**:
- Take the opposite side of a Turtle 20-day breakout when the breakout fails
  within 2–4 bars and price reverses back inside the channel.

**Performance**: Hedge fund manager; featured in New Market Wizards.

**Key Pine Script**:
```pinescript
//@version=5
indicator("Raschke Holy Grail", overlay=true)
adx_len = input.int(14)
ema20 = ta.ema(close, 20)
[diplus, diminus, adx] = ta.dmi(adx_len, adx_len)
strong_trend = adx > 30
plot(ema20, color=strong_trend ? color.green : color.gray, title="20 EMA")
bgcolor(strong_trend and close <= ema20 * 1.002 and close >= ema20 * 0.998
  ? color.new(color.green, 80) : na, title="Holy Grail Zone")
```

**Social**: Twitter: @LindaRaschke

---

### 9. Richard Dennis — Turtle Trading Rules

**Country**: USA  
**Style**: Systematic Trend-Following

**Complete Turtle Rules**:
- **System 1 (short term)**: Buy new 20-day high; sell new 10-day low.
- **System 2 (long term)**: Buy new 55-day high; sell new 20-day low.
- **Position Size**: 1 unit = (1% of equity) / (2 × ATR(20)).
  Maximum 4 units per market, 6 units per correlated group.
- **Entry**: Only take the entry if the previous signal in that direction was a loser
  (to filter false breakouts).
- **Stop**: 2 × ATR(20) from entry.
- **Trail**: Tighten to 1 × ATR(20) after a 2 × ATR profit.

**Performance**: Turned $400 into $200M. Proved trading can be taught systematically.

**Key Python (Backtest-Ready)**:
```python
def turtle_position_size(equity, atr, risk_pct=0.01):
    """1% risk / (2 × ATR) gives unit size (shares)."""
    return int((equity * risk_pct) / (2 * atr))

def turtle_signal(highs, lows, system=1):
    period_entry = 20 if system == 1 else 55
    period_exit  = 10 if system == 1 else 20
    buy_signal  = highs[-1] > max(highs[-period_entry-1:-1])
    sell_signal = lows[-1]  < min(lows[-period_exit-1:-1])
    return buy_signal, sell_signal
```

**Social**: N/A

---

### 10. John Carter — TTM Squeeze (Momentum Compression)

**Country**: USA  
**Style**: Options Swing Trading

**TTM Squeeze Rules**:
- Bollinger Bands contract inside Keltner Channels = market in compression ("squeeze on").
- When Bollinger Bands expand outside Keltner Channels, the squeeze fires.
- Momentum histogram colour determines direction: green rising = long, red falling = short.
- Entry on squeeze release candle; stop below the low of the squeeze.

**Key Pine Script**:
```pinescript
//@version=5
indicator("TTM Squeeze", overlay=false)
length = input.int(20)
bb_mult = input.float(2.0)
kc_mult = input.float(1.5)
basis = ta.sma(close, length)
bb_upper = basis + bb_mult * ta.stdev(close, length)
bb_lower = basis - bb_mult * ta.stdev(close, length)
kc_upper = basis + kc_mult * ta.atr(length)
kc_lower = basis - kc_mult * ta.atr(length)
squeeze_on  = bb_upper < kc_upper and bb_lower > kc_lower
squeeze_off = bb_upper > kc_upper and bb_lower < kc_lower
momentum = ta.linreg(close - math.avg(ta.highest(high,length), ta.lowest(low,length), ta.sma(close,length)), length, 0)
plot(momentum, style=plot.style_histogram,
     color= momentum > 0 ? (momentum > momentum[1] ? color.lime : color.green)
                         : (momentum < momentum[1] ? color.red  : color.maroon))
plotchar(squeeze_on,  char="●", color=color.red,   size=size.tiny, location=location.bottom)
plotchar(squeeze_off, char="●", color=color.lime,  size=size.tiny, location=location.bottom)
```

**Social**: YouTube: Simpler Trading, Twitter: @johnfcarter

---

### 11. ICT (Michael Huddleston) — Smart Money Concepts

**Country**: USA  
**Style**: Smart Money Concepts (SMC), Scalping / Day Trading

**Core Concepts**:
- **Liquidity Sweeps**: Price wicks above swing highs (buy-side liquidity / BSL) or below
  swing lows (sell-side liquidity / SSL) to hunt retail stop orders before reversing.
- **Order Blocks**: The last bearish candle before a sharp bullish move (or vice versa)
  represents an institutional accumulation zone.
- **Fair Value Gaps (FVG)**: A 3-candle pattern where the middle candle leaves a gap
  between candle 1's high and candle 3's low. Price typically returns to fill these gaps.
- **Killzones** (ideal entry windows): London Open (2:30–5:30 AM EST),
  New York Open (8:30–11:00 AM EST). Avoid trading outside these windows.
- **Silver Bullet Strategy**: 3:00–4:00 AM EST or 10:00–11:00 AM EST. Wait for a
  liquidity sweep into an FVG within the killzone.

**ICT Entry Logic**:
1. Identify the higher-timeframe draw on liquidity (where price is heading).
2. Drop to lower timeframe. Wait for liquidity sweep of opposing side.
3. Entry at the FVG or order block left behind immediately after the sweep.
4. Stop: beyond the sweep wick.
5. Target: the higher-timeframe draw on liquidity.

**Key Pine Script**:
```pinescript
//@version=5
indicator("ICT Fair Value Gaps", overlay=true, max_boxes_count=50)
bullFVG = low > high[2]
bearFVG = high < low[2]
if bullFVG
    box.new(bar_index[2], high[2], bar_index, low,
            border_color=color.green, bgcolor=color.new(color.green, 85))
if bearFVG
    box.new(bar_index[2], high,    bar_index, low[2],
            border_color=color.red,   bgcolor=color.new(color.red,   85))
```

**Social**: YouTube: The Inner Circle Trader, Twitter: @I_Am_The_ICT

---

### 12. Ross Cameron (Warrior Trading) — Gap and Go

**Country**: USA  
**Style**: Day Trading (Low Float Momentum Scalping)

**Strategy Rules**:
- Pre-market scanner: stocks gapping up > 10% with relative volume > 5× average
  and float below 20 million shares.
- Entry: first pull back to the 9 EMA after the initial opening momentum candle.
- Stop: below the 9 EMA or VWAP.
- Target: measure the opening range and project 1:2 to 1:3.
- Never hold through lunch (11:30–2:00 PM EST) — volume dries up.

**Key Pine Script**:
```pinescript
//@version=5
indicator("VWAP + 9 EMA Warrior", overlay=true)
vwap_val = ta.vwap(hlc3)
ema9     = ta.ema(close, 9)
ema20    = ta.ema(close, 20)
plot(vwap_val, color=color.orange, linewidth=2, title="VWAP")
plot(ema9,     color=color.blue,   title="9 EMA")
plot(ema20,    color=color.purple, title="20 EMA")
```

**Performance**: Audited returns from $583 to over $10 million.

**Social**: YouTube: Warrior Trading, Instagram: @warriortrading

---

### 13. Rayner Teo — Trend-Pullback System

**Country**: Singapore  
**Style**: Swing Trend-Following

**Strategy Rules**:
- Identify the primary trend using the 200 EMA. Trade only in trend direction.
- Use the 50 EMA as the pullback entry zone.
- Wait for a "price rejection" candlestick (hammer, pin bar, engulfing) at the 50 EMA.
- Stop loss: 1 ATR below the rejection candle low.
- Target: previous swing high (minimum 1:2 risk-reward).
- Only trade when ADX > 20 (trending market, not ranging).

**Key Pine Script**:
```pinescript
//@version=5
indicator("Rayner Trend Pullback", overlay=true)
ema50  = ta.ema(close, 50)
ema200 = ta.ema(close, 200)
[_, _, adx] = ta.dmi(14, 14)
atr = ta.atr(14)
uptrend = close > ema200 and ema50 > ema200
pullback_zone = close < ema50 * 1.005 and close > ema50 * 0.995 and uptrend
plot(ema50,  title="50 EMA",  color=color.blue)
plot(ema200, title="200 EMA", color=color.red)
bgcolor(pullback_zone ? color.new(color.blue, 88) : na)
```

**Social**: YouTube: Rayner Teo (1.9M+ subscribers), Twitter: @Rayner_Teo

---

## PART 2 — INDIA'S BEST TRADERS

---

### 14. Rakesh Jhunjhunwala — Value + Momentum

**Style**: Value Investing with Momentum Confirmation

**Core Rules**:
- Identify businesses with scalable models, high economic moats, and dominant
  market position in their sector.
- Valuation discipline: never overpay. The margin of safety comes from understanding
  the business deeply, not from the chart.
- Wait for the market to agree: enter after the stock has already started moving
  (momentum confirmation, not pure bottom-fishing).
- Hold for years. Size up as conviction grows and the business delivers.
- Famous long holds: Titan, Tata Motors, Star Health, Aptech.

**Key Fundamental Metrics**:
- ROE consistently above 20%.
- Earnings growth compounding above 20% annually.
- Promoter holding high and stable.
- Debt-to-equity below 0.5 for manufacturing; near zero for finance/tech.

**Social**: N/A (deceased 2022)

---

### 15. Prashant Shah (Definedge) — Noiseless Charting

**Style**: Point & Figure and Renko Price Action

**Why Noiseless Charts**:
Standard OHLC charts include time-noise — small irrelevant moves during low-volume
periods that distort the picture. P&F and Renko charts plot only significant price
moves, filtering out time entirely.

**Point & Figure Entry Rules**:
- **Double Top Breakout**: New column of X exceeds the previous column of X by one box.
  This is the fundamental buy signal.
- **Triple Top Breakout**: Three prior columns of X at the same level are all exceeded.
  Higher probability than double top.
- **Bearish Double Bottom Breakdown**: Inverse of above — sell/short signal.
- Box size for Nifty: typically 30–50 points.

**Renko Strategy**:
- Brick size = 1 ATR of the underlying.
- Buy signal: two consecutive bullish bricks after a reversal from a bearish run.
- Stop: two consecutive bearish bricks after entry.

**Platform**: Definedge Securities (India), RZone charting platform.

**Social**: YouTube: Definedge Solutions, Twitter: @Prashant_Defi

---

### 16. PR Sundar — Options Premium Selling (Theta Decay)

**Style**: Non-Directional Options Selling

**Core Strategy — Short Strangle**:
- Sell 1 OTM Call and 1 OTM Put on Nifty/BankNifty weekly expiry.
- Strike selection: sell the strike nearest to 0.20–0.25 delta.
- Entry: Monday or Tuesday morning after IV settles post-weekend.
- Profit target: 30–50% of premium collected. Do not hold to expiry.
- Adjustment rules: If the underlying moves within 3% of either short strike,
  roll the breached side 2 strikes further OTM.
- Stop: 2× the premium collected on any single leg (hard stop).

**India VIX Rules**:
- VIX above 18: premiums are high, ideal entry window for selling.
- VIX below 12: premiums are thin, reduce size or skip the week.

**Key Python — Delta-Based Strike Selector**:
```python
import numpy as np
from scipy.stats import norm

def black_scholes_delta(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * np.sqrt(T))
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1

def find_otm_strike(spot, sigma, dte, target_delta=0.20, option_type='call'):
    T = dte / 365
    r = 0.065  # Indian risk-free rate approximate
    test_strikes = range(int(spot * 0.8), int(spot * 1.2), 50)
    best_strike = None
    min_diff = float('inf')
    for K in test_strikes:
        delta = abs(black_scholes_delta(spot, K, T, r, sigma, option_type))
        diff = abs(delta - target_delta)
        if diff < min_diff:
            min_diff = diff
            best_strike = K
    return best_strike
```

**Social**: YouTube: PR Sundar, Twitter: @PRSundar64

---

### 17. Alok Jain (Weekend Investing) — Quantitative Momentum Rotation

**Style**: Rules-Based Weekly Momentum Rotation

**System Logic**:
- Universe: Nifty 500 constituents (all 500 stocks).
- Every week, rank all stocks by 12-1 month momentum (12-month total return
  excluding the most recent 1 month to avoid short-term reversal).
- Invest equally in the top N stocks (typically top 20–30).
- Rebalance weekly: drop stocks that fall below the threshold; buy those entering.
- Hard exit rule: if a position falls 15% from entry, exit regardless of rank.

**Momentum Score Formula**:
```python
def momentum_score(prices_df, lookback_months=12, skip_months=1):
    """12-1 month momentum: return from 12 months ago to 1 month ago."""
    end_period   = -skip_months * 21   # ~21 trading days per month
    start_period = -lookback_months * 21
    returns = prices_df.iloc[end_period] / prices_df.iloc[start_period] - 1
    return returns.sort_values(ascending=False)
```

**Products**: Mi20 (top 20 momentum), Mi30 (top 30), Mi NNF (Nifty Next Fifty).

**Performance**: Long-run backtests (2002–present) show ~25–30% CAGR versus Nifty's
~14%, though with higher drawdowns during momentum crashes.

**Social**: YouTube: WeekendInvesting, Twitter: @WeekendInvestng

---

### 18. Ghanshyam Tech — BankNifty Price Action Scalping

**Style**: Intraday Options Buying (BankNifty Specialist)

**Core Rules**:
- Trade only BankNifty weekly options expiry (Thursday).
- Instruments: buy ATM or 1-strike ITM Call/Put based on direction.
- Time filter: only take trades between 9:30–11:30 AM or 1:30–3:00 PM IST.
  Avoid the 11:30–1:30 PM dead zone.
- Setup: wait for a clear candlestick reversal pattern (hammer, shooting star,
  inside bar breakout) at a key support/resistance zone or PDH/PDL.
- Entry: enter on close of the signal candle on the 5-minute chart.
- Stop: below/above the signal candle's opposite end.
- Target: 1:2 risk-reward minimum. Book 50% at 1:1, trail the rest.
- Maximum 2 trades per day. Stop trading after 2 losses.

**Social**: YouTube: Ghanshyam Tech / Art of Trading, Twitter: @ghanshyamtech

---

### 19. Anish Singh Thakur (Booming Bulls) — SMC + EMA Structure

**Style**: Swing and Intraday with Smart Money Concepts

**Strategy Rules**:
- Daily chart: confirm the higher-timeframe trend using 50 EMA and 200 EMA alignment.
- Drop to 15-minute chart to identify order blocks (last bearish candle before a
  large bullish push).
- Entry: when price returns to the order block zone, look for a bullish engulfing
  or pin bar for confirmation.
- Fibonacci: use 0.618 (golden ratio) retracement level as the sweet-spot entry
  within the order block zone.
- Stop: below the order block zone's lowest wick.
- Target: 1:2 minimum, targeting the next structural high.

**Pine Script — Order Block Detector**:
```pinescript
//@version=5
indicator("Order Block Detector", overlay=true)
lookback = input.int(3, "Lookback Bars")
bull_ob = low[lookback] < low and close > open and close[lookback] < open[lookback]
bear_ob = high[lookback] > high and close < open and close[lookback] > open[lookback]
if bull_ob
    box.new(bar_index[lookback], high[lookback], bar_index, low[lookback],
            border_color=color.green, bgcolor=color.new(color.green, 90))
if bear_ob
    box.new(bar_index[lookback], high[lookback], bar_index, low[lookback],
            border_color=color.red,   bgcolor=color.new(color.red,   90))
```

**Social**: YouTube: Booming Bulls Academy, Instagram: @anishsinghthakur

---

### 20. Kunal Saraogi — RSI Divergence + Bollinger Band Squeeze

**Style**: Swing Trading

**Strategy Rules**:
- **Bullish RSI Divergence Setup**: Price makes a lower low but RSI makes a higher
  low. Enter long at the second low with stop below the price low.
- **Bollinger Band Squeeze**: When Bollinger Bands narrow to their tightest 6-month
  range (BB width at a 6-month low), prepare for a big directional move. Enter
  on the first candle that breaks above/below the bands.
- Confirmation: MACD must cross in the direction of trade.

**Key Pine Script**:
```pinescript
//@version=5
indicator("BB Squeeze + RSI Divergence", overlay=false)
bb_length = input.int(20)
bb_mult   = input.float(2.0)
basis     = ta.sma(close, bb_length)
dev       = ta.stdev(close, bb_length)
bb_width  = (basis + bb_mult*dev - (basis - bb_mult*dev)) / basis * 100
rsi       = ta.rsi(close, 14)
plot(bb_width, color=color.blue,  title="BB Width %")
plot(rsi,      color=color.orange, title="RSI")
hline(30, "RSI Oversold",  color=color.green)
hline(70, "RSI Overbought", color=color.red)
```

**Social**: YouTube: Kunal Saraogi, Twitter: @kunalsaraogi

---

### 21. Amit Jeswani (Stallion Asset) — Indian CANSLIM Adaptation

**Style**: Growth Investing (CANSLIM adapted for Indian markets)

**Strategy Rules**:
- Focus on Indian consumer monopolies: companies that own a consumer category
  and face minimal import competition.
- EPS growth must be accelerating: last 3 quarters must show increasing growth rates.
- Price must be at or near all-time highs — this is a feature, not a warning.
- Stock must have institutional holding increasing quarter-on-quarter.
- Entry on breakout from a well-formed base (typically 6–12 week consolidation)
  with volume at least 2× the average.
- Hold for 6–18 months as long as the fundamental story intact.
- Examples held: Dixon Technologies, Laurus Labs, Route Mobile.

**Social**: Twitter: @StallionAsset

---

### 22. Hitesh Patel — Classical Chart Patterns (India's Chartist)

**Style**: Pattern-Based Swing Trading

**Core Patterns**:
- **Cup and Handle**: Rounded base with a short handle consolidation. Entry on
  handle breakout above the cup rim.
- **Head and Shoulders**: Reversal pattern. Entry on neckline breakdown.
- **Ascending Triangle**: Flat top with rising lows. Entry on flat-top breakout.
- **Flag and Pennant**: Continuation patterns after a sharp move.

**Rules**:
- Volume must dry up during the handle/flag consolidation.
- Volume must surge at least 2× on the breakout candle.
- Stop below the right shoulder (H&S) or below the handle (Cup & Handle).

**Social**: Screener.in threads, Twitter: @hitesh2710

---

### 23. Shankar Sharma — Contrarian Macro (India & EM)

**Style**: Contrarian Value / Global Macro

**Strategy Rules**:
- Find sectors or stocks that the entire market hates and has abandoned.
- Quantify the hatred: RSI near 20 on the monthly chart, fund ownership near zero,
  consensus analyst recommendations uniformly negative.
- Enter in tranches as the trend bottom forms (does not try to catch the exact low).
- Short exuberantly valued sectors (e.g., shorted IT during the 2000 tech bubble).
- Holds are multi-year. Exit when consensus turns bullish and valuations normalise.

**Social**: Twitter: @1shankarsharma

---

## PART 3 — UNIVERSAL PINE SCRIPT TOOLKIT

---

### Complete Multi-Strategy Dashboard Script

```pinescript
//@version=5
indicator("Master Trader Toolkit", overlay=true)

// --- Minervini Trend Template ---
ma50  = ta.sma(close, 50)
ma150 = ta.sma(close, 150)
ma200 = ta.sma(close, 200)
trend_template = close > ma150 and close > ma200 and ma150 > ma200 and ma50 > ma200
bgcolor(trend_template ? color.new(color.green, 92) : na)

// --- ICT Fair Value Gaps ---
bullFVG = low > high[2]
bearFVG = high < low[2]

// --- Turtle Donchian Channels ---
don_high = ta.highest(high, 20)[1]
don_low  = ta.lowest(low,  20)[1]
plot(don_high, color=color.teal, title="Turtle 20-Day High")
plot(don_low,  color=color.maroon, title="Turtle 20-Day Low")

// --- VWAP (Warrior / PTJ Defence) ---
plot(ta.vwap(hlc3), color=color.orange, linewidth=2, title="VWAP")
plot(ma50,  color=color.blue,  title="50 SMA")
plot(ma200, color=color.red,   linewidth=2, title="200 SMA")

// --- Raschke Holy Grail Zone ---
ema20 = ta.ema(close, 20)
[_, _, adx] = ta.dmi(14, 14)
holy_grail_zone = adx > 30 and math.abs(close - ema20) / ema20 < 0.005
bgcolor(holy_grail_zone ? color.new(color.blue, 85) : na)
```

---

### Turtle Position Sizing Calculator (Python)

```python
def calculate_position_size(portfolio_equity: float, entry_price: float,
                             atr: float, risk_pct: float = 0.01) -> dict:
    """
    Richard Dennis / Ed Seykota position sizing.
    risk_pct: fraction of equity to risk per trade (default 1%)
    stop_distance: 2 * ATR from entry
    """
    stop_distance = 2 * atr
    dollar_risk   = portfolio_equity * risk_pct
    shares        = int(dollar_risk / stop_distance)
    stop_price    = entry_price - stop_distance
    position_val  = shares * entry_price
    return {
        "shares": shares,
        "entry": entry_price,
        "stop": round(stop_price, 2),
        "dollar_risk": round(dollar_risk, 2),
        "position_value": round(position_val, 2),
        "pct_of_portfolio": round(position_val / portfolio_equity * 100, 2)
    }
```

---

### Momentum Rotation Screener (Python — Alok Jain style)

```python
import pandas as pd

def rank_momentum(prices: pd.DataFrame, top_n: int = 20,
                  lookback: int = 252, skip: int = 21) -> pd.Series:
    """
    12-1 month momentum ranking.
    prices: DataFrame of daily close prices (columns = tickers)
    Returns top N tickers ranked by momentum score.
    """
    end_idx   = -skip
    start_idx = -(lookback)
    momentum  = prices.iloc[end_idx] / prices.iloc[start_idx] - 1
    ranked    = momentum.sort_values(ascending=False)
    return ranked.head(top_n)
```

---

### India VIX Options Filter (Python — PR Sundar style)

```python
def vix_regime(india_vix: float) -> dict:
    """Classifies India VIX into trading regime for options sellers."""
    if india_vix >= 20:
        return {"regime": "HIGH_VIX", "action": "SELL_STRANGLES",
                "size": "FULL", "note": "Premium is rich, ideal for theta collection."}
    elif india_vix >= 14:
        return {"regime": "NORMAL_VIX", "action": "SELL_STRANGLES",
                "size": "HALF", "note": "Moderate premium, reduce size slightly."}
    elif india_vix >= 10:
        return {"regime": "LOW_VIX", "action": "WAIT_OR_SMALL",
                "size": "QUARTER", "note": "Thin premium, very small size or skip."}
    else:
        return {"regime": "EXTREME_LOW_VIX", "action": "AVOID",
                "size": "NONE", "note": "VIX historically mean-reverts — do not sell."}
```

---

## PART 4 — IMPLEMENTATION REFERENCE MAP

| Trader | Framework Key | Implemented In |
|:---|:---|:---|
| Minervini | VCP + Trend Template (50/150/200 SMA) | `personas.py` → `evaluate_minervini()` |
| Richard Dennis | Turtle Breakout + ATR sizing | `personas.py` → `evaluate_turtle()` |
| ICT / Day Trading Guruji | Liquidity sweeps + FVG + Order Blocks | `personas.py` → `evaluate_day_trading_guruji()` |
| Ray Fu | ATR 1% sizing + Maker-Checker | `personas.py` → `evaluate_ray_fu()` |
| PR Sundar | VIX regime + delta-based strike selector | `server.py` → `/api/options/vix_regime` |
| Alok Jain | 12-1 momentum rotation | `server.py` → `/api/screener/momentum` |
| Ghanshyam Tech | BankNifty candlestick + time filter | Web Playbook tab |
| Seykota / Dennis | Donchian + turtle sizing | Web Playbook tab calculator |
| O'Neil | CAN SLIM RS Line | Web Playbook tab |
| algotrader.sahil / Booming Bulls | FRVP VAH/VAL | `src/analysis/frvp.py` → `evaluate_frvp()` |

---

## PART 5 — COMMUNITY FIND: FRVP GOLD STRATEGY

**Source**: Instagram @algotrader.sahil (9,450 likes, 10K comments — July 11 2026)  
**Reel**: https://www.instagram.com/reel/Dap-XNMzFM_/  
**Credit**: Algo-backtested version of a strategy popularised by Anish Singh Thakur (Booming Bulls, 3.5M+ subscribers)

---

### 24. Fixed Range Volume Profile (FRVP) — VAH/VAL Strategy

**What is FRVP**:
The Fixed Range Volume Profile plots the distribution of trading volume across price
levels for a user-defined range of candles (e.g., the previous week or the previous
session). It produces three critical levels:

- **POC (Point of Control)**: The exact price level where the most volume traded.
  This is the market's "fairest" price and acts as the strongest support/resistance.
- **VAH (Value Area High)**: The upper boundary of the zone where 70% of all volume
  traded. Price above VAH = premium territory, statistically likely to revert.
- **VAL (Value Area Low)**: The lower boundary of the 70% volume zone. Price below
  VAL = discount territory, statistically likely to revert toward VAH.

The "Value Area" (VAL to VAH) represents the zone where institutional participants
conducted the bulk of their business. Retail traders consistently over-extend outside
this zone, creating mean-reversion opportunities.

---

**Strategy Rules (FRVP VAH/VAL Setup)**:

**Setup Type**: Mean Reversion + Breakout Confirmation  
**Instrument**: Any liquid instrument (Gold MCX, Nifty Futures, BankNifty, XAUUSD)  
**Timeframe**: 15-minute chart for entry; 1-hour chart for FRVP calculation range  
**Risk-Reward Target**: Minimum 1:2.5, optimal 1:3

**Step 1 — Draw the FRVP**:
Set the Fixed Range from the start of the previous session (or previous week for
positional trades) to its close. The profile plots automatically in TradingView
using the "Fixed Range Volume Profile" tool.

**Step 2 — Long Setup (VAL Bounce)**:
- Price falls below VAL (discount zone entry).
- Wait for a bullish rejection candle at or just below VAL (hammer, bullish engulfing,
  pin bar) on the 15-minute chart.
- Volume on the rejection candle must be above the 20-period average.
- Entry: on close of the rejection candle.
- Stop Loss: 1 ATR below the rejection candle low.
- Target 1 (50% position exit): POC level.
- Target 2 (remaining 50%): VAH level (1:3 risk-reward zone).

**Step 3 — Short Setup (VAH Rejection)**:
- Price rises above VAH (premium zone, overextended).
- Wait for a bearish rejection candle at or just above VAH (shooting star, bearish
  engulfing, inside bar break) on the 15-minute chart.
- Volume confirmation: rejection candle volume above 20-period average.
- Entry: on close of the rejection candle.
- Stop Loss: 1 ATR above the rejection candle high.
- Target 1 (50% position exit): POC level.
- Target 2 (remaining 50%): VAL level.

**Step 4 — Breakout Setup (POC/VAH/VAL Breakout)**:
- If price breaks above VAH with a strong candle (body > 60% of candle range)
  and volume 2× the 20-period average, a breakout continuation setup forms.
- Entry: retest of VAH from above (VAH now acts as support).
- Stop: below VAH.
- Target: VAH + (VAH − VAL) projected upward (equal range projection).

**Filter Rules**:
- Do NOT take VAL long trades when the broader market trend (Nifty/sensex) is
  in a confirmed downtrend (price below its daily 200 SMA).
- Do NOT take VAH short trades during a high-momentum breakout session
  (ADX above 35 in trend-following mode).
- Time filter: avoid the first 15 minutes after market open (9:15–9:30 AM IST)
  — FRVP levels often get tested and rejected multiple times in the opening noise.

---

**Backtested Context (from @algotrader.sahil reel)**:
- Asset: Gold (MCX or XAUUSD)
- Claimed risk-reward: up to 1:3
- Strategy originally used by prop firm traders
- 1-year backtest results teased in the reel (full results shared via DM for "BACKTEST" comment)

---

**Pine Script — FRVP VAH/VAL Levels + Signal**:

```pinescript
//@version=5
indicator("FRVP VAH/VAL Strategy (Approximate)", overlay=true)

// Since TradingView's FRVP is a drawing tool, we approximate using
// the highest volume price level over a fixed lookback window.

lookback   = input.int(50, "FRVP Lookback Bars", minval=10)
atr_len    = input.int(14, "ATR Length")
atr_mult   = input.float(1.0, "Stop ATR Multiplier")

// Approximate VAH, VAL, POC using price percentiles as a volume proxy
// (Replace with actual volume-weighted calculations if volume data is available)
highest_h = ta.highest(high, lookback)
lowest_l  = ta.lowest(low,  lookback)
range_sz  = highest_h - lowest_l
vah       = lowest_l + range_sz * 0.85   // top of 70% value area
val       = lowest_l + range_sz * 0.15   // bottom of 70% value area
poc       = lowest_l + range_sz * 0.50   // midpoint approximation

plot(vah, color=color.new(color.red,   20), linewidth=2, title="VAH")
plot(val, color=color.new(color.green, 20), linewidth=2, title="VAL")
plot(poc, color=color.new(color.orange,20), linewidth=1, title="POC", style=plot.style_circles)

atr = ta.atr(atr_len)

// Long Signal: price at VAL with bullish rejection
long_signal = close <= val * 1.002 and close > open and volume > ta.sma(volume, 20)
// Short Signal: price at VAH with bearish rejection
short_signal = close >= vah * 0.998 and close < open and volume > ta.sma(volume, 20)

plotshape(long_signal,  style=shape.triangleup,   location=location.belowbar, color=color.green, size=size.small, title="VAL Long")
plotshape(short_signal, style=shape.triangledown,  location=location.abovebar, color=color.red,   size=size.small, title="VAH Short")

// Stop and target levels on signal
long_stop   = val - atr * atr_mult
long_target = vah
short_stop  = vah + atr * atr_mult
short_target = val
```

**Python — FRVP Calculation from OHLCV Data**:

```python
import pandas as pd
import numpy as np

def calculate_frvp(df: pd.DataFrame, start_idx: int, end_idx: int,
                   n_bins: int = 50) -> dict:
    """
    Calculate Fixed Range Volume Profile levels (VAH, VAL, POC)
    from a slice of OHLCV data.

    df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
    start_idx, end_idx: integer row indices defining the fixed range
    n_bins: number of price buckets in the profile
    """
    slice_df = df.iloc[start_idx:end_idx + 1].copy()

    price_min = slice_df['low'].min()
    price_max = slice_df['high'].max()
    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_mids  = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Distribute each bar's volume proportionally across the price bins it spans
    volume_at_price = np.zeros(n_bins)
    for _, row in slice_df.iterrows():
        bar_low, bar_high, bar_vol = row['low'], row['high'], row['volume']
        # Find which bins this bar spans
        in_range = (bin_mids >= bar_low) & (bin_mids <= bar_high)
        n_covered = in_range.sum()
        if n_covered > 0:
            volume_at_price[in_range] += bar_vol / n_covered

    # POC: bin with highest volume
    poc_idx = np.argmax(volume_at_price)
    poc     = round(bin_mids[poc_idx], 2)

    # Value Area: bins containing 70% of total volume, starting from POC
    total_vol    = volume_at_price.sum()
    target_vol   = total_vol * 0.70
    accumulated  = volume_at_price[poc_idx]
    upper_idx    = poc_idx
    lower_idx    = poc_idx

    while accumulated < target_vol:
        expand_up   = upper_idx < n_bins - 1
        expand_down = lower_idx > 0
        vol_up   = volume_at_price[upper_idx + 1] if expand_up   else 0
        vol_down = volume_at_price[lower_idx - 1] if expand_down else 0
        if vol_up >= vol_down and expand_up:
            upper_idx  += 1
            accumulated += vol_up
        elif expand_down:
            lower_idx  -= 1
            accumulated += vol_down
        else:
            break

    vah = round(bin_mids[upper_idx], 2)
    val = round(bin_mids[lower_idx], 2)

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "value_area_pct": round(accumulated / total_vol * 100, 1),
        "price_range": (round(price_min, 2), round(price_max, 2))
    }


def evaluate_frvp_setup(current_price: float, vah: float, val: float,
                         poc: float, atr: float,
                         candle_bullish: bool, volume_above_avg: bool) -> dict:
    """
    Given current FRVP levels and current bar conditions, determine
    if a VAH/VAL setup is active and compute stops + targets.
    """
    at_val = current_price <= val * 1.003
    at_vah = current_price >= vah * 0.997

    if at_val and candle_bullish and volume_above_avg:
        setup = "LONG_VAL_BOUNCE"
        entry = current_price
        stop  = round(val - atr, 2)
        tp1   = poc
        tp2   = vah
        rr    = round((tp2 - entry) / (entry - stop), 2) if entry > stop else 0
    elif at_vah and not candle_bullish and volume_above_avg:
        setup = "SHORT_VAH_REJECTION"
        entry = current_price
        stop  = round(vah + atr, 2)
        tp1   = poc
        tp2   = val
        rr    = round((entry - tp2) / (stop - entry), 2) if stop > entry else 0
    else:
        setup = "NO_SETUP"
        entry = stop = tp1 = tp2 = rr = None

    return {
        "setup":  setup,
        "entry":  entry,
        "stop":   stop,
        "tp1":    tp1,
        "tp2":    tp2,
        "rr":     rr,
        "vah":    vah,
        "val":    val,
        "poc":    poc
    }
```

---

*Last updated: September 2026. Sources: YouTube channels, documented interviews, publicly
available books (Market Wizards, Trade Like a Stock Market Wizard, How to Make Money
in Stocks), Instagram @algotrader.sahil, and TradingView community Pine Scripts.*

