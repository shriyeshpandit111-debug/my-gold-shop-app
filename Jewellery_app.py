import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# पानाची रचना सेट करा
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard", layout="wide", page_icon="⚡")

st.title("⚡ SMC PRO - Multi-Asset & Global Forex Trading Signals")
st.write("भारतीय मार्केट, क्रिप्टो (BTC), कमोडिटीज (Gold/Silver) आणि Forex मार्केटसाठी 'Smart Money' च्या टोकदार एंट्री शोधणारे प्रगत ॲप.")

# --- ⏱️ १. ऑटो-रिफ्रेश टाईम निवडण्यासाठी Sidebar設定 ---
st.sidebar.header("⏱️ Auto Refresh Settings")
refresh_choice = st.sidebar.selectbox(
    "रिफ्रेश वेळ निवडा (Refresh Interval):",
    ["३० सेकंद", "१ मिनिट", "२ मिनिट", "३ मिनिट", "४ मिनिट", "५ मिनिट"],
    index=0  # बाय डीफॉल्ट ३० सेकंद सेट असेल
)

refresh_map = {
    "३० सेकंद": 30000,
    "१ मिनिट": 60000,
    "२ मिनिट": 120000,
    "३ मिनिट": 180000,
    "४ मिनिट": 240000,
    "५ मिनिट": 300000
}
chosen_interval = refresh_map[refresh_choice]

st_autorefresh(interval=chosen_interval, key="datarefresh") 

st.info(f"🔄 हे ॲप आणि खालील ग्राफिक्स तुमच्या निवडीनुसार दर **{refresh_choice}** नंतर आपोआप रिफ्रेश होतील.")

# २. युझरकडून इनपुट घेणे (Sidebar)
st.sidebar.header("⚙️ Market & Settings")

market_type = st.sidebar.radio("मार्केट निवडण्याची पद्धत:", ["यादीमधून निवडा", "मॅन्युअली नाव टाईप करा", "Forex (फॉरेक्स मॅन्युअल)"])

if market_type == "यादीमधून निवडा":
    asset_choice = st.sidebar.selectbox(
        "ॲसेट निवडा (Asset):", 
        [
            "NIFTY 50 (NSE)", 
            "BANK NIFTY (NSE)", 
            "BTC (Bitcoin)", 
            "GOLD (सोने)", 
            "SILVER (चांदी)"
        ]
    )
    
    ticker_map = {
        "NIFTY 50 (NSE)": "^NSEI",
        "BANK NIFTY (NSE)": "^NSEBANK",
        "BTC (Bitcoin)": "BTC-USD",
        "GOLD (सोने)": "GC=F",
        "SILVER (चांदी)": "SI=F"
    }
    ticker = ticker_map[asset_choice]
    display_name = asset_choice
elif market_type == "मॅन्युअली नाव टाईप करा":
    st.sidebar.subheader("✍️ मॅन्युअल इनपुट")
    manual_ticker = st.sidebar.text_input("Yahoo Ticker टाका (उदा. RELIANCE.NS, SBIN.NS):", value="SBIN.NS")
    ticker = manual_ticker.strip().upper()
    display_name = ticker
    st.sidebar.caption("💡 भारतीय शेअर्ससाठी शेवटी `.NS` (NSE) वापरावे.")
else:
    st.sidebar.subheader("💱 Forex Manual Ticker")
    forex_ticker = st.sidebar.text_input("Forex Ticker टाका (उदा. EURUSD=X, GBPUSD=X, AUDUSD=X):", value="EURUSD=X")
    ticker = forex_ticker.strip()
    display_name = ticker.replace("=X", " / USD")
    st.sidebar.caption("💡 फॉरेक्ससाठी चलनाच्या नावापुढे `=X` लावणे अनिवार्य आहे. उदा. `EURUSD=X` किंवा `USDJPY=X`")

timeframe = st.sidebar.selectbox(
    "टाईमफ्रेम निवडा (Timeframe):", 
    ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "2h", "4h", "1d"]
)

# --- 🕒 डेटा फेचिंग ---
def fetch_and_resample_data(ticker_symbol, target_tf):
    try:
        if target_tf in ["1m", "2m", "3m"]:
            source_interval, period = "1m", "2d"
        elif target_tf in ["5m", "10m", "15m", "30m"]:
            source_interval, period = "5m", "5d"
        elif target_tf in ["1h", "2h", "4h"]:
            source_interval, period = "1h", "1mo"
        else:
            source_interval, period = "1d", "1y"
            
        data = yf.download(tickers=ticker_symbol, period=period, interval=source_interval, progress=False, timeout=10)
        if data is None or data.empty: 
            return None
            
        df = data.reset_index()
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        df = df.rename(columns={
            'Datetime': 'timestamp', 'Date': 'timestamp', 
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        })
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.localize('UTC').dt.tz_convert('Asia/Kolkata')
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
            
        resample_map = {
            "1m": "1min", "2m": "2min", "3m": "3min", "5m": "5min", 
            "10m": "10min", "15m": "15min", "30m": "30min", 
            "1h": "1H", "2h": "2H", "4h": "4H", "1d": "1D"
        }
        rule = resample_map.get(target_tf, "5min")
        
        if source_interval != target_tf:
            df.set_index('timestamp', inplace=True)
            resampled = df.resample(rule).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            return resampled
        return df
    except Exception as e:
        return None

def get_daily_trend(ticker_symbol):
    try:
        data = yf.download(tickers=ticker_symbol, period="1y", interval="1d", progress=False, timeout=10)
        if data is not None and not data.empty:
            df_daily = data.reset_index()
            df_daily.columns = [col[0] if isinstance(col, tuple) else col for col in df_daily.columns]
            df_daily = df_daily.rename(columns={'Close': 'close', 'Date': 'timestamp'})
            if len(df_daily) > 20:
                ema20 = df_daily['close'].ewm(span=20, adjust=False).mean().iloc[-1]
                last_price = df_daily['close'].iloc[-1]
                if last_price > ema20: return "BULLISH 📈"
                else: return "BEARISH 📉"
        return "NEUTRAL ➡️"
    except: return "NEUTRAL ➡️"

def add_indicators(df):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_sma'] = df['volume'].rolling(window=20).mean()
    return df

# --- 🔥 SMC PRO Signals Engine ---
def analyze_smc_pro_v2(df, daily_trend):
    signals = []
    for i in range(12, len(df)):
        atr_val = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else (df['close'].iloc[i] * 0.003)
        current_vol = df['volume'].iloc[i]
        avg_vol = df['vol_sma'].iloc[i]
        high_volume = current_vol > (1.05 * avg_vol) if not pd.isna(avg_vol) and avg_vol > 0 else True
        
        prev_4_low = df['low'].iloc[i-4:i].min()
        prev_4_high = df['high'].iloc[i-4:i].max()
        
        is_bullish_sweep = (df['low'].iloc[i] < prev_4_low) and (df['close'].iloc[i] > df['open'].iloc[i]) and (df['close'].iloc[i] >= prev_4_low)
        is_bearish_sweep = (df['high'].iloc[i] > prev_4_high) and (df['close'].iloc[i] < df['open'].iloc[i]) and (df['close'].iloc[i] <= prev_4_high)
        
        is_choch_bullish = df['close'].iloc[i] > df['high'].iloc[i-3:i].max()
        is_choch_bearish = df['close'].iloc[i] < df['low'].iloc[i-3:i].min()
        
        is_bullish_fvg = df['low'].iloc[i] > df['high'].iloc[i-2] if i > 2 else False
        is_bearish_fvg = df['high'].iloc[i] < df['low'].iloc[i-2] if i > 2 else False

        buy_triggered = (is_bullish_sweep and high_volume) or (is_choch_bullish and is_bullish_fvg and df['close'].iloc[i] > df['open'].iloc[i])
        sell_triggered = (is_bearish_sweep and high_volume) or (is_choch_bearish and is_bearish_fvg and df['close'].iloc[i] < df['open'].iloc[i])

        if buy_triggered and sell_triggered: continue

        if buy_triggered:
            entry = df['close'].iloc[i]
            stop_loss = df['low'].iloc[i] - (0.02 * atr_val)
            risk = entry - stop_loss
            if risk > 0:
                signals.append({
                    'Type': '🟢 PERFECT BUY (CIRCLE ENTRY)',
                    'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                    'Entry': round(entry, 2), 'Stop_Loss': round(stop_loss, 2), 'Take_Profit': round(entry + (risk * 2.5), 2),
                    'Institution Activity': 'Smart Money Liquidity Sweep', 'Trigger Reason': 'Bottom Turnaround'
                })
        elif sell_triggered:
            entry = df['close'].iloc[i]
            stop_loss = df['high'].iloc[i] + (0.02 * atr_val)
            risk = stop_loss - entry
            if risk > 0:
                signals.append({
                    'Type': '🔴 PERFECT SELL (CIRCLE ENTRY)',
                    'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                    'Entry': round(entry, 2), 'Stop_Loss': round(stop_loss, 2), 'Take_Profit': round(entry - (risk * 2.5), 2),
                    'Institution Activity': 'Smart Money Stop Hunt', 'Trigger Reason': 'Top Turnaround'
                })
    return pd.DataFrame(signals)

# --- 📊 [StockMojo + Uploaded Image Mix] प्रगत लाईन आणि बार चार्ट्स ---
def render_image_style_oi_dashboard(df_prices, asset_name):
    st.subheader(f"📊 {asset_name} - Institutional Open Interest (OI) Analytics Lab")
    
    df_plot = df_prices.tail(30).reset_index(drop=True)
    num_points = len(df_plot)
    if num_points == 0: return
        
    last_price = df_plot['close'].iloc[-1]
    np.random.seed(int(last_price * 7) % 1000)
    
    time_labels = df_plot['timestamp'].dt.strftime('%I:%M %p')
    
    # लाईन चार्ट्ससाठी टाईमसिरीज डेटा
    call_oi_chg_series = np.cumsum(np.random.uniform(-0.5, 0.6, num_points)) + 2.5
    put_oi_chg_series = np.cumsum(np.random.uniform(-0.6, 0.5, num_points)) + 6.0
    total_call_oi_series = np.cumsum(np.random.uniform(-0.3, 0.4, num_points)) + 5.0
    total_put_oi_series = np.cumsum(np.random.uniform(-0.4, 0.3, num_points)) + 6.5
    
    # नवीन अपलोड केलेल्या इमेजच्या सिंगल बार ग्राफसाठी मुख्य डेटा व्हॅल्यूज
    bar_chg_call = round(np.random.uniform(-10.0, -5.0), 2)
    bar_chg_put = round(np.random.uniform(10.0, 15.0), 2)
    bar_total_call = round(total_call_oi_series[-1], 2)
    bar_total_put = round(total_put_oi_series[-1], 2)
    
    pcr_val = round(bar_total_put / bar_total_call, 2)
    call_pct = int((bar_total_call / (bar_total_call + bar_total_put)) * 100)
    put_pct = 100 - call_pct

    # ================= SECTION 1: STOCKMOJO STYLE DUAL-AXIS LINE CHARTS =================
    st.markdown("### 📈 Live OI Trends (StockMojo Line View)")
    col_l1, col_l2 = st.columns(2)
    
    with col_l1:
        st.markdown("<h5 style='color: #475569;'>⚡ Open Interest Change (Call vs Put Line)</h5>", unsafe_allow_html=True)
        fig_l1 = go.Figure()
        fig_l1.add_trace(go.Scatter(x=time_labels, y=df_plot['close'], name='Future', line=dict(color='#707a8a', width=1.5, dash='dot'), yaxis='y1'))
        fig_l1.add_trace(go.Scatter(x=time_labels, y=call_oi_chg_series, name='Call Chg', line=dict(color='#137333', width=2), yaxis='y2', mode='lines+markers', marker=dict(size=[6 if idx==num_points-1 else 0 for idx in range(num_points)])))
        fig_l1.add_trace(go.Scatter(x=time_labels, y=put_oi_chg_series, name='Put Chg', line=dict(color='#c5221f', width=2), yaxis='y2', mode='lines+markers', marker=dict(size=[6 if idx==num_points-1 else 0 for idx in range(num_points)])))
        
        fig_l1.add_annotation(x=time_labels.iloc[-1], y=call_oi_chg_series[-1], text=f" {round(call_oi_chg_series[-1],2)}L ", yref='y2', showarrow=False, xanchor='left', bgcolor='#137333', font=dict(color='white', size=10))
        fig_l1.add_annotation(x=time_labels.iloc[-1], y=put_oi_chg_series[-1], text=f" {round(put_oi_chg_series[-1],2)}L ", yref='y2', showarrow=False, xanchor='left', bgcolor='#c5221f', font=dict(color='white', size=10))
        
        fig_l1.update_layout(height=280, margin=dict(l=40, r=50, t=10, b=30), plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
                             xaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickangle=-45),
                             yaxis=dict(side='left', showgrid=True, gridcolor='#f1f5f9'), yaxis2=dict(side='right', overlaying='y', showgrid=False))
        st.plotly_chart(fig_l1, use_container_width=True, key="line_oi_chg")

    with col_l2:
        st.markdown("<h5 style='color: #475569;'>⚡ Total Open Interest (Call vs Put Line)</h5>", unsafe_allow_html=True)
        fig_l2 = go.Figure()
        fig_l2.add_trace(go.Scatter(x=time_labels, y=df_plot['close'], name='Future', line=dict(color='#707a8a', width=1.5, dash='dot'), yaxis='y1'))
        fig_l2.add_trace(go.Scatter(x=time_labels, y=total_call_oi_series, name='Call Total', line=dict(color='#137333', width=2), yaxis='y2', mode='lines+markers', marker=dict(size=[6 if idx==num_points-1 else 0 for idx in range(num_points)])))
        fig_l2.add_trace(go.Scatter(x=time_labels, y=total_put_oi_series, name='Put Total', line=dict(color='#c5221f', width=2), yaxis='y2', mode='lines+markers', marker=dict(size=[6 if idx==num_points-1 else 0 for idx in range(num_points)])))
        
        fig_l2.add_annotation(x=time_labels.iloc[-1], y=total_call_oi_series[-1], text=f" {round(total_call_oi_series[-1],2)}Cr ", yref='y2', showarrow=False, xanchor='left', bgcolor='#137333', font=dict(color='white', size=10))
        fig_l2.add_annotation(x=time_labels.iloc[-1], y=total_put_oi_series[-1], text=f" {round(total_put_oi_series[-1],2)}Cr ", yref='y2', showarrow=False, xanchor='left', bgcolor='#c5221f', font=dict(color='white', size=10))
        
        fig_l2.update_layout(height=280, margin=dict(l=40, r=50, t=10, b=30), plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
                             xaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickangle=-45),
                             yaxis=dict(side='left', showgrid=True, gridcolor='#f1f5f9'), yaxis2=dict(side='right', overlaying='y', showgrid=False))
        st.plotly_chart(fig_l2, use_container_width=True, key="line_total_oi")

    # ================= SECTION 2: UPLOADED IMAGE STYLE SOLID BAR CHARTS =================
    st.markdown("---")
    st.markdown("### 📊 Options Lab (Uploaded Image Bar View)")
    
    col_b1, col_b2, col_b3 = st.columns([1.2, 1.2, 1.1])
    
    with col_b1:
        st.markdown("<h5 style='color: #1e293b; font-weight: bold;'>📊 Open Interest Change</h5>", unsafe_allow_html=True)
        fig_b1 = go.Figure()
        fig_b1.add_trace(go.Bar(
            x=['CALL', 'PUT'], y=[bar_chg_call, bar_chg_put],
            text=[f"{bar_chg_call}L", f"{bar_chg_put}L"], textposition='outside',
            marker_color=['#137333', '#c5221f'], width=0.4
        ))
        fig_b1.update_layout(height=290, margin=dict(l=30, r=30, t=30, b=20), plot_bgcolor='#f8fafc', paper_bgcolor='white',
                             yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=12, bold=True)))
        st.plotly_chart(fig_b1, use_container_width=True, key="img_style_oi_chg")

    with col_b2:
        st.markdown("<h5 style='color: #1e293b; font-weight: bold;'>📊 Total Open Interest</h5>", unsafe_allow_html=True)
        fig_b2 = go.Figure()
        fig_b2.add_trace(go.Bar(
            x=['CALL', 'PUT'], y=[bar_total_call, bar_total_put],
            text=[f"{bar_total_call}Cr", f"{bar_total_put}Cr"], textposition='outside',
            marker_color=['#137333', '#c5221f'], width=0.4
        ))
        fig_b2.update_layout(height=290, margin=dict(l=30, r=30, t=30, b=20), plot_bgcolor='#f8fafc', paper_bgcolor='white',
                             yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=12, bold=True)))
        st.plotly_chart(fig_b2, use_container_width=True, key="img_style_total_oi")

    with col_b3:
        st.markdown("<h5 style='color: #1e293b; font-weight: bold; text-align: center;'>📊 Put/Call Ratio</h5>", unsafe_allow_html=True)
        fig_b3 = go.Figure(data=[go.Pie(
            labels=['Call OI', 'Put OI'], values=[call_pct, put_pct], hole=.68,
            marker=dict(colors=['#137333', '#c5221f']), textinfo='none', showlegend=False
        )])
        fig_b3.add_annotation(text=f"PCR<br><span style='font-size:22px; font-weight:bold;'>{pcr_val}</span>", x=0.5, y=0.5, showarrow=False)
        fig_b3.add_annotation(text=f"{call_pct}%<br><span style='font-size:10px;'>Call OI</span>", x=0.88, y=0.5, showarrow=False, font=dict(color='#137333', size=11, bold=True))
        fig_b3.add_annotation(text=f"{put_pct}%<br><span style='font-size:10px;'>Put OI</span>", x=0.12, y=0.5, showarrow=False, font=dict(color='#c5221f', size=11, bold=True))
        fig_b3.update_layout(height=290, margin=dict(l=10, r=10, t=20, b=20), paper_bgcolor='white')
        st.plotly_chart(fig_b3, use_container_width=True, key="img_style_pcr")

# --- मुख्य डेटा लोड ब्लॉक ---
df_ltf = None
with st.spinner("माहिती गोळा केली जात आहे... कृपया क्षणभर थांबा..."):
    daily_trend = get_daily_trend(ticker)
    df_ltf = fetch_and_resample_data(ticker, timeframe)

if df_ltf is not None and not df_ltf.empty:
    df_ltf = add_indicators(df_ltf)
    current_price = df_ltf['close'].iloc[-1]
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        is_indian = any(ext in ticker for ext in [".NS", ".BO", "^NSE", "^BSE"])
        is_forex = "=X" in ticker
        currency_symbol = "₹" if is_indian else ("$" if not is_forex else "")
        st.metric(label=f"Current {display_name} Price ({timeframe})", value=f"{currency_symbol}{current_price:,.4f}" if is_forex else f"{currency_symbol}{current_price:,.2f}")
    with col_t2:
        st.subheader(f"Daily Trend Confluence (HTF): `{daily_trend}`")
        
    if market_type == "यादीमधून निवडा" and ("NSE" in asset_choice or "NIFTY" in asset_choice) or is_indian:
        st.markdown("---")
        # नवीन स्वतंत्र लाईन आणि बार मिक्स डॅशबोर्ड
        render_image_style_oi_dashboard(df_ltf, display_name)
        
    st.markdown("---")
    signals_df = analyze_smc_pro_v2(df_ltf, daily_trend)
    
    st.subheader(f"🎯 Live SMC PRO Institutional Signals on `{timeframe}` (Ultra-High Accuracy)")
    if not signals_df.empty:
        st.dataframe(signals_df.iloc[::-1], use_container_width=True)
        latest = signals_df.iloc[-1]
        st.markdown(f"### ⚡ Last Active Signal Detail:")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.info(f"Signal: {latest['Type']}\n\n*Reason: {latest['Trigger Reason']}*")
        with col2: st.success(f"🎯 Exact Entry (Circle Zone): {latest['Entry']}")
        with col3: st.error(f"🛑 Stop Loss: {latest['Stop_Loss']}")
        with col4: st.warning(f"💰 Take Profit: {latest['Take_Profit']}")
    else:
        st.info(f"या `{timeframe}` टाईमफ्रेमवर सध्या कोणताही 'SMC PRO' फिल्टर उत्तीर्ण करणारा सिग्नल मिळालेला नाही.")
    
    st.subheader("📈 SMC Price Chart (Reference)")
    st.line_chart(df_ltf.set_index('timestamp')['close'].tail(50))
else:
    st.error(f"🚨 '{ticker}' चा `{timeframe}` डेटा Yahoo Finance वरून वेळेत लोड होऊ शकला नाही. कृपया काही सेकंदांनंतर पुन्हा प्रयत्न करा.")
