# Bharat Trade Agent (NSE / BSE)

An autonomous Indian equity research and trading workstation with mobile-responsive UI, multi-agent debate architecture, strategy backtesting, and Angel One SmartAPI integration.

## Features
- **Real-Time Indian Equities Data:** Live quotes, 52-week ranges, technicals, and sector classifications for NSE/BSE.
- **Top AI Buy Recommendations:** Automated screener finding high-conviction buy setups across liquid Nifty bluechips.
- **Multi-Agent Research Engine:** Technical Analyst + Fundamental Analyst + Bull vs. Bear debate with entry, target, and stop-loss levels.
- **Live Indian Financial News:** Real-time headlines and exchange filings injected into research.
- **Macro Market Bar:** Live Nifty 50, Bank Nifty, USD/INR, and Brent Crude oil tracking.
- **Strategy Backtester:** Vectorized multi-year backtesting (EMA Crossovers, RSI Mean Reversion, Breakouts) with compounding equity curves and win rates.
- **Angel One SmartAPI Module:** Direct portfolio tracking, simulation paper trading mode, and order execution.
- **Mobile-First Web App:** Works across desktop browsers and mobile phones ("Add to Home Screen" PWA support).
- **Telegram Phone Alerts:** One-click trade alerts pushed straight to your Telegram app.

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
