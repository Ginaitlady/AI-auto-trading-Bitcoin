import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ccxt 
import numpy as np
import time

# --- Page Setup (Default Light Theme) ---
st.set_page_config(
    page_title="Bitcoin Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Data Loading Functions (SQLite) ---

def get_trades_data():
    # Create a new connection for use in the current thread
    conn = sqlite3.connect("bitcoin_trading.db")
    query = """
    SELECT 
        id, timestamp, action, entry_price, exit_price, amount, leverage, 
        status, profit_loss, profit_loss_percentage, exit_timestamp
    FROM trades
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()  # Close connection
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if 'exit_timestamp' in df.columns:
        df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp'])
    return df

def get_ai_analysis_data():
    # Create a new connection for use in the current thread
    conn = sqlite3.connect("bitcoin_trading.db")
    query = """
    SELECT 
        id, timestamp, current_price, direction, 
        recommended_leverage, reasoning, trade_id
    FROM ai_analysis
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()  # Close connection
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# --- CCXT (Exchange) Data Loading ---
@st.cache_data(ttl=3600)  # 1-hour cache
def get_bitcoin_price_data(timeframe='1d', limit=90):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Failed to load Bitcoin price data: {e}")
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# --- Trading Performance Metrics Calculation ---
def calculate_trading_metrics(trades_df):
    if trades_df.empty:
        return {
            'total_return': 0, 'sharpe_ratio': 0, 'win_rate': 0, 'profit_factor': 0,
            'max_drawdown': 0, 'total_trades': 0, 'avg_profit_loss': 0, 'avg_holding_time': 0
        }
    
    # Filter only closed trades
    closed_trades = trades_df[trades_df['status'] == 'CLOSED']
    if closed_trades.empty:
        return {
            'total_return': 0, 'sharpe_ratio': 0, 'win_rate': 0, 'profit_factor': 0,
            'max_drawdown': 0, 'total_trades': 0, 'avg_profit_loss': 0, 'avg_holding_time': 0
        }
    
    # Total Return (Initial investment is estimated)
    total_profit_loss = closed_trades['profit_loss'].sum()
    # Estimate initial investment
    initial_investment = closed_trades.sort_values('timestamp').head(3)['entry_price'].mean() * \
                         closed_trades.sort_values('timestamp').head(3)['amount'].mean()
    if initial_investment < 100:  # If too small, set to a reasonable value
        initial_investment = 10000
    total_return = (total_profit_loss / initial_investment) * 100
    
    # Win Rate
    winning_trades = len(closed_trades[closed_trades['profit_loss'] > 0])
    total_trades = len(closed_trades)
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    # Profit Factor
    total_profit = closed_trades[closed_trades['profit_loss'] > 0]['profit_loss'].sum()
    total_loss = abs(closed_trades[closed_trades['profit_loss'] < 0]['profit_loss'].sum())
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    
    # Maximum Drawdown
    closed_trades_sorted = closed_trades.sort_values('timestamp')
    if 'profit_loss' in closed_trades_sorted.columns:
        closed_trades_sorted['cumulative_pl'] = closed_trades_sorted['profit_loss'].cumsum()
        closed_trades_sorted['peak'] = closed_trades_sorted['cumulative_pl'].cummax()
        closed_trades_sorted['drawdown'] = (closed_trades_sorted['peak'] - closed_trades_sorted['cumulative_pl']) / closed_trades_sorted['peak'].replace(0, np.nan)
        max_drawdown = closed_trades_sorted['drawdown'].max() * 100  # Convert to percentage
    else:
        max_drawdown = 0
    
    # Sharpe Ratio (based on daily returns)
    if 'profit_loss_percentage' in closed_trades.columns and len(closed_trades) > 1:
        returns = closed_trades['profit_loss_percentage'] / 100  # Convert to ratio
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Average Profit/Loss
    avg_profit_loss = closed_trades['profit_loss'].mean()
    
    # Average Holding Time
    if 'exit_timestamp' in closed_trades.columns and 'timestamp' in closed_trades.columns:
        # Check if both timestamp and exit_timestamp are datetime
        valid_timestamps = closed_trades.dropna(subset=['exit_timestamp'])
        if not valid_timestamps.empty:
            holding_times = (valid_timestamps['exit_timestamp'] - valid_timestamps['timestamp']).dt.total_seconds() / 3600  # in hours
            avg_holding_time = holding_times.mean()
        else:
            avg_holding_time = 0
    else:
        avg_holding_time = 0
    
    return {
        'total_return': total_return, 'sharpe_ratio': sharpe_ratio, 'win_rate': win_rate, 
        'profit_factor': profit_factor, 'max_drawdown': max_drawdown, 'total_trades': total_trades,
        'avg_profit_loss': avg_profit_loss, 'avg_holding_time': avg_holding_time
    }

# --- Sidebar ---
st.sidebar.title("Bitcoin Trading Bot 🤖")

# 1. Refresh Button
if st.sidebar.button("Force Refresh Data"):
    st.cache_data.clear()
    st.success("Data cache cleared.")

# 2. Auto-Refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh every 60s", value=False)

# 3. Time Filter
time_filter = st.sidebar.selectbox(
    "Select Period:", 
    ["All", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
)

# 4. Chart Type
chart_type = st.sidebar.radio("Price Chart Type", ["Line", "Candlestick"])


# --- Main Dashboard ---
try:
    # Load data
    trades_df = get_trades_data()
    ai_analysis_df = get_ai_analysis_data()
    btc_price_df = get_bitcoin_price_data()

    # Apply time filter
    now = datetime.now()
    if time_filter == "Last 24 Hours":
        filter_time = now - timedelta(days=1)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 1
    elif time_filter == "Last 7 Days":
        filter_time = now - timedelta(days=7)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 7
    elif time_filter == "Last 30 Days":
        filter_time = now - timedelta(days=30)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 30
    elif time_filter == "Last 90 Days":
        filter_time = now - timedelta(days=90)
        filtered_trades = trades_df[trades_df['timestamp'] > filter_time]
        chart_days = 90
    else:
        filtered_trades = trades_df
        chart_days = 90  # Default chart period when 'All' is selected

    # Calculate metrics
    metrics = calculate_trading_metrics(filtered_trades)

    # Current position
    open_trades = trades_df[trades_df['status'] == 'OPEN']
    has_open_position = len(open_trades) > 0
    current_position = open_trades.iloc[0] if has_open_position else None

    # Current BTC price
    current_btc_price = ai_analysis_df.iloc[0]['current_price'] if not ai_analysis_df.empty else btc_price_df.iloc[-1]['close']

    # --- Dashboard Title ---
    st.title("📈 Bitcoin Trading Dashboard")

    # --- Key Performance Indicators (st.metric) ---
    st.subheader("Key Performance Indicators (KPIs)")
    kpi_cols = st.columns(4)
    kpi_cols[0].metric(label="Total Return", value=f"{metrics['total_return']:.2f}%")
    kpi_cols[1].metric(label="Win Rate", value=f"{metrics['win_rate']:.1f}%", 
                       delta=f"{metrics['win_rate'] - 50:.1f} vs 50%")
    kpi_cols[2].metric(label="Profit Factor", value=f"{metrics['profit_factor']:.2f}", 
                       delta=f"{metrics['profit_factor'] - 1:.2f} vs 1.0")
    kpi_cols[3].metric(label="Sharpe Ratio", value=f"{metrics['sharpe_ratio']:.2f}")

    kpi_cols2 = st.columns(4)
    kpi_cols2[0].metric(label="Max Drawdown", value=f"{metrics['max_drawdown']:.2f}%", 
                        delta_color="inverse") # Larger number is worse
    kpi_cols2[1].metric(label="Total Closed Trades", value=f"{metrics['total_trades']}")
    kpi_cols2[2].metric(label="Avg Profit/Loss", value=f"{metrics['avg_profit_loss']:.2f} USDT")
    kpi_cols2[3].metric(label="Avg Holding Time", value=f"{metrics['avg_holding_time']:.1f} hours")
    
    st.divider()

    # --- Current Price & Position Summary (st.metric) ---
    pos_cols = st.columns(3)
    pos_cols[0].metric(label="Current BTC Price", value=f"${current_btc_price:,.2f}")
    
    if has_open_position:
        position_label = f"Current Position: {current_position['action'].upper()}"
        pos_cols[1].metric(label=position_label, 
                           value=f"{current_position['leverage']}x Leverage")
        
        # Calculate Unrealized P/L
        price_diff = current_btc_price - current_position['entry_price']
        if current_position['action'] == 'short':
            price_diff = -price_diff  # Short position profits if price drops
        
        unrealized_pl = price_diff * current_position['amount'] * current_position['leverage']
        unrealized_pl_pct = (unrealized_pl / (current_position['entry_price'] * current_position['amount'])) * 100
        
        pos_cols[2].metric(label="Unrealized P/L", 
                           value=f"${unrealized_pl:,.2f}", 
                           delta=f"{unrealized_pl_pct:.2f}%")
    else:
        pos_cols[1].metric(label="Current Position", value="None")
        pos_cols[2].metric(label="Unrealized P/L", value="$0.00")


    # --- BTC Price Chart & Trade Entries (Line / Candlestick) ---
    st.subheader("Bitcoin Price Chart & Trade Entries")

    # Filter price data for chart
    filtered_price_df = btc_price_df[btc_price_df['timestamp'] > (now - timedelta(days=chart_days))]

    fig = go.Figure()

    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=filtered_price_df['timestamp'],
            open=filtered_price_df['open'],
            high=filtered_price_df['high'],
            low=filtered_price_df['low'],
            close=filtered_price_df['close'],
            name='BTC Price'
        ))
        fig.update_layout(xaxis_rangeslider_visible=False) # Disable rangeslider for candlestick
    else:
        # 'Line' (Default)
        fig.add_trace(go.Scatter(
            x=filtered_price_df['timestamp'],
            y=filtered_price_df['close'],
            mode='lines',
            name='BTC Price',
            line=dict(color='gray', width=2),
            hovertemplate='<b>Price</b>: $%{y:,.2f}<br>'
        ))

    # Long (buy) points
    long_points = filtered_trades[filtered_trades['action'] == 'long']
    if not long_points.empty:
        fig.add_trace(go.Scatter(
            x=long_points['timestamp'],
            y=long_points['entry_price'],
            mode='markers',
            name='Long Entry',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            hovertemplate='<b>Long Entry</b><br>Price: $%{y:,.2f}<br>Date: %{x}<extra></extra>'
        ))

    # Short (sell) points
    short_points = filtered_trades[filtered_trades['action'] == 'short']
    if not short_points.empty:
        fig.add_trace(go.Scatter(
            x=short_points['timestamp'],
            y=short_points['entry_price'],
            mode='markers',
            name='Short Entry',
            marker=dict(color='red', size=10, symbol='triangle-down'),
            hovertemplate='<b>Short Entry</b><br>Price: $%{y:,.2f}<br>Date: %{x}<extra></extra>'
        ))

    # Exit points
    exit_points = filtered_trades[(filtered_trades['status'] == 'CLOSED') & (filtered_trades['exit_price'].notna())]
    if not exit_points.empty:
        fig.add_trace(go.Scatter(
            x=exit_points['exit_timestamp'] if 'exit_timestamp' in exit_points.columns else exit_points['timestamp'],
            y=exit_points['exit_price'],
            mode='markers',
            name='Exit',
            marker=dict(color='blue', size=8, symbol='circle'),
            hovertemplate='<b>Exit</b><br>Price: $%{y:,.2f}<br>Date: %{x}<extra></extra>'
        ))

    # Set chart layout
    fig.update_layout(
        title='Bitcoin Price & Trading Points',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        hovermode='x unified',
        height=500,
        legend_title_text='Legend'
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Trading Performance Charts ---
    st.subheader("Trading Performance")
    chart_cols = st.columns(2)

    with chart_cols[0]:
        closed_trades = filtered_trades[filtered_trades['status'] == 'CLOSED']
        if not closed_trades.empty:
            # Cumulative P/L Chart
            trades_sorted = closed_trades.sort_values('timestamp')
            trades_sorted['cumulative_pl'] = trades_sorted['profit_loss'].cumsum()
            
            fig_cum_pl = px.line(
                trades_sorted, x='timestamp', y='cumulative_pl',
                title='Cumulative Profit/Loss',
                labels={'timestamp': 'Date', 'cumulative_pl': 'P/L (USDT)'}
            )
            fig_cum_pl.update_layout(height=400)
            st.plotly_chart(fig_cum_pl, use_container_width=True)
        else:
            st.info("No closed trades to display.")

    with chart_cols[1]:
        if not filtered_trades.empty:
            # Trade Direction Distribution
            decisions = filtered_trades['action'].value_counts().reset_index()
            decisions.columns = ['Direction', 'Count']
            
            fig_pie = px.pie(
                decisions, values='Count', names='Direction',
                title='Trade Direction Distribution',
                color='Direction',
                color_discrete_map={'long': '#00CC96', 'short': '#EF553B'}
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No trades to display.")

    st.divider()

    # --- AI Analysis & Trade History (Tabs) ---
    tab1, tab2, tab3 = st.tabs(["📊 Recent Trades", "🧠 Latest AI Analysis", "📂 Open Position Details"])

    with tab1:
        st.subheader("Recent Trade History")
        if not filtered_trades.empty:
            # Prepare dataframe for display
            display_df = filtered_trades[['timestamp', 'action', 'entry_price', 'exit_price', 'status', 'profit_loss']].copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            display_df = display_df.rename(columns={
                'timestamp': 'Date', 'action': 'Direction', 'entry_price': 'Entry Price',
                'exit_price': 'Exit Price', 'status': 'Status', 'profit_loss': 'P/L'
            })
            st.dataframe(display_df, height=400, use_container_width=True)
        else:
            st.info("No trades in the selected time period.")

    with tab2:
        st.subheader("Latest AI Analysis")
        if not ai_analysis_df.empty:
            latest_analysis = ai_analysis_df.iloc[0]
            
            analysis_cols = st.columns(2)
            with analysis_cols[0]:
                direction = latest_analysis['direction']
                st.metric(label="AI Recommendation", value=direction)
                st.metric(label="Recommended Leverage", value=f"{latest_analysis['recommended_leverage']}x")
                st.caption(f"Analysis Time: {latest_analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

            with analysis_cols[1]:
                st.markdown("### Analysis Reasoning")
                st.info(latest_analysis['reasoning'])
        else:
            st.info("No AI analysis data available.")

    with tab3:
        st.subheader("Current Open Position Details")
        if has_open_position:
            entry_time = current_position['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            st.markdown(f"""
            - **Direction**: `{current_position['action'].upper()}`
            - **Entry Time**: `{entry_time}`
            - **Entry Price**: `${current_position['entry_price']:,.2f}`
            - **Leverage**: `{current_position['leverage']}x`
            - **Amount**: `{current_position['amount']} BTC`
            """)
        else:
            st.info("There is no open position currently.")
            
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(60)
        st.rerun()

except Exception as e:
    st.error(f"An error occurred while loading the dashboard: {str(e)}")
    st.exception(e)
    st.stop()