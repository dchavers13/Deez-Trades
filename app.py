import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import time

st.set_page_config(page_title="Deez Trades", layout="wide")

st.title("📈 Deez Trades — QQQ Simulator & Charting App")

FALLBACK_CSV = """Datetime,Open,High,Low,Close,Volume
2025-09-08 09:30:00,473.15,474.22,472.80,473.55,1432100
2025-09-08 09:31:00,473.60,474.00,472.95,473.20,985400
2025-09-08 09:32:00,473.25,473.80,472.70,473.00,742100
2025-09-08 09:33:00,473.10,473.75,472.55,472.90,635200
"""

@st.cache_data(ttl=24*3600)
def get_qqq_data():
    try:
        qqq = yf.download("QQQ", period="5y", interval="1m")
        if qqq.empty:
            raise ValueError("Empty dataframe from Yahoo Finance")
        qqq.reset_index(inplace=True)
        return qqq
    except Exception as e:
        st.warning(f"⚠️ Yahoo Finance failed. Using fallback CSV. Error: {e}")
        from io import StringIO
        return pd.read_csv(StringIO(FALLBACK_CSV))

df = get_qqq_data()

if isinstance(df.columns, pd.MultiIndex):
    df.columns = ['_'.join([str(c) for c in col if c]) for col in df.columns.values]

rename_map = {}
for col in df.columns:
    if "Close" in col: rename_map[col] = "Close"
    elif "Open" in col: rename_map[col] = "Open"
    elif "High" in col: rename_map[col] = "High"
    elif "Low" in col: rename_map[col] = "Low"
    elif "Volume" in col: rename_map[col] = "Volume"
    elif col in ["Date", "Datetime", "index"]: rename_map[col] = "Datetime"

df.rename(columns=rename_map, inplace=True)

if "Datetime" not in df.columns:
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Datetime"}, inplace=True)

df['Datetime'] = pd.to_datetime(df['Datetime'])
df.sort_values('Datetime', inplace=True)
df.reset_index(drop=True, inplace=True)

df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
macd = MACD(df['Close'])
df['MACD'] = macd.macd()
df['Signal'] = macd.macd_signal()
df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
for w in [5, 10, 15, 20]:
    df[f"MA{w}"] = SMAIndicator(df['Close'], window=w).sma_indicator()

st.sidebar.header("🔧 Chart Controls")
show_rsi = st.sidebar.checkbox("RSI", True)
show_macd = st.sidebar.checkbox("MACD", True)
show_vwap = st.sidebar.checkbox("VWAP", True)
show_ma = st.sidebar.multiselect("Moving Averages", ["MA5","MA10","MA15","MA20"], ["MA5","MA10"])
simulation_mode = st.sidebar.checkbox("Simulation Mode", False)

def plot_chart(data, title="QQQ Candlesticks"):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data['Datetime'],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="Candlesticks"
    ))
    if show_vwap:
        fig.add_trace(go.Scatter(x=data['Datetime'], y=data['VWAP'], mode="lines", name="VWAP"))
    for ma in show_ma:
        fig.add_trace(go.Scatter(x=data['Datetime'], y=data[ma], mode="lines", name=ma))
    fig.update_layout(title=title, xaxis_rangeslider_visible=False, dragmode="drawline")
    return fig

if simulation_mode:
    st.subheader("🕹 Simulation Mode (1-second steps)")
    sim_data = df.head(60)
    chart = st.empty()
    for i in range(61, 121):
        sim_data = pd.concat([sim_data, df.iloc[[i]]])
        chart.plotly_chart(plot_chart(sim_data, "Simulated Playback"), use_container_width=True)
        time.sleep(1)
else:
    st.subheader("QQQ Chart")
    st.plotly_chart(plot_chart(df), use_container_width=True)

if show_rsi:
    st.subheader("RSI (14)")
    st.line_chart(df.set_index("Datetime")[["RSI"]])

if show_macd:
    st.subheader("MACD vs Signal")
    st.line_chart(df.set_index("Datetime")[["MACD","Signal"]])
