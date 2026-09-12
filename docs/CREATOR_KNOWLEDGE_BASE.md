# Master Trading Knowledge Base: Ray Fu & Day Trading Guruji

This document synthesizes the quantitative, architectural, and price action principles extracted from Ray Fu (@raycfu) and Hardik Sharma / Day Trading Guruji (@daytradingguruji). Both methodologies are directly integrated into our autonomous Indian trading agent, risk constitution, persona evaluations, and web dashboard.

---

## 1. Ray Fu (@raycfu) Quantitative Trading Architecture

Ray Fu's work focuses on systematic algorithmic trading, quantitative risk management, and adversarial multi-agent verification.

### A. ATR-Based 1% Volatility Risk Sizing
Rather than allocating arbitrary share quantities or fixed cash percentages, position sizing is strictly dictated by volatility:
- **Rule**: Never risk more than 1.0% of total portfolio equity on any individual trade setup.
- **Formula**:
  Risk Budget = Portfolio Equity * 0.01
  Stop Distance = 1.5 * ATR_14 (or 2.0 * ATR_14)
  Max Allowed Shares = Risk Budget / Stop Distance
- **Capital Constraint**: If total position outlay exceeds available capital, size scales down while preserving the 1% risk ceiling.

### B. Multi-Instrument Regime Matrix
A single strategy cannot operate across all market conditions. Ray Fu segments execution by regime:
1. **Index Mean Reversion**: Active during low-volatility, range-bound environments where price oscillates around historical averages and CPR pivots.
2. **Momentum Breakouts**: Triggered when volatility expands out of compression (e.g., Bollinger Band squeeze release or narrow CPR expansion) accompanied by relative volume surges.
3. **Trend Following**: Activated when ADX > 25 with stacked moving averages (20 EMA > 50 EMA > 200 EMA).

### C. 10% Maximum Portfolio Drawdown Circuit Breaker
A systematic drawdown circuit breaker protects capital from compounding losses:
- **Drawdown >= 2.0%**: Defensive tier engages; position sizing is cut by 50% and setup conviction threshold increases.
- **Drawdown >= 5.0%**: Critical tier engages; new buy orders are locked and trailing stops are tightened.
- **Drawdown >= 10.0% or Daily Loss >= 6.0%**: Circuit breaker trips; all automated trading operations suspend immediately.

### D. Maker-Checker Adversarial Loop
To prevent hallucinations and sloppy execution in automated research:
- **The Maker**: Proposes the fundamental thesis, entry range, target price, and stop loss.
- **The Checker**: An independent deterministic validation layer that:
  1. Recalculates all mathematics to verify risk-to-reward is at least 1.5:1.
  2. Cross-verifies fundamental metrics (P/E, ROE, Debt/Equity) against exchange filings.
  3. Tags unverified metrics with [UNVERIFIED].
  4. Caps conviction score if critical metrics lack empirical backing.

### E. Loop Engineering & Signal Decay
- **Information Coefficient (IC)**: Evaluates predictive correlation between signal ranking and forward asset returns. Scores > 0.5 indicate strong predictive power; scores < 0.3 represent noise.
- **Signal Half-Life Filter**: Requires signals to hold statistical edge for at least 5 trading bars, eliminating transient 1-bar spikes.
- **Walk-Forward Validation**: 70/30 in-sample/out-of-sample data splits with Bonferroni multiple testing corrections to prevent curve-fitting.

---

## 2. Day Trading Guruji (@daytradingguruji / Hardik Sharma) Setups

Hardik Sharma's work exposes the failures of retail indicator crossover scripts and emphasizes institutional price action, Central Pivot Range (CPR), and liquidity sweeps.

### A. Retail Indicator Backtest Reality Check
Historical backtests across Indian indices and stocks reveal that mechanical indicator scripts consistently lose money in real market conditions:

| Strategy Name | Source / Guru | Timeframe | Net Return | Win Rate | Drawdown | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **5 EMA Strategy** | Subasish Pani (Power of Stocks) | 5m (Short) / 15m (Buy) | -5.19% | 23.5% | 8.7% | **Loss**: Whipsaws in sideways markets |
| **9 & 15 EMA Scalp** | Mayank Raj (The Trade Room) | 5m | Negative | <30.0% | 11.2% | **Loss**: Moving average lag without volume |
| **Brahmastra Setup** | Pushkar Raj Thakur | 5m (VWAP + Supertrend + MACD) | -0.09% | 41.5% | 3.5% | **Loss**: Multi-indicator lag and overfitting |
| **Liquidity Sweep Re-Entry** | Hardik Sharma (Price Action) | 5m / 15m | +18.0% | 62.0% | 4.0% | **Profitable**: Exploits institutional absorption |

### B. Institutional Liquidity Sweep Setup
Rather than buying breakouts (which fail 80% of the time in choppy markets), trade institutional stop runs:
1. **Identify Key Support**: Locate a previous day low, swing low, or bottom central pivot (BC).
2. **Detect the Sweep**: Price punches 1% to 2% below support, flushing retail stops and trapping late breakdown sellers.
3. **Volume Absorption**: A surge in volume appears on the sweep bar, demonstrating institutional buyers absorbing supply.
4. **Confirmation Close**: Wait for a candle to close back inside or above the support zone.
5. **Execution**: Enter at the close of the confirmation candle.
6. **Hard Invalidation**: Place the stop loss tightly below the lowest wick of the sweep.
7. **Target**: Minimum 1:2 to 1:3 risk-to-reward ratio.

### C. Central Pivot Range (CPR) Width Analysis
The distance between Top Central (TC) and Bottom Central (BC) indicates the day's expected volatility profile:
- **Narrow CPR (Width <= 0.35%)**: Signals energy compression. High probability of a directional trend day. Suitable for breakout expansion setups.
- **Average CPR (0.35% - 0.90%)**: Normal trading range with standard pivot support/resistance tests.
- **Wide CPR (Width >= 0.90%)**: Signals an exhausted range. High probability of sideways chop. Avoid breakout trades; fade extremes back toward the central pivot.

### D. Time-of-Day Discipline
- **9:15 AM - 9:45 AM**: Opening auction volatility and institutional positioning. Do not take mechanical entries.
- **9:45 AM - 11:30 AM**: Prime morning execution window for liquidity sweeps and CPR breakouts.
- **11:30 AM - 1:30 PM**: European open transition and midday volume dip. Consolidations form.
- **1:30 PM - 3:15 PM**: Afternoon momentum continuation and closing auction flows.

---

## 3. The NotebookLM Strategy Extraction & Backtest Pipeline

Both Ray Fu and Day Trading Guruji utilize Google NotebookLM as an automated research assistant to extract rules from unstructured sources and test them mathematically.

### The 4-Step Pipeline:
1. **Source Ingestion**:
   - Copy any YouTube trading tutorial link, earnings call recording, or corporate filing PDF.
   - Paste the link into Google NotebookLM (notebooklm.google.com) as a new source.
2. **Rule Extraction Prompt**:
   - Send the following prompt to NotebookLM:
     Act as a senior quantitative trading researcher. Extract the complete trading rules from this source: 1. Target asset class and recommended chart timeframe. 2. Indicator parameters (exact periods, lengths, and multipliers). 3. Precise Long entry conditions and confirmations. 4. Precise Short entry conditions and confirmations. 5. Hard stop-loss placement formula. 6. Profit target determination and minimum risk-to-reward ratio. 7. Invalidation and early exit criteria. Format the output as a numbered, deterministic rulebook.
3. **Code Generation Prompt**:
   - Take the extracted rules and send them to an LLM:
     You are a Pine Script v5 and Python quantitative developer. Convert these exact trading rules into: 1. An error-free TradingView Pine Script v5 strategy with inputs for risk-to-reward and trailing stops. 2. A modular Python backtest function incorporating 1% ATR volatility position sizing and 0.1% slippage per leg.
4. **Validation**:
   - Paste the generated Pine Script into TradingView Pine Editor or run it through our backend backtest engine (/api/backtest).
   - Discard any strategy that fails out-of-sample walk-forward tests or displays negative risk-adjusted returns after slippage and Indian STT/GST taxes.

---

## 4. System Implementation Status in Our Agent

- **src/analysis/personas.py**: Added evaluate_ray_fu and evaluate_day_trading_guruji, expanding the investor evaluation consensus to a 5-member council.
- **src/agents/research_team.py**: Integrated run_maker_checker_audit to mathematically verify every research report before presentation.
- **src/analysis/order_flow.py**: Provides liquidity sweep detection (detect_liquidity_sweeps) and Wyckoff volume spread analysis (analyze_wyckoff_vsa).
- **src/engine/constitution.py & src/engine/risk_tiers.py**: Enforces the 1.5% single-trade risk mandate, hard stop loss, and the 10% portfolio drawdown circuit breaker.
- **static/index.html**: Features the 5-council member evaluation cards and the interactive Playbook & Creator Hub tab with live calculators and prompt generators.
