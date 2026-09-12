# Bharat Trade Agent (NSE / BSE)

An autonomous Indian equity research and trading workstation with mobile-responsive UI, multi-agent debate architecture, strategy backtesting, and Angel One SmartAPI integration.

## Features
- **Real-Time Indian Equities Data:** Live quotes, 52-week ranges, technicals, and sector classifications for NSE/BSE.
- **Top AI Buy Recommendations:** Automated screener finding high-conviction buy setups across liquid Nifty bluechips.
- **Master Strategy Council (5 Frameworks):** Evaluates stocks across Warren Buffett (Moat), Benjamin Graham (Margin of Safety), Peter Lynch (GARP), Ray Fu (1% ATR Volatility Sizing & Quant Regimes), and Day Trading Guruji (CPR & Liquidity Sweeps).
- **Ray Fu Maker-Checker Adversarial Loop:** Deterministic audit verifying mathematics (risk-to-reward >= 1.5:1), validating exchange filings, and tagging unconfirmed data with `[UNVERIFIED]`.
- **Day Trading Guruji Price Action Engine:** False-breakdown sell-side liquidity sweep (SSL) detection, CPR width breakout/range filters, and retail indicator reality checks.
- **NotebookLM AI Backtest Pipeline:** Seamless 4-step workflow to convert any YouTube video or corporate filing PDF into quantitative TradingView Pine Script and Python backtest logic.
- **Tactical Battle Plan:** Pullback vs. breakout entry bands, relative volume (RVOL) confluence, and Freqtrade positive trailing stops.
- **Interactive Playbook & Creator Studio:** Dedicated UI hub with interactive 1% ATR volatility position sizer, indicator backtest comparisons, and one-click prompt copy cards.
- **Telegram Phone Alerts:** One-click trade alerts and morning/evening daily market briefings pushed straight to your Telegram app.

## Quickstart (Local Run)
```bash
git clone https://github.com/nishantjainjain3-glitch/bharat-trade-agent.git
cd bharat-trade-agent
pip install -r requirements.txt
python run.py
```
Open `http://localhost:8000` on your desktop or `http://<your-ip>:8000` on your phone.

## Remote Access on Phone
To open the dashboard on your phone away from home over 4G/5G:
```bash
python run_tunnel.py
```

## Cloud Deployment (24/7 Hosting)
This repository includes a `render.yaml` and `Procfile` ready for free 24/7 deployment on **Render**, **Railway**, or **Fly.io**.
