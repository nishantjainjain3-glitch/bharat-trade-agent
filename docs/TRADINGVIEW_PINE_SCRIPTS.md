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


---

## 6. Hardik Sharma & Mandeep Joon - Central Pivot Range (CPR) Width & Regime Indicator

```pinescript
//@version=5
indicator("CPR Width & Regime Classifier", overlay=true)

// Daily Reference Bars
prevClose = request.security(syminfo.tickerid, "D", close[1], barmerge.gaps_off, barmerge.lookahead_on)
prevHigh  = request.security(syminfo.tickerid, "D", high[1], barmerge.gaps_off, barmerge.lookahead_on)
prevLow   = request.security(syminfo.tickerid, "D", low[1], barmerge.gaps_off, barmerge.lookahead_on)

pp = (prevHigh + prevLow + prevClose) / 3.0
bc = (prevHigh + prevLow) / 2.0
tc = (pp - bc) + pp

cprTop = math.max(tc, bc)
cprBottom = math.min(tc, bc)
cprWidthPct = (math.abs(tc - bc) / pp) * 100.0

plot(pp, "Pivot", color=color.yellow, linewidth=2)
pTop = plot(cprTop, "TC", color=color.blue, linewidth=1)
pBot = plot(cprBottom, "BC", color=color.blue, linewidth=1)
fill(pTop, pBot, color=cprWidthPct < 0.25 ? color.new(color.green, 80) : color.new(color.orange, 85), title="CPR Range")

var table cprTable = table.new(position.top_right, 2, 2, bgcolor=color.new(color.black, 40), border_width=1)
if (barstate.islast)
    string regText = cprWidthPct < 0.25 ? "NARROW (TREND DAY 70%)" : (cprWidthPct > 0.60 ? "WIDE (RANGE CHOP 80%)" : "NORMAL CPR")
    color regCol = cprWidthPct < 0.25 ? color.green : (cprWidthPct > 0.60 ? color.red : color.gray)
    table.cell(cprTable, 0, 0, "CPR Width:", text_color=color.white, text_size=size.small)
    table.cell(cprTable, 1, 0, str.tostring(cprWidthPct, "#.###") + "%", text_color=regCol, text_size=size.small)
    table.cell(cprTable, 0, 1, "Regime:", text_color=color.white, text_size=size.small)
    table.cell(cprTable, 1, 1, regText, text_color=regCol, text_size=size.small)
```

---

## 7. Mandeep Joon (@generous_gyan) - Inside Bar (Mother Candle) Breakout Strategy

```pinescript
//@version=5
strategy("Mandeep Joon Inside Bar Breakout", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=20)

motherHigh = high[2]
motherLow  = low[2]
insideHigh = high[1]
insideLow  = low[1]

isInsideBar = (insideHigh <= motherHigh) and (insideLow >= motherLow)
ema20 = ta.ema(close, 20)
plot(ema20, "20 EMA", color=color.yellow, linewidth=2)

bullBreakout = isInsideBar and ta.crossover(close, motherHigh) and close > ema20
bearBreakdown = isInsideBar and ta.crossunder(close, motherLow) and close < ema20

plotshape(isInsideBar and not (bullBreakout or bearBreakdown), title="Inside Bar", style=shape.circle, location=location.abovebar, color=color.gray, size=size.tiny)
plotshape(bullBreakout, title="Bullish Inside Breakout", style=shape.triangleup, location=location.belowbar, color=color.green, size=size.small, text="IB BREAK")
plotshape(bearBreakdown, title="Bearish Inside Breakdown", style=shape.triangledown, location=location.abovebar, color=color.red, size=size.small, text="IB DOWN")

if (bullBreakout)
    stopLoss = insideLow
    target = close + 1.5 * (motherHigh - motherLow)
    strategy.entry("Long IB", strategy.long)
    strategy.exit("TP/SL", "Long IB", limit=target, stop=stopLoss)

if (bearBreakdown)
    stopLoss = insideHigh
    target = close - 1.5 * (motherHigh - motherLow)
    strategy.entry("Short IB", strategy.short)
    strategy.exit("TP/SL", "Short IB", limit=target, stop=stopLoss)
```

---

## 8. Algo With Wahid - Fair Value Gap (FVG) / Imbalance Detector

```pinescript
//@version=5
indicator("Algo With Wahid Fair Value Gap (FVG)", overlay=true)

bullishFVG = low[0] > high[2]
bearishFVG = high[0] < low[2]

if (bullishFVG)
    box.new(left=bar_index[2], top=low[0], right=bar_index + 5, bottom=high[2], bgcolor=color.new(color.green, 85), border_color=color.green)

if (bearishFVG)
    box.new(left=bar_index[2], top=low[2], right=bar_index + 5, bottom=high[0], bgcolor=color.new(color.red, 85), border_color=color.red)
```

---

## 9. TradeIQ Day 2 - RSI Multi-Pivot Divergence Indicator

```pinescript
//@version=5
indicator("TradeIQ RSI Divergence Engine", overlay=true)

rsiVal = ta.rsi(close, 14)

// Pivot Points in Price and RSI
plPrice = ta.pivotlow(low, 5, 2)
phPrice = ta.pivothigh(high, 5, 2)

// Bullish Divergence: Price Lower Low, RSI Higher Low
bullDiv = not na(plPrice) and (low[2] < ta.valuewhen(not na(plPrice), low[2], 1)) and (rsiVal[2] > ta.valuewhen(not na(plPrice), rsiVal[2], 1)) and (rsiVal[2] < 45)
plotshape(bullDiv, title="Bullish Divergence", style=shape.labelup, location=location.belowbar, color=color.green, size=size.small, text="BULL DIV")

// Bearish Divergence: Price Higher High, RSI Lower High
bearDiv = not na(phPrice) and (high[2] > ta.valuewhen(not na(phPrice), high[2], 1)) and (rsiVal[2] < ta.valuewhen(not na(phPrice), rsiVal[2], 1)) and (rsiVal[2] > 55)
plotshape(bearDiv, title="Bearish Divergence", style=shape.labeldown, location=location.abovebar, color=color.red, size=size.small, text="BEAR DIV")
```


---

## 10. Larry Connors - RSI(2) Quantitative Mean Reversion Model

```pinescript
//@version=5
strategy("Larry Connors RSI(2) Quantitative Model", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=25)

rsi2 = ta.rsi(close, 2)
sma200 = ta.sma(close, 200)
ema5 = ta.ema(close, 5)

plot(sma200, "200 SMA Filter", color=color.white, linewidth=2)
plot(ema5, "5 EMA Exit", color=color.yellow, linewidth=1)

inUptrend = close > sma200
oversoldDip = rsi2 < 10.0
exitCondition = close > ema5

if (inUptrend and oversoldDip)
    strategy.entry("Connors Dip Long", strategy.long)

if (exitCondition)
    strategy.close("Connors Dip Long", comment="Exit above 5 EMA")
```

---

## 11. Nick Stott - Camarilla Pivot Points (H4 Breakout & L3 Reversal)

```pinescript
//@version=5
indicator("Camarilla Pivot Points (Intraday)", overlay=true)

prevClose = request.security(syminfo.tickerid, "D", close[1], barmerge.gaps_off, barmerge.lookahead_on)
prevHigh  = request.security(syminfo.tickerid, "D", high[1], barmerge.gaps_off, barmerge.lookahead_on)
prevLow   = request.security(syminfo.tickerid, "D", low[1], barmerge.gaps_off, barmerge.lookahead_on)

rng = prevHigh - prevLow
h4 = prevClose + rng * 1.1 / 2.0
h3 = prevClose + rng * 1.1 / 4.0
l3 = prevClose - rng * 1.1 / 4.0
l4 = prevClose - rng * 1.1 / 2.0

plot(h4, "H4 Breakout Long", color=color.green, linewidth=2, style=plot.style_linebr)
plot(h3, "H3 Resistance", color=color.orange, linewidth=1, style=plot.style_linebr)
plot(l3, "L3 Support", color=color.teal, linewidth=1, style=plot.style_linebr)
plot(l4, "L4 Breakdown Short", color=color.red, linewidth=2, style=plot.style_linebr)
```

---

## 12. Kunal Saraogi - VIP (Volume, Indicator, Price) Setup

```pinescript
//@version=5
indicator("Kunal Saraogi VIP Setup", overlay=true)

// Price (P): 20 EMA
ema20 = ta.ema(close, 20)
plot(ema20, "20 EMA", color=color.teal, linewidth=2)
pPass = close > ema20

// Indicator (I): MACD Histogram
[macdLine, signalLine, histLine] = ta.macd(close, 12, 26, 9)
iPass = histLine > 0

// Volume (V): Volume > 1.1x SMA20
volSMA = ta.sma(volume, 20)
vPass = volume > (1.1 * volSMA)

vipScore = (pPass ? 1 : 0) + (iPass ? 1 : 0) + (vPass ? 1 : 0)
plotshape(vipScore == 3, title="VIP Strong Buy", style=shape.triangleup, location=location.belowbar, color=color.green, size=size.small, text="VIP BUY")
```
