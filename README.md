# 🤖 AI Bitcoin Automated Trading Bot  
An intelligent cryptocurrency trading bot powered by OpenAI's GPT models.  
It uses multi-timeframe analysis, news sentiment, and the Kelly Criterion (via a detailed system prompt)  
to execute trades on **Binance Futures**.  

> ⚠️ **WARNING:** Cryptocurrency trading involves substantial risk of loss.  
> Never invest more than you can afford to lose.  
> Past performance does not guarantee future results.

---

## 📘 Table of Contents
- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Dashboard](#dashboard)
- [Trading Strategy](#trading-strategy)
- [Risk Management](#risk-management)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## 🚀 Features
- **AI-Powered Decisions:** Uses an OpenAI GPT model for comprehensive market analysis.  
- **Multi-Timeframe Analysis:** Fetches and analyzes 15m, 1h, and 4h chart data from Binance.  
- **News Sentiment Analysis:** Integrates real-time Google News headlines (via SerpAPI).  
- **Kelly Criterion Sizing:** AI calculates optimal, risk-adjusted position sizes.  
- **Dynamic Risk Management:** Determines leverage, Stop-Loss (SL), and Take-Profit (TP) dynamically.  
- **Persistent Logging:** Saves trades and AI reasoning to a local SQLite database.  
- **Historical Learning:** AI learns from its own past trades (wins, losses, P/L).  
- **Real-time Dashboard:** Built-in Streamlit dashboard visualizes performance and reasoning.  
- **24/7 Cloud Operation:** Designed to run continuously on a cloud server (AWS EC2, etc.).

---

## ⚙️ How It Works
1. **Check Position:** The bot checks for any open Binance positions.  
2. **Collect Data:**  
   - Multi-timeframe OHLCV data (15m, 1h, 4h)  
   - Recent Google News headlines for *“bitcoin”*  
   - Historical trade data from SQLite DB  
3. **AI Analysis:**  
   - Data sent to OpenAI API with detailed `system_prompt`  
   - AI returns conviction probability (p) and win/loss ratio (b)  
4. **Kelly Sizing:**  
   - Uses Kelly Criterion: `f* = (p × b - q) / b`  
   - Applies **Half-Kelly** for conservative sizing  
5. **Execute Trade:**  
   - If conviction < 55% → `NO_POSITION`  
   - Else → Place **Market Order** (LONG/SHORT)  
   - Immediately sets **STOP_MARKET** and **TAKE_PROFIT_MARKET** orders  
6. **Log & Monitor:**  
   - Trade and reasoning saved to database  
   - View real-time stats via `streamlit_app.py`

---

## 📁 Project Structure

ai-bitcoin-trading-bot/
│
├── 📄 autotrade.py # Main bot script
├── 📄 streamlit_app.py # Streamlit dashboard
├── 📄 requirements.txt # Python dependencies
├── 📄 .env # API keys
├── 📄 bitcoin_trading.db # SQLite database (auto-created)
└── 📄 README.md # This file


---

## 📊 Dashboard
The included **Streamlit dashboard (`streamlit_app.py`)** provides real-time monitoring.

### Features:
- **Real-time KPIs:** Total Return, Win Rate, Profit Factor, Sharpe Ratio  
- **Current Position:** Open position, leverage, Unrealized P/L  
- **Interactive Chart:** BTC price with bot’s entries/exits (Plotly)  
- **Performance Charts:** Cumulative P/L and LONG vs SHORT distribution  
- **AI Reasoning Tab:** View exact reasoning for the latest trade  
- **Trade History:** Filterable table of all past trades  

---

## 🧠 Trading Strategy
The strategy logic is defined in the `system_prompt` of `autotrade.py`.

### Analysis Components:
- **Multi-Timeframe:**  
  - 15m → short-term momentum  
  - 1h → intermediate trend  
  - 4h → long-term bias  
- **News Sentiment:** Determines bullish/bearish/neutral tone  
- **Historical Learning:** Adjusts behavior based on recent success/failure patterns  

---

## 📈 Kelly Criterion Position Sizing
Formula: f* = (p × b - q) / b

Where:  
- `p`: Win probability (AI conviction)  
- `q`: Loss probability (1 - p)  
- `b`: Win/Loss ratio (e.g., TP 3% / SL 1.5% = 2.0)  

> The bot uses **Half-Kelly (f*/2)** for conservative sizing.

---

## 🛡️ Risk Management
- **Conviction Threshold:** Skip trades if conviction < 55%  
- **Position Size:** Controlled strictly by Half-Kelly formula  
- **Leverage:** Dynamically chosen (1x–20x) based on volatility  
- **Order Safety:** Uses `STOP_MARKET` and `TAKE_PROFIT_MARKET` to limit loss immediately  

---

## 🧩 Troubleshooting

| Issue | Solution |
|-------|-----------|
| **"API key not found"** | Ensure `.env` file exists and keys are correctly formatted (no quotes). |
| **"Insufficient balance"** | Ensure enough **USDT** in your **Futures Wallet**. The bot enforces a $100 minimum trade. |
| **Error: -4061 "Order's position side does not match user's setting."** | Your Binance account is in **Hedge Mode**. Switch to **One-way Mode** via *Preferences → Position Mode → One-way*. |
| **"AI returns NO_POSITION constantly"** | Not an error — AI’s conviction is below 55%, so it waits. This protects your capital. |

---

## ⚠️ Disclaimer
This software is for **educational and research purposes only**.  
Use it entirely at your own risk.  
The authors and contributors are **not responsible** for any financial losses or damages resulting from its use.

---
