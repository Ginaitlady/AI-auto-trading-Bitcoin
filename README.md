AI Bitcoin Automated Trading Bot
An intelligent cryptocurrency trading bot powered by OpenAI's GPT models. It uses multi-timeframe analysis, news sentiment, and the Kelly Criterion (via a detailed system prompt) to execute trades on Binance Futures. Includes a real-time Streamlit dashboard for monitoring.

WARNING: Cryptocurrency trading involves substantial risk of loss. Never invest more than you can afford to lose. Past performance does not guarantee future results.

Table of Contents
Features

How It Works

Installation

Configuration

Usage

Project Structure

Dashboard

Trading Strategy

Risk Management

Troubleshooting

License

Disclaimer

Features
AI-Powered Decisions: Uses an OpenAI GPT model for comprehensive market analysis.

Multi-Timeframe Analysis: Fetches and analyzes 15m, 1h, and 4h chart data from Binance.

News Sentiment Analysis: Integrates real-time Google News headlines (via SerpAPI) into its decision-making.

Kelly Criterion Sizing: AI is instructed to use the Kelly Criterion to calculate optimal, risk-adjusted position sizes.

Dynamic Risk Management: AI dynamically determines leverage, Stop-Loss (SL), and Take-Profit (TP) levels for each trade.

Persistent Logging: Saves all trades and AI analysis reasoning to a local SQLite database (bitcoin_trading.db).

Historical Learning: The bot feeds its own past trade history (wins, losses, P/L) back to the AI, allowing it to "learn" from its performance.

Real-time Dashboard: A built-in Streamlit dashboard (dashboard.py) visualizes performance, trade history, and AI reasoning.

24/7 Cloud Operation: Designed to run continuously on a cloud server (e.g., AWS EC2) using nohup or tmux.

How It Works
Check Position: The bot (trading_bot.py) checks Binance for any existing open positions.

Collect Data: If no position is open, it gathers all necessary data:

Multi-timeframe OHLCV data (15m, 1h, 4h).

Recent Google News headlines for "bitcoin".

Historical trade performance and metrics from the SQLite DB.

AI Analysis: All collected data is sent to the OpenAI API with a detailed system_prompt. The AI analyzes the data, determines a conviction probability (p), and calculates an optimal win/loss ratio (b).

Kelly Sizing: The AI uses these values to calculate the Kelly Criterion position size (f*) and applies a Half-Kelly multiplier for safety.

Execute Trade:

If AI conviction is < 55%, it decides NO_POSITION and waits.

If conviction is high, it sets the recommended leverage and places a Market Order (LONG or SHORT).

Immediately after, it places the corresponding STOP_MARKET (for SL) and TAKE_PROFIT_MARKET (for TP) orders.

Log & Monitor: The trade and the AI's full reasoning are saved to the SQLite database. You can then run dashboard.py to monitor performance in real-time.


Project Structure
This project consists of two main Python files:

ai-bitcoin-trading-bot/
│
├── 📄 autotrade.py         # The main bot script that executes trades
├── 📄 steamlit_app.py      # The Streamlit dashboard for monitoring
├── 📄 requirements.txt     # Python dependencies
├── 📄 .env                 # API keys
├── 📄 bitcoin_trading.db   # SQLite database (auto-created on run)
└── 📄 README.md            # This file
Dashboard
The included Streamlit dashboard (steamlit_app.py) provides a real-time monitoring interface for your bot's performance.

![dashboard 2](https://github.com/user-attachments/assets/8fe10cd5-fed1-4f8f-8b01-c1c3dde90ab9)

Features:
Real-time KPIs: View Total Return, Win Rate, Profit Factor, and Sharpe Ratio.

Current Position: See your current open position, leverage, and Unrealized P/L.

Interactive Price Chart: A Plotly chart showing the BTC price along with your bot's Long Entry, Short Entry, and Exit points.

Performance Charts: See your cumulative P/L over time and a pie chart of LONG vs. SHORT trades.

AI Reasoning: A dedicated tab shows the exact reasoning from the AI for its latest trading decision.

Full Trade History: A filterable table of all past trades.

Trading Strategy
The bot's entire strategy is defined by the system_prompt variable in autotrade.py.

1. Analysis Components
Multi-Timeframe: 15m (short-term momentum), 1h (intermediate trend), 4h (long-term bias).

News Sentiment: AI reads news titles to determine if the market mood is bullish, bearish, or neutral.

Historical Learning: AI reviews its own past trades (from the DB) to see what worked (e.g., "high leverage trades lost money recently, I will be more conservative").

2. Kelly Criterion Position Sizing
The bot uses the Kelly Criterion to decide how much to invest in a trade.

Formula: f* = (p × b - q) / b

p: The AI's conviction (win probability), e.g., 65%.

q: Probability of failure (1 - p), e.g., 35%.

b: The win/loss ratio, (e.g., TP 3% / SL 1.5% = 2.0).

The bot then uses Half-Kelly (f* / 2) for a safer, more conservative position size.

Risk Management
Conviction Threshold: The AI is instructed not to trade (NO_POSITION) if its conviction is below 55%.

Sizing: Position size is strictly controlled by the Half-Kelly formula.

Leverage: AI dynamically selects leverage (1x-20x) based on volatility and conviction.

Order Types: The bot uses STOP_MARKET and TAKE_PROFIT_MARKET orders, which are placed on the exchange immediately after a position is opened to protect against losses.

Troubleshooting
Issue: "API key not found"
Solution: Ensure your .env file is in the same directory as autotrade.py and is correctly formatted (no quotes).

Issue: "Insufficient balance"
Solution:

Ensure you have USDT in your Binance Futures wallet (not Spot).

The code enforces a $100 minimum order. Ensure your available_capital * position_size_percentage is at least $100.

Issue: Error: binance {"code":-4061,"msg":"Order's position side does not match user's setting."}
Solution: This is the most common error. Your Binance account is in Hedge Mode. This bot requires One-way Mode.

Fix: In your Binance Futures trading interface, go to Preferences (top-right) -> Position Mode -> select One-way Mode.

Issue: "AI returns NO_POSITION constantly"
Solution: This is not an error; it's the bot working correctly. It means the AI's conviction is below 55%, and it is following Warren Buffett's rule: "Never lose money." It's protecting your capital by waiting for a clearer opportunity.
