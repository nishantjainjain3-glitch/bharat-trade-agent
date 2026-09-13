# TradingView Pine Script (v5) Library: Social Media Strategies

This file contains copy-paste ready Pine Script v5 code for the strategies extracted from top trading educators and creators.

---

## 1. Mandeep Joon (@generous_gyan) - 9 EMA + Pivot Points Standard Strategy

```pinescript
//@version=5
strategy("Mandeep Joon 9 EMA + Standard Pivots Strategy", overlay=true, initial_capital=100000, default_qty_type=strategy.percent_of_equity, default_qty_value=20)

// 1. Indicators
ema9 = ta.ema(close, 9)
plot(ema9, "9 EMA", color=color.blue, linewidth=2)

// Daily Pivots
prevClose = request.security(syminfo.tickerid, "D", close[1], barmerge.gaps_off, barmerge.lookahead_on)
prevHigh  = request.security(syminfo.tickerid, "D", high[1], barmerge.gaps_off, barmerge.lookahead_on)
prevLow   = request.security(syminfo.tickerid, "D", low[1], barmerge.gaps_off, barmerge.lookahead_on)

pp = (prevHigh + prevLow + prevClose) / 3.0
r1 = 2 * pp - prevLow
s1 = 2 * pp - prevHigh
r2 = pp + (prevHigh - prevLow)
s2 = pp - (prevHigh - prevLow)

plot(pp, "Pivot (P)", color=color.yellow, linewidth=2)
plot(r1, "R1", color=color.green, linewidth=1, style=plot.style_stepline)
plot(s1, "S1", color=color.red, linewidth=1, style=plot.style_stepline)
plot(r2, "R2", color=color.green, linewidth=2, style=plot.style_stepline)
plot(s2, "S2", color=color.red, linewidth=2, style=plot.style_stepline)

// Conditions
bullishCandle = close > open
bearishCandle = close < open

// Buy Signal 1: Breakout above Pivot Point and above 9 EMA
longPivotBreakout = ta.crossover(close, pp) and close > ema9 and bullishCandle

// Buy Signal 2: S1 Support Bounce
longS1Bounce = low <= s1 and close > s1 and close > ema9 and bullishCandle

// Sell Signal: Breakdown below Pivot Point and below 9 EMA
shortPivotBreakdown = ta.crossunder(close, pp) and close < ema9 and bearishCandle

if (longPivotBreakout or longS1Bounce)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", limit=r1, stop=math.min(pp, ema9))

if (shortPivotBreakdown)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", limit=s1, stop=math.max(pp, ema9))
```

---

## 2. Harinder Sahu (@kingresearch_academy) - 5-Pillar Confluence Engine

```pinescript
//@version=5
indicator("King Research 5-Pillar Confluence Engine", overlay=true)

// Pillar 1: Trend (20 & 200 EMA)
ema20  = ta.ema(close, 20)
ema200 = ta.ema(close, 200)
plot(ema20, "20 EMA", color=color.teal, linewidth=2)
plot(ema200, "200 EMA", color=color.maroon, linewidth=2)
trendBull = close > ema20 and ema20 > ema200
trendBear = close < ema20 and ema20 < ema200

// Pillar 2: Momentum (RSI 14)
rsi14 = ta.rsi(close, 14)
rsiBull = rsi14 >= 60
rsiBear = rsi14 <= 40

// Pillar 3: Value (VWAP)
vwapVal = ta.vwap(hlc3)
plot(vwapVal, "VWAP", color=color.purple, linewidth=2, style=plot.style_circles)
vwapBull = close > vwapVal
vwapBear = close < vwapVal

// Pillar 4: Volume (Volume > 1.2x SMA20)
volSMA = ta.sma(volume, 20)
volSurge = volume > (1.2 * volSMA)

// Pillar 5: Risk (ATR 14)
atrVal = ta.atr(14)

// Scoring Confluence
int bullScore = (trendBull ? 1 : 0) + (rsiBull ? 1 : 0) + (vwapBull ? 1 : 0) + (volSurge ? 1 : 0) + (close > ema20 ? 1 : 0)
int bearScore = (trendBear ? 1 : 0) + (rsiBear ? 1 : 0) + (vwapBear ? 1 : 0) + (volSurge ? 1 : 0) + (close < ema20 ? 1 : 0)

plotshape(bullScore >= 4, title="5-Pillar Buy Signal", style=shape.triangleup, location=location.belowbar, color=color.green, size=size.small, text="BUY 4/5")
plotshape(bearScore >= 4, title="5-Pillar Sell Signal", style=shape.triangledown, location=location.abovebar, color=color.red, size=size.small, text="SELL 4/5")
```

---

## 3. Nitya Tiwari (@tradeiq.with.nitz) - 9/21 EMA Dynamic Pullback Strategy

```pinescript
//@version=5
strategy("TradeIQ 9/21 EMA Dynamic Pullback Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=20)

ema9  = ta.ema(close, 9)
ema21 = ta.ema(close, 21)

plot(ema9, "9 EMA", color=color.green, linewidth=2)
plot(ema21, "21 EMA", color=color.orange, linewidth=2)

// ATR for Stop Loss
atrVal = ta.atr(14)

bullTrend = ema9 > ema21
bearTrend = ema9 < ema21

// Pullback to 9-21 EMA ribbon
bullPullback = bullTrend and low <= ema9 and close > ema9 and close > open
bearPullback = bearTrend and high >= ema9 and close < ema9 and close < open

if (bullPullback)
    stopLoss = math.min(low, ema21) - (0.2 * atrVal)
    takeProfit = close + 2.0 * (close - stopLoss)
    strategy.entry("Long Pullback", strategy.long)
    strategy.exit("TP/SL", "Long Pullback", limit=takeProfit, stop=stopLoss)

if (bearPullback)
    stopLoss = math.max(high, ema21) + (0.2 * atrVal)
    takeProfit = close - 2.0 * (stopLoss - close)
    strategy.entry("Short Pullback", strategy.short)
    strategy.exit("TP/SL", "Short Pullback", limit=takeProfit, stop=stopLoss)
```

---

## 4. Hardik Sharma (@daytradingguruji) - Stock Burner 9/20 EMA Momentum Strategy

```pinescript
//@version=5
strategy("Stock Burner 9/20 EMA Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=20)

ema9   = ta.ema(close, 9)
ema20  = ta.ema(close, 20)
ema200 = ta.ema(close, 200)

plot(ema9, "9 EMA", color=color.aqua, linewidth=2)
plot(ema20, "20 EMA", color=color.blue, linewidth=2)
plot(ema200, "200 EMA", color=color.white, linewidth=3)

atrVal = ta.atr(14)

bullCross = ta.crossover(ema9, ema20) and close > ema200
bearCross = ta.crossunder(ema9, ema20) and close < ema200

// Retest entry
retestLong = (ema9 > ema20) and (close > ema200) and (low <= ema20) and (close > ema9)

if (bullCross or retestLong)
    stopLoss = ema20 - (0.5 * atrVal)
    takeProfit = close + (1.8 * atrVal)
    strategy.entry("Burner Long", strategy.long)
    strategy.exit("Exit Long", "Burner Long", limit=takeProfit, stop=stopLoss)

if (bearCross)
    stopLoss = ema20 + (0.5 * atrVal)
    takeProfit = close - (1.8 * atrVal)
    strategy.entry("Burner Short", strategy.short)
    strategy.exit("Exit Short", "Burner Short", limit=takeProfit, stop=stopLoss)
```

---

## 5. System Cracker (@systemcracker_1) - Dark Pool / Absorption Detector

```pinescript
//@version=5
indicator("System Cracker Dark Pool / Absorption Footprint", overlay=true)

volSMA = ta.sma(volume, 20)
atrVal = ta.atr(14)

// Dark Pool Absorption: Huge Volume with Tightly Compressed Candle Range
isAbsorption = (volume >= 2.2 * volSMA) and ((high - low) <= 0.8 * atrVal)

var float darkPoolBenchmark = na
if (isAbsorption)
    darkPoolBenchmark := (high + low) / 2.0

plot(darkPoolBenchmark, "Dark Pool Benchmark", color=color.new(color.yellow, 20), linewidth=3, style=plot.style_linebr)
plotshape(isAbsorption, title="Dark Pool Accumulation", style=shape.diamond, location=location.belowbar, color=color.yellow, size=size.normal, text="DARK POOL")
```
