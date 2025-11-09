import ccxt # Cryptocurrency exchange API library
import os # Environment variable and file system access
import math # Mathematical operations
import time # Time delay and timestamps
import pandas as pd # Data analysis and manipulation
import requests # HTTP requests
import json # JSON data processing
import sqlite3 # Local database
from dotenv import load_dotenv # Load environment variables
load_dotenv() # Load environment variables from .env file
from openai import OpenAI # OpenAI API access
from datetime import datetime # Date and time processing

# ===== Settings and Initialization =====
api_key = os.getenv("BINANCE_API_KEY") # Binance API key
secret = os.getenv("BINANCE_SECRET_KEY") # Binance secret key

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # Adhere to API rate limits
    'options': {
        'defaultType': 'future', # Set to futures trading
        'adjustForTimeDifference': True # Adjust for time difference
    }
})
symbol = "BTC/USDT"

# Initialize OpenAI API client
client = OpenAI()

# SERP API settings (for news data collection)
serp_api_key = os.getenv("SERP_API_KEY") # SERP API key

# SQLite database settings
DB_FILE = "bitcoin_trading.db" # Database filename

# ===== Database Related Functions =====
def setup_database():
    """
    Create database and necessary tables
    
    Creates tables to store trade history and AI analysis results.
    - trades: All trade information (entry price, exit price, P/L, etc.)
    - ai_analysis: AI's analysis results and recommendations
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Trade history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,          -- Trade start time
        action TEXT NOT NULL,             -- long or short
        entry_price REAL NOT NULL,        -- Entry price
        amount REAL NOT NULL,             -- Trade amount (BTC)
        leverage INTEGER NOT NULL,        -- Leverage multiplier
        sl_price REAL NOT NULL,           -- Stop-loss price
        tp_price REAL NOT NULL,           -- Take-profit price
        sl_percentage REAL NOT NULL,      -- Stop-loss percentage
        tp_percentage REAL NOT NULL,      -- Take-profit percentage
        position_size_percentage REAL NOT NULL, -- Position size relative to capital
        investment_amount REAL NOT NULL,  -- Investment amount (USDT)
        status TEXT DEFAULT 'OPEN',       -- Trade status (OPEN/CLOSED)
        exit_price REAL,                  -- Exit price
        exit_timestamp TEXT,              -- Exit time
        profit_loss REAL,                 -- Profit/Loss (USDT)
        profit_loss_percentage REAL       -- Profit/Loss percentage
    )
    ''')
    
    # AI analysis results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,                -- Analysis time
        current_price REAL NOT NULL,            -- Price at analysis time
        direction TEXT NOT NULL,                -- Recommended direction (LONG/SHORT/NO_POSITION)
        recommended_position_size REAL NOT NULL, -- Recommended position size
        recommended_leverage INTEGER NOT NULL,     -- Recommended leverage
        stop_loss_percentage REAL NOT NULL,       -- Recommended stop-loss percentage
        take_profit_percentage REAL NOT NULL,     -- Recommended take-profit percentage
        reasoning TEXT NOT NULL,                   -- Explanation of analysis reasoning
        trade_id INTEGER,                          -- Linked trade ID
        FOREIGN KEY (trade_id) REFERENCES trades (id) -- Foreign key setup
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup complete")

def save_ai_analysis(analysis_data, trade_id=None):
    """
    Save AI analysis results to the database
    
    Parameters:
        analysis_data (dict): AI analysis result data
        trade_id (int, optional): Linked trade ID
        
    Returns:
        int: The ID of the created analysis record
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO ai_analysis (
        timestamp, 
        current_price, 
        direction, 
        recommended_position_size, 
        recommended_leverage, 
        stop_loss_percentage, 
        take_profit_percentage, 
        reasoning,
        trade_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(), # Current time
        analysis_data.get('current_price', 0), # Current price
        analysis_data.get('direction', 'NO_POSITION'), # Recommended direction
        analysis_data.get('recommended_position_size', 0), # Recommended position size
        analysis_data.get('recommended_leverage', 0), # Recommended leverage
        analysis_data.get('stop_loss_percentage', 0), # Stop-loss percentage
        analysis_data.get('take_profit_percentage', 0), # Take-profit percentage
        analysis_data.get('reasoning', ''), # Analysis reasoning
        trade_id # Linked trade ID
    ))
    
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return analysis_id

def save_trade(trade_data):
    """
    Save trade information to the database
    
    Parameters:
        trade_data (dict): Trade information data
        
    Returns:
        int: The ID of the created trade record
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO trades (
        timestamp,
        action,
        entry_price,
        amount,
        leverage,
        sl_price,
        tp_price,
        sl_percentage,
        tp_percentage,
        position_size_percentage,
        investment_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(), # Entry time
        trade_data.get('action', ''), # Position direction
        trade_data.get('entry_price', 0), # Entry price
        trade_data.get('amount', 0), # Trade amount
        trade_data.get('leverage', 0), # Leverage
        trade_data.get('sl_price', 0), # Stop-loss price
        trade_data.get('tp_price', 0), # Take-profit price
        trade_data.get('sl_percentage', 0), # Stop-loss percentage
        trade_data.get('tp_percentage', 0), # Take-profit percentage
        trade_data.get('position_size_percentage', 0), # Position size relative to capital
        trade_data.get('investment_amount', 0) # Investment amount
    ))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def update_trade_status(trade_id, status, exit_price=None, exit_timestamp=None, profit_loss=None, profit_loss_percentage=None):
    """
    Updates the trade status
    
    Parameters:
        trade_id (int): The ID of the trade to update
        status (str): The new status ('OPEN' or 'CLOSED')
        exit_price (float, optional): The exit price
        exit_timestamp (str, optional): The exit time
        profit_loss (float, optional): The P/L amount
        profit_loss_percentage (float, optional): The P/L percentage
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Dynamically construct the SQL update query
    update_fields = ["status = ?"]
    update_values = [status]
    
    # Include only the provided fields in the update
    if exit_price is not None:
        update_fields.append("exit_price = ?")
        update_values.append(exit_price)
    
    if exit_timestamp is not None:
        update_fields.append("exit_timestamp = ?")
        update_values.append(exit_timestamp)
    
    if profit_loss is not None:
        update_fields.append("profit_loss = ?")
        update_values.append(profit_loss)
    
    if profit_loss_percentage is not None:
        update_fields.append("profit_loss_percentage = ?")
        update_values.append(profit_loss_percentage)
    
    update_sql = f"UPDATE trades SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(trade_id)
    
    cursor.execute(update_sql, update_values)
    conn.commit()
    conn.close()

def get_latest_open_trade():
    """
    Fetches the most recent open trade information
    
    Returns:
        dict: Trade information or None (if no open trades)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, action, entry_price, amount, leverage, sl_price, tp_price
    FROM trades
    WHERE status = 'OPEN'
    ORDER BY timestamp DESC  -- Most recent trade first
    LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    # If a result is found, convert it to a dictionary and return
    if result:
        return {
            'id': result[0],
            'action': result[1],
            'entry_price': result[2],
            'amount': result[3],
            'leverage': result[4],
            'sl_price': result[5],
            'tp_price': result[6]
        }
    return None # No open trades

def get_trade_summary(days=7):
    """
    Fetches a summary of trades for the specified number of days
    
    Parameters:
        days (int): The period (in days) to summarize
        
    Returns:
        dict: Trade summary information or None
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT 
        COUNT(*) as total_trades,                  -- Total number of trades
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades, -- Number of winning trades
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,   -- Number of losing trades
        SUM(profit_loss) as total_profit_loss,               -- Total P/L
        AVG(profit_loss_percentage) as avg_profit_loss_percentage -- Average P/L percentage
    FROM trades
    WHERE exit_timestamp IS NOT NULL  -- Only closed trades
    AND timestamp >= datetime('now', ?) -- Only trades within the specified days
    ''', (f'-{days} days',))
    
    result = cursor.fetchone()
    conn.close()
    
    # If a result is found, convert it to a dictionary and return
    if result:
        return {
            'total_trades': result[0] or 0,
            'winning_trades': result[1] or 0,
            'losing_trades': result[2] or 0,
            'total_profit_loss': result[3] or 0,
            'avg_profit_loss_percentage': result[4] or 0
        }
    return None

def get_historical_trading_data(limit=10):
    """
    Fetches historical trade history and related AI analysis results
    
    Parameters:
        limit (int): The maximum number of trade records to fetch
        
    Returns:
        list: A list of dictionaries containing trade and analysis data
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing results by column name
    cursor = conn.cursor()
    
    # Query for completed trade history along with related AI analysis (using LEFT JOIN)
    cursor.execute('''
    SELECT 
        t.id as trade_id,
        t.timestamp as trade_timestamp,
        t.action,
        t.entry_price,
        t.exit_price,
        t.amount,
        t.leverage,
        t.sl_price,
        t.tp_price,
        t.sl_percentage,
        t.tp_percentage,
        t.position_size_percentage,
        t.status,
        t.profit_loss,
        t.profit_loss_percentage,
        a.id as analysis_id,
        a.reasoning,
        a.direction,
        a.recommended_leverage,
        a.recommended_position_size,
        a.stop_loss_percentage,
        a.take_profit_percentage
    FROM 
        trades t
    LEFT JOIN 
        ai_analysis a ON t.id = a.trade_id
    WHERE 
        t.status = 'CLOSED'  -- Only completed trades
    ORDER BY 
        t.timestamp DESC  -- Most recent trades first
    LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    
    # Convert results to a list of dictionaries
    historical_data = []
    for row in results:
        historical_data.append({k: row[k] for k in row.keys()})
    
    conn.close()
    return historical_data

def get_performance_metrics():
    """
    Calculates trading performance metrics
    
    This function calculates overall and directional (long/short) performance indicators, including:
    - Total number of trades
    - Win rate
    - Average return
    - Max profit/loss
    - Directional performance
    
    Returns:
        dict: Performance metrics data
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Query for overall trade performance
    cursor.execute('''
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss_percentage) as avg_profit_loss_percentage,
        MAX(profit_loss_percentage) as max_profit_percentage,
        MIN(profit_loss_percentage) as max_loss_percentage,
        AVG(CASE WHEN profit_loss > 0 THEN profit_loss_percentage ELSE NULL END) as avg_win_percentage,
        AVG(CASE WHEN profit_loss < 0 THEN profit_loss_percentage ELSE NULL END) as avg_loss_percentage
    FROM trades
    WHERE status = 'CLOSED'
    ''')
    
    overall_metrics = cursor.fetchone()
    
    # Query for directional (long/short) performance
    cursor.execute('''
    SELECT 
        action,
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss_percentage) as avg_profit_loss_percentage
    FROM trades
    WHERE status = 'CLOSED'
    GROUP BY action
    ''')
    
    directional_metrics = cursor.fetchall()
    
    conn.close()
    
    # Construct the results
    metrics = {
        "overall": {
            "total_trades": overall_metrics[0] or 0,
            "winning_trades": overall_metrics[1] or 0,
            "losing_trades": overall_metrics[2] or 0,
            "total_profit_loss": overall_metrics[3] or 0,
            "avg_profit_loss_percentage": overall_metrics[4] or 0,
            "max_profit_percentage": overall_metrics[5] or 0,
            "max_loss_percentage": overall_metrics[6] or 0,
            "avg_win_percentage": overall_metrics[7] or 0,
            "avg_loss_percentage": overall_metrics[8] or 0
        },
        "directional": {}
    }
    
    # Calculate win rate
    if metrics["overall"]["total_trades"] > 0:
        metrics["overall"]["win_rate"] = (metrics["overall"]["winning_trades"] / metrics["overall"]["total_trades"]) * 100
    else:
        metrics["overall"]["win_rate"] = 0
    
    # Add directional metrics
    for row in directional_metrics:
        action = row[0] # 'long' or 'short'
        total = row[1] or 0
        winning = row[2] or 0
        
        direction_metrics = {
            "total_trades": total,
            "winning_trades": winning,
            "losing_trades": row[3] or 0,
            "total_profit_loss": row[4] or 0,
            "avg_profit_loss_percentage": row[5] or 0,
            "win_rate": (winning / total * 100) if total > 0 else 0
        }
        
        metrics["directional"][action] = direction_metrics
    
    return metrics

# ===== Data Collection Functions =====
def fetch_multi_timeframe_data():
    """
    Fetches price data for multiple timeframes
    
    For each timeframe (15m, 1h, 4h), fetches the following data:
    - Date/Time
    - Open
    - High
    - Low
    - Close
    - Volume
    
    Returns:
        dict: DataFrame data per timeframe
    """
    # Timeframe data collection settings
    timeframes = {
        "15m": {"timeframe": "15m", "limit": 96}, # 24 hours (15m * 96)
        "1h": {"timeframe": "1h", "limit": 48},   # 48 hours (1h * 48)
        "4h": {"timeframe": "4h", "limit": 30}    # 5 days (4h * 30)
    }
    
    multi_tf_data = {}
    
    # Collect data for each timeframe
    for tf_name, tf_params in timeframes.items():
        try:
            # Fetch OHLCV data (Open, High, Low, Close, Volume)
            ohlcv = exchange.fetch_ohlcv(
                symbol, 
                timeframe=tf_params["timeframe"], 
                limit=tf_params["limit"]
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime format
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Store in the results dictionary
            multi_tf_data[tf_name] = df
            print(f"Collected {tf_name} data: {len(df)} candles")
        except Exception as e:
            print(f"Error fetching {tf_name} data: {e}")
    
    return multi_tf_data

def fetch_bitcoin_news():
    """
    Fetches the latest news related to Bitcoin
    
    Uses SERP API to fetch the latest 10 news articles related to Bitcoin from Google News.
    
    Returns:
        list: Latest news article information (includes only title and date)
    """
    try:
        # SERP API request settings
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_news", # Google News search
            "q": "bitcoin",          # Search query: bitcoin
            "gl": "us",              # Country: US
            "hl": "en",              # Language: English
            "api_key": serp_api_key  # API key
        }
        
        # Send API request
        response = requests.get(url, params=params)
        
        # Check and process response
        if response.status_code == 200:
            data = response.json()
            news_results = data.get("news_results", [])
            
            # Extract only the 10 latest news items, including only title and date
            recent_news = []
            for i, news in enumerate(news_results[:10]):
                news_item = {
                    "title": news.get("title", ""),
                    "date": news.get("date", "")
                }
                recent_news.append(news_item)
            
            print(f"Collected {len(recent_news)} recent news articles (title and date only)")
            return recent_news
        else:
            print(f"Error fetching news: Status code {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# ===== Position Management Functions =====
def handle_position_closure(current_price, side, amount, current_trade_id=None):
    """
    Updates the database and displays results when a position is closed
    
    Parameters:
        current_price (float): The current price (exit price)
        side (str): Position direction ('long' or 'short')
        amount (float): Position amount
        current_trade_id (int, optional): Current trade ID
    """
    # If trade ID is not provided, fetch the latest open trade
    if current_trade_id is None:
        latest_trade = get_latest_open_trade()
        if latest_trade:
            current_trade_id = latest_trade['id']
    
    if current_trade_id:
        # Get the most recent open trade
        latest_trade = get_latest_open_trade()
        if latest_trade:
            entry_price = latest_trade['entry_price']
            action = latest_trade['action']
            
            # Calculate P/L (differs by direction)
            if action == 'long':
                # For long positions: (exit_price - entry_price) * amount
                profit_loss = (current_price - entry_price) * amount
                profit_loss_percentage = (current_price / entry_price - 1) * 100
            else: # 'short'
                # For short positions: (entry_price - exit_price) * amount
                profit_loss = (entry_price - current_price) * amount
                profit_loss_percentage = (1 - current_price / entry_price) * 100
                
            # Update trade status
            update_trade_status(
                current_trade_id,
                'CLOSED', # Change status to 'CLOSED'
                exit_price=current_price,
                exit_timestamp=datetime.now().isoformat(),
                profit_loss=profit_loss,
                profit_loss_percentage=profit_loss_percentage
            )
            
            # Print results
            print(f"\n=== Position Closed ===")
            print(f"Entry: ${entry_price:,.2f}")
            print(f"Exit: ${current_price:,.2f}")
            print(f"P/L: ${profit_loss:,.2f} ({profit_loss_percentage:.2f}%)")
            print("=======================")
            
            # Display recent trade summary
            summary = get_trade_summary(days=7)
            if summary:
                print("\n=== 7-Day Trading Summary ===")
                print(f"Total Trades: {summary['total_trades']}")
                print(f"Win/Loss: {summary['winning_trades']}/{summary['losing_trades']}")
                if summary['total_trades'] > 0:
                    win_rate = (summary['winning_trades'] / summary['total_trades']) * 100
                    print(f"Win Rate: {win_rate:.2f}%")
                print(f"Total P/L: ${summary['total_profit_loss']:,.2f}")
                print(f"Avg P/L %: {summary['avg_profit_loss_percentage']:.2f}%")
                print("=============================")

# ===== Main Program Start =====
print("\n=== Bitcoin Trading Bot Started ===")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Trading Pair:", symbol)
print("Dynamic Leverage: AI Optimized")
print("Dynamic SL/TP: AI Optimized")
print("Multi Timeframe Analysis: 15m, 1h, 4h")
print("News Sentiment Analysis: Enabled")
print("Historical Performance Learning: Enabled")
print("Database Logging: Enabled")
print("===================================\n")

# Database setup
setup_database()

# ===== Main Trading Loop =====
while True:
    try:
        # Fetch current time and price
        current_time = datetime.now().strftime('%H:%M:%S')
        current_price = exchange.fetch_ticker(symbol)['last']
        print(f"\n[{current_time}] Current BTC Price: ${current_price:,.2f}")

        # ===== 1. Check Current Position =====
        current_side = None # Current position side (long/short/None)
        amount = 0 # Position amount
        
        # Fetch current positions from Binance
        positions = exchange.fetch_positions([symbol])
        for position in positions:
            if position['symbol'] == 'BTC/USDT:USDT':
                amt = float(position['info']['positionAmt'])
                if amt > 0:
                    current_side = 'long'
                    amount = amt
                elif amt < 0:
                    current_side = 'short'
                    amount = abs(amt)
        
        # Fetch current trade info from database
        current_trade = get_latest_open_trade()
        current_trade_id = current_trade['id'] if current_trade else None
        
        # ===== 2. Handle Case: Position Exists =====
        if current_side:
            print(f"Current Position: {current_side.upper()} {amount} BTC")
            
            # If position exists but no record in DB (e.g., bot restart)
            if not current_trade:
                # Create and save temporary trade info to DB
                temp_trade_data = {
                    'action': current_side,
                    'entry_price': current_price, # Set temporarily with current price
                    'amount': amount,
                    'leverage': 1, # Default value
                    'sl_price': 0,
                    'tp_price': 0,
                    'sl_percentage': 0,
                    'tp_percentage': 0,
                    'position_size_percentage': 0,
                    'investment_amount': 0
                }
                current_trade_id = save_trade(temp_trade_data)
                print("Creating new trade record (for existing position)")
        
        # ===== 3. Handle Case: No Position =====
        else:
            # If a position previously existed and an open trade is in DB (position was closed)
            if current_trade:
                handle_position_closure(current_price, current_trade['action'], current_trade['amount'], current_trade_id)
            
            # If no position, cancel any remaining open orders
            try:
                open_orders = exchange.fetch_open_orders(symbol)
                if open_orders:
                    for order in open_orders:
                        exchange.cancel_order(order['id'], symbol)
                    print("Cancelled remaining open orders for", symbol)
                else:
                    print("No remaining open orders to cancel.")
            except Exception as e:
                print("Error cancelling orders:", e)
                
            # Wait a moment then start market analysis
            time.sleep(5)
            print("No position. Analyzing market...")

            # ===== 4. Collect Market Data =====
            # Collect multi-timeframe chart data
            multi_tf_data = fetch_multi_timeframe_data()
            
            # Collect recent Bitcoin news
            recent_news = fetch_bitcoin_news()
            
            # Fetch historical trading data and AI analysis results
            historical_trading_data = get_historical_trading_data(limit=10) # Recent 10 trades
            
            # Calculate overall trading performance metrics
            performance_metrics = get_performance_metrics()
            
            # ===== 5. Prepare Data for AI Analysis =====
            market_analysis = {
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "timeframes": {},
                "recent_news": recent_news,
                "historical_trading_data": historical_trading_data,
                "performance_metrics": performance_metrics
            }
            
            # Convert each timeframe's data to dict and store
            for tf_name, df in multi_tf_data.items():
                market_analysis["timeframes"][tf_name] = df.to_dict(orient="records")
            
            # ===== 6. Request AI Trading Decision =====
            # Set system prompt for AI analysis
            system_prompt = """
You are an expert crypto trading analyst. Your goal is to analyze market data and historical performance to determine a trading decision based on strict risk management rules.

**Core Principles:**
1.  **Warren Buffett's Rule #1:** Never lose money. Prioritize capital preservation.
2.  **Conviction Threshold:** Only recommend "LONG" or "SHORT" if conviction is 55% or higher.
3.  **Default Action:** If conviction is below 55%, you MUST return "NO_POSITION".

**Analysis Process:**

1.  **Review Historical Performance (Learning):**
    * Analyze the provided `historical_trading_data` (recent trades) and `performance_metrics`.
    * What worked? What failed? (e.g., "Recent high-leverage trades failed," "SL was too tight").
    * Adjust your current strategy based on these lessons. Be more conservative if recent trades lost money.

2.  **Analyze Market Conditions:**
    * **Multi-Timeframe (15m, 1h, 4h):** Identify the short-term momentum, intermediate trend, and long-term bias.
    * **News Sentiment:** Is the sentiment from `recent_news` bullish, bearish, or neutral?
    * **Key Levels:** Identify clear support and resistance.
    * **Volatility:** Is volatility high or low?

3.  **Formulate Trade Plan & Risk Management:**
    * **Direction & Conviction (p):** Determine direction (LONG/SHORT) and your win probability (p) (e.g., 0.65 for 65%).
    * **SL/TP & Win/Loss Ratio (b):**
        * Set a technical `stop_loss_percentage` (e.g., 0.015 for 1.5%) that invalidates your thesis.
        * Set a realistic `take_profit_percentage` (e.g., 0.03 for 3%).
        * Calculate the win/loss ratio (b = TP / SL).
    * **Kelly Position Sizing (f*):**
        * Calculate f* using `p` and `b`: `f* = p - ((1-p) / b)`.
        * **Apply Half-Kelly Rule:** Your final `recommended_position_size` must be `f* / 2` (e.g., if f* is 0.4, return 0.2). This is mandatory to reduce volatility.
    * **Leverage:**
        * Use low leverage (1-3x) in high volatility or low conviction (55-65%) scenarios.
        * Use moderate leverage (3-8x) only in clear, low-volatility trends with high conviction (>70%).
        * Be more conservative if past high-leverage trades failed.

4.  **Provide Reasoning:**
    * Briefly explain *why* you chose the direction, SL, TP, and leverage.
    * Explicitly state how historical performance or news sentiment influenced your decision.

**Output Format:**
Your response MUST be ONLY a valid JSON object with these 6 fields. Do NOT include ```json or any other text. Return ONLY the raw JSON object.

{
"direction": "LONG" or "SHORT" or "NO_POSITION",
"recommended_position_size": [decimal, result of (f* / 2)],
"recommended_leverage": [integer],
"stop_loss_percentage": [decimal],
"take_profit_percentage": [decimal],
"reasoning": "Your concise analysis and justification, including how historical data was used."
}

"""
            
            # Call OpenAI API to request trading decision
            response = client.chat.completions.create(
                model="gpt-5-mini", # Use gpt-5-mini model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(market_analysis)}
                ]
            )

            # ===== 7. Process AI Response and Execute Trade =====
            try:
                # Extract content from API response
                response_content = response.choices[0].message.content.strip()
                print(f"Raw AI response: {response_content}") # For debugging
                
                # Clean up JSON format (remove code blocks)
                if response_content.startswith("```"):
                    # Extract content after the first newline and before the last ```
                    content_parts = response_content.split("\n", 1)
                    if len(content_parts) > 1:
                        response_content = content_parts[1]
                    # Remove the last ```
                    if "```" in response_content:
                        response_content = response_content.rsplit("```", 1)[0]
                    response_content = response_content.strip()
                
                # Parse JSON
                trading_decision = json.loads(response_content)
                
                # Print decision details
                print(f"AI Trading Decision:")
                print(f"Direction: {trading_decision['direction']}")
                print(f"Recommended Position Size: {trading_decision['recommended_position_size']*100:.1f}%")
                print(f"Recommended Leverage: {trading_decision['recommended_leverage']}x")
                print(f"Stop Loss Level: {trading_decision['stop_loss_percentage']*100:.2f}%")
                print(f"Take Profit Level: {trading_decision['take_profit_percentage']*100:.2f}%")
                print(f"Reasoning: {trading_decision['reasoning']}")
                
                # Save AI analysis results to database
                analysis_data = {
                    'current_price': current_price,
                    'direction': trading_decision['direction'],
                    'recommended_position_size': trading_decision['recommended_position_size'],
                    'recommended_leverage': trading_decision['recommended_leverage'],
                    'stop_loss_percentage': trading_decision['stop_loss_percentage'],
                    'take_profit_percentage': trading_decision['take_profit_percentage'],
                    'reasoning': trading_decision['reasoning']
                }
                analysis_id = save_ai_analysis(analysis_data)
                
                # Get AI recommended direction
                action = trading_decision['direction'].lower()
                
                # ===== 8. Execute Action Based on Trading Decision =====
                # If position should not be opened
                if action == "no_position":
                    print("It is best not to open a position in the current market situation.")
                    print(f"Reason: {trading_decision['reasoning']}")
                    time.sleep(60) # Wait 1 minute when no position
                    continue
                    
                # ===== 9. Calculate Investment Amount =====
                # Check current balance
                balance = exchange.fetch_balance()
                available_capital = balance['USDT']['free'] # Available USDT balance
                
                # Apply AI recommended position size percentage
                position_size_percentage = trading_decision['recommended_position_size']
                investment_amount = available_capital * position_size_percentage
                
                # Check minimum order amount (min 100 USDT)
                if investment_amount < 100:
                    investment_amount = 100
                    print(f"Adjusted to minimum order amount (100 USDT)")
                
                print(f"Investment Amount: {investment_amount:.2f} USDT")
                
                # ===== 10. Calculate Order Amount =====
                # BTC Amount = Investment Amount / Current Price, rounded up to 3 decimal places
                amount = math.ceil((investment_amount / current_price) * 1000) / 1000
                print(f"Order Amount: {amount} BTC")

                # ===== 11. Set Leverage =====
                # Set AI recommended leverage
                recommended_leverage = trading_decision['recommended_leverage']
                exchange.set_leverage(recommended_leverage, symbol)
                print(f"Leverage set to: {recommended_leverage}x")

                # ===== 12. Set Stop Loss / Take Profit =====
                # Get AI recommended SL/TP percentages
                sl_percentage = trading_decision['stop_loss_percentage']
                tp_percentage = trading_decision['take_profit_percentage']

                # ===== 13. Enter Position and Execute SL/TP Orders =====
                if action == "long":
                    # Market buy order
                    order = exchange.create_market_buy_order(symbol, amount)
                    entry_price = current_price
                    
                    # Calculate stop loss / take profit prices
                    sl_price = round(entry_price * (1 - sl_percentage), 2)   # Decrease by AI recommended percentage
                    tp_price = round(entry_price * (1 + tp_percentage), 2)   # Increase by AI recommended percentage
                    
                    # Create SL/TP orders
                    exchange.create_order(symbol, 'STOP_MARKET', 'sell', amount, None, {'stopPrice': sl_price})
                    exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', amount, None, {'stopPrice': tp_price})
                    
                    # Save trade data
                    trade_data = {
                        'action': 'long',
                        'entry_price': entry_price,
                        'amount': amount,
                        'leverage': recommended_leverage,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'sl_percentage': sl_percentage,
                        'tp_percentage': tp_percentage,
                        'position_size_percentage': position_size_percentage,
                        'investment_amount': investment_amount
                    }
                    trade_id = save_trade(trade_data)
                    
                    # Link AI analysis result with the trade
                    update_analysis_sql = "UPDATE ai_analysis SET trade_id = ? WHERE id = ?"
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(update_analysis_sql, (trade_id, analysis_id))
                    conn.commit()
                    conn.close()
                    
                    print(f"\n=== LONG Position Opened ===")
                    print(f"Entry: ${entry_price:,.2f}")
                    print(f"Stop Loss: ${sl_price:,.2f} (-{sl_percentage*100:.2f}%)")
                    print(f"Take Profit: ${tp_price:,.2f} (+{tp_percentage*100:.2f}%)")
                    print(f"Leverage: {recommended_leverage}x")
                    print(f"Reasoning: {trading_decision['reasoning']}")
                    print("===========================")

                elif action == "short":
                    # Market sell order
                    order = exchange.create_market_sell_order(symbol, amount)
                    entry_price = current_price
                    
                    # Calculate stop loss / take profit prices
                    sl_price = round(entry_price * (1 + sl_percentage), 2)   # Increase by AI recommended percentage
                    tp_price = round(entry_price * (1 - tp_percentage), 2)   # Decrease by AI recommended percentage
                    
                    # Create SL/TP orders
                    exchange.create_order(symbol, 'STOP_MARKET', 'buy', amount, None, {'stopPrice': sl_price})
                    exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', 'buy', amount, None, {'stopPrice': tp_price})
                    
                    # Save trade data
                    trade_data = {
                        'action': 'short',
                        'entry_price': entry_price,
                        'amount': amount,
                        'leverage': recommended_leverage,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'sl_percentage': sl_percentage,
                        'tp_percentage': tp_percentage,
                        'position_size_percentage': position_size_percentage,
                        'investment_amount': investment_amount
                    }
                    trade_id = save_trade(trade_data)
                    
                    # Link AI analysis result with the trade
                    update_analysis_sql = "UPDATE ai_analysis SET trade_id = ? WHERE id = ?"
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(update_analysis_sql, (trade_id, analysis_id))
                    conn.commit()
                    conn.close()
                    
                    print(f"\n=== SHORT Position Opened ===")
                    print(f"Entry: ${entry_price:,.2f}")
                    print(f"Stop Loss: ${sl_price:,.2f} (+{sl_percentage*100:.2f}%)")
                    print(f"Take Profit: ${tp_price:,.2f} (-{tp_percentage*100:.2f}%)")
                    print(f"Leverage: {recommended_leverage}x")
                    print(f"Reasoning: {trading_decision['reasoning']}")
                    print("============================")
                else:
                    print("Action is not 'long' or 'short', no order executed.")
                    
            except json.JSONDecodeError as e:
                print(f"JSON Parsing Error: {e}")
                print(f"AI Response: {response.choices[0].message.content}")
                time.sleep(30) # Wait and retry
                continue
            except Exception as e:
                print(f"Other Error: {e}")
                time.sleep(10)
                continue

        # ===== 14. Wait for a Period Before Next Loop =====
        time.sleep(60) # Main loop runs every 1 minute

    except Exception as e:
        print(f"\n Error: {e}")
        time.sleep(5)