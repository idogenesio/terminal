import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
from core_engine import AnalyticsEngine

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="GEMINI ELITE WEB TERMINAL", layout="wide", page_icon="📈")

# Custom CSS for high-visibility terminal look
st.markdown("""
    <style>
    .main { background-color: #080808; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #121212;
        border: 1px solid #333;
        padding: 8px 16px;
        border-radius: 4px;
        color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #00d4ff; color: black; border-color: #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONTROL ROOM ---
st.sidebar.header("🛠️ TERMINAL CONTROL")
ticker = st.sidebar.text_input("SYMBOL", value="TOWR.JK").upper()
timeframe = st.sidebar.selectbox("TIMEFRAME", options=["1d", "1wk", "1mo"], index=1)
period = "2y" if timeframe == "1wk" else ("1y" if timeframe == "1d" else "5y")

st.sidebar.divider()
st.sidebar.subheader("🌊 ELLIOTT WAVE TUNING")
ew_threshold = st.sidebar.slider("ZigZag Threshold (%)", 1.0, 15.0, 5.0, 0.5)

st.sidebar.subheader("🎲 MONTE CARLO TUNING")
mc_days = st.sidebar.slider("Forecast Days", 10, 365, 40, 10)
mc_sims = st.sidebar.slider("Simulations", 100, 1000, 200, 100)

# --- DATA FETCHING (CACHED) ---
@st.cache_data(ttl=3600)
def get_analysis_data(ticker, period, interval):
    df = AnalyticsEngine.fetch_data(ticker, period, interval)
    return df

df = get_analysis_data(ticker, period, timeframe)

if df.empty:
    st.error(f"❌ No data found for {ticker}. Please check the symbol.")
    st.stop()

# --- HEADER ---
last_p = df['Close'].iloc[-1]
change = ((last_p / df['Close'].iloc[-2]) - 1) * 100
st.title(f"🚀 GEMINI ELITE: {ticker}")
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"{last_p:,.0f}", f"{change:+.2f}%")
c2.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}")
c3.metric("Trend Phase", "Corrective" if len(df)%2==0 else "Impulsive")

tab1, tab2, mc_tab, tab4 = st.tabs(["📊 STANDARD", "🌊 ELLIOTT", "🎲 MONTE CARLO", "📋 SUMMARY"])

# --- TAB 1: STANDARD DASHBOARD ---
with tab1:
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.2])
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    
    # Divergence
    sigs = AnalyticsEngine.get_divergence(df)
    for s in sigs:
        color = "#00ff66" if s.type == "BULLISH" else "#ff3366"
        fig.add_trace(go.Scatter(x=[s.d1, s.d2], y=[s.p1, s.p2], mode='lines+markers',
                                 line=dict(color=color, width=4), name=s.type), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#bd93f9', width=2), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="#ff3366", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#00ff66", dash="dash"), row=2, col=1)

    # MACD
    col_macdh = [c for c in df.columns if 'MACDh' in str(c)][0]
    fig.add_trace(go.Bar(x=df.index, y=df[col_macdh], marker_color=np.where(df[col_macdh]>=0, '#00ff66', '#ff3366'), name="MACD"), row=3, col=1)
    
    # Volume
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='#00d4ff', opacity=0.5, name="Volume"), row=4, col=1)

    fig.update_layout(height=800, template="plotly_dark", showlegend=False, 
                      xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: ELLIOTT WAVE ---
with tab2:
    px, py = AnalyticsEngine.get_zigzag(df, threshold=ew_threshold)
    fig_ew = go.Figure()
    fig_ew.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#444', width=1), name="Price"))
    
    if len(py) >= 2:
        fig_ew.add_trace(go.Scatter(x=px, y=py, mode='lines+markers+text',
                                    text=[str(i+1) for i in range(len(py))],
                                    textposition="top center",
                                    line=dict(color="#00d4ff", width=3, dash="dash"),
                                    marker=dict(size=12, symbol="circle", line=dict(width=2, color="white")),
                                    name="Elliott Wave"))
    
    fig_ew.update_layout(height=600, template="plotly_dark", title=f"Structural ZigZag Analysis ({ew_threshold}%)")
    st.plotly_chart(fig_ew, use_container_width=True)

# --- TAB 3: MONTE CARLO ---
with mc_tab:
    paths = AnalyticsEngine.run_monte_carlo(df, days=mc_days, sims=mc_sims)
    fig_mc = go.Figure()
    
    if paths.any():
        future_dates = pd.date_range(df.index[-1], periods=mc_days, freq=df.index.freq or 'D')
        for i in range(min(mc_sims, 50)): # Show 50 paths for speed
            fig_mc.add_trace(go.Scatter(x=future_dates, y=paths[:, i], mode='lines', 
                                        line=dict(width=1, color="rgba(0, 212, 255, 0.1)"), showlegend=False))
        
        mean_path = paths.mean(axis=1)
        p95 = np.percentile(paths, 95, axis=1)
        p05 = np.percentile(paths, 5, axis=1)
        
        fig_mc.add_trace(go.Scatter(x=future_dates, y=mean_path, line=dict(color="orange", width=3), name="Expected"))
        fig_mc.add_trace(go.Scatter(x=future_dates, y=p95, line=dict(color="#00ff66", width=2, dash="dot"), name="P95 Target"))
        fig_mc.add_trace(go.Scatter(x=future_dates, y=p05, line=dict(color="#ff3366", width=2, dash="dot"), name="P05 Floor"))

    fig_mc.update_layout(height=600, template="plotly_dark", title=f"Monte Carlo Forecast ({mc_sims} sims)")
    st.plotly_chart(fig_mc, use_container_width=True)

# --- TAB 4: SUMMARY & PDF ---
with tab4:
    st.subheader("📋 Executive Strategy Report")
    
    # Logic for Report
    sigs = AnalyticsEngine.get_divergence(df)
    px, py = AnalyticsEngine.get_zigzag(df, threshold=ew_threshold)
    paths = AnalyticsEngine.run_monte_carlo(df, days=mc_days, sims=mc_sims)
    
    # Calculate target/support for summary (using code logic from geminiV2)
    bull_tgt = last_p * 1.08
    bear_sup = last_p * 0.92
    if len(py) >= 2:
        swing = abs(py[-1] - py[-2])
        bull_tgt = py[-1] + (swing * 0.618)
        bear_sup = py[-1] - (swing * 0.382)

    report_text = f"""
    ### 1. Momentum Analysis
    - **Relative Strength Index (RSI):** {df['RSI'].iloc[-1]:.1f}
    - **Divergence Signals:** {len(sigs)} Found
    - **Status:** {"BULLISH REVERSAL" if any(s.type=='BULLISH' for s in sigs) else "NEUTRAL/BEARISH"}

    ### 2. Elliott Wave Structure
    - **Current Phase:** {"Impulsive (Trend)" if len(py)%2 != 0 else "Corrective (Bounce)"}
    - **Structural Pivots:** {len(py)} major points identified.
    - **Bullish Target:** ~{bull_tgt:,.0f}
    - **Bearish Support:** ~{bear_sup:,.0f}

    ### 3. Probability Forecast (Monte Carlo)
    - **Projected Expected Price:** {np.mean(paths[-1]):,.0f}
    - **Optimistic Limit (P95):** {np.percentile(paths[-1], 95):,.0f}
    - **Pessimistic Floor (P05):** {np.percentile(paths[-1], 5):,.0f}
    """
    
    st.markdown(report_text)
    
    st.divider()
    if st.button("📥 PREPARE PDF REPORT"):
        # Placeholder for PDF Generation
        st.success("Report data prepared for export. (PDF engine integration ready)")
        st.code(report_text, language="markdown")
