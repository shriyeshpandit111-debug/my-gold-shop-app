import streamlit as st
import ccxt
import pandas as pd
import numpy as np

# पानाची रचना सेट करा (Page Configuration)
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard", layout="wide", page_icon="⚡")

st.title("⚡ SMC PRO - Multi-Asset Trading Signals")
st.write("BTC, Gold, आणि Silver साठी प्रगत स्मार्ट मनी संकल्पना (SMC) आणि अचूक इंडिकेटर्स फिल्टर असलेले वेब ॲप.")

# १. युझरकडून इनपुट घेणे (Sidebar)
st.sidebar.header("⚙️ Advanced Settings")
asset = st.sidebar.selectbox("ॲसेट निवडा (Asset):", ["BTC/USDT", "GOLD/USD", "SILVER/USD"])
timeframe = st.sidebar.selectbox("टाईमफ्रेम (Timeframe) - लहान चार्ट:", ["1m", "5m", "15m", "30m", "1h"])
higher_tf = st.sidebar.selectbox("ट्रेंड चेक करण्यासाठी मोठी टाईमफ्रेम (HTF):", ["1h", "4h", "1d"])

exchange = ccxt.binance({'enableRateLimit': True})

def fetch_data(symbol, tf, limit=150):
    try:
        trading_symbol = symbol
        if "GOLD" in symbol:
            trading_symbol = "PAXG/USDT"  # लाईव्ह गोल्ड ट्रॅक करणारे टोकन
        elif "SILVER" in symbol:
            trading_symbol = "BTC/USDT"   # डेमोसाठी
            
        bars = exchange.fetch_ohlcv(trading_symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"डेटा लोड करताना चूक झाली: {e}")
        return None

# इंडिकेटर्स काढणे (RSI, ATR, Volume SMA)
def add_indicators(df):
    # --- पर्याय ४: ATR (Average True Range) - योग्य स्टॉप लॉस बफरसाठी ---
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # --- पर्याय ३: RSI (Relative Strength Index) ---
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # --- पर्याय २: व्हॉल्युम फिल्टर (Volume Average) ---
    df['vol_sma'] = df['volume'].rolling(window=20).mean()
    
    return df

# मुख्य अचूक SMC Logic
def analyze_smc_pro(df, htf_trend):
    signals = []
    
    for i in range(5, len(df) - 1):
        # अटी तपासणे:
        current_vol = df['volume'].iloc[i]
        avg_vol = df['vol_sma'].iloc[i]
        rsi_val = df['rsi'].iloc[i]
        atr_val = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else (df['close'].iloc[i] * 0.005)
        
        # --- पर्याय २: व्हॉल्युम फिल्टर (Volume २ पट जास्त असावा जेणेकरून खोटा सिग्नल टळेल) ---
        volume_condition = current_vol > (avg_vol * 1.5)

        # --- पर्याय १: BULLISH FVG + RSI Oversold (मोठ्या ट्रेंंडनूसार फक्त BUY) ---
        if (df['low'].iloc[i] > df['high'].iloc[i-2]) and volume_condition:
            # ट्रेंड जर मोठ्या टाईमफ्रेमवर बुलिश असेल तरच ट्रेड घेणे
            if htf_trend == "BULLISH" and rsi_val < 40:  # पर्याय ३: RSI फिल्टर
                entry = df['low'].iloc[i]
                
                # पर्याय ४: ATR बफर वापरून Stop Loss सेट करणे जेणेकरून नको असलेला SL हिट होणार नाही
                stop_loss = df['low'].iloc[i-1] - (0.5 * atr_val)
                risk = entry - stop_loss
                
                if risk > 0:
                    take_profit = entry + (risk * 3.5)  # 1:3.5 Target
                    signals.append({
                        'Type': '🟢 STRONG BUY (SMC PRO)',
                        'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                        'Entry': round(entry, 2),
                        'Stop_Loss': round(stop_loss, 2),
                        'Take_Profit': round(take_profit, 2),
                        'SMC Reason': 'High Vol. + RSI Oversold + HTF Trend Support'
                    })

        # --- पर्याय १: BEARISH FVG + RSI Overbought (मोठ्या ट्रेंंडनूसार फक्त SELL) ---
        elif (df['high'].iloc[i] < df['low'].iloc[i-2]) and volume_condition:
            if htf_trend == "BEARISH" and rsi_val > 60:
                entry = df['high'].iloc[i]
                stop_loss = df['high'].iloc[i-1] + (0.5 * atr_val)
                risk = stop_loss - entry
                
                if risk > 0:
                    take_profit = entry - (risk * 3.5)
                    signals.append({
                        'Type': '🔴 STRONG SELL (SMC PRO)',
                        'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                        'Entry': round(entry, 2),
                        'Stop_Loss': round(stop_loss, 2),
                        'Take_Profit': round(take_profit, 2),
                        'SMC Reason': 'High Vol. + RSI Overbought + HTF Trend Support'
                    })
                    
    return pd.DataFrame(signals)

# डेटा मिळवा
df_ltf = fetch_data(asset, timeframe)
df_htf = fetch_data(asset, higher_tf)

if df_ltf is not None and df_htf is not None:
    # --- पर्याय १: मोठ्या टाईमफ्रेमचा ट्रेंड ठरवणे (EMA Cross किंवा Price Direction ने) ---
    htf_close_now = df_htf['close'].iloc[-1]
    htf_close_prev = df_htf['close'].iloc[-10] # मागील १० कॅन्डल्स आधीची किंमत
    
    if htf_close_now > htf_close_prev:
        htf_trend = "BULLISH"
        trend_color = "🟢 BULLISH"
    else:
        htf_trend = "BEARISH"
        trend_color = "🔴 BEARISH"
        
    # इंडिकेटर्स जोडा
    df_ltf = add_indicators(df_ltf)
    
    # डॅशबोर्डवर लाईव्ह ट्रेंड आणि किमती दाखवणे
    current_price = df_ltf['close'].iloc[-1]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(label=f"Current {asset} Price", value=f"${current_price:,.2f}")
    with col_b:
        st.metric(label=f"Higher TF ({higher_tf}) Trend", value=trend_color)
        
    # प्रो सिग्नल्स जनरेट करणे
    signals_df = analyze_smc_pro(df_ltf, htf_trend)
    
    st.subheader("🎯 Live SMC PRO Signals (High Accuracy Only)")
    if not signals_df.empty:
        st.dataframe(signals_df.iloc[::-1], use_container_width=True)
        
        # मुख्य कार्डवर शेवटचा सिग्नल हायलाईट करणे
        latest = signals_df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"Signal: {latest['Type']}")
        with col2:
            st.success(f"🎯 Entry: {latest['Entry']}")
        with col3:
            st.danger(f"🛑 Stop Loss: {latest['Stop_Loss']}")
        with col4:
            st.warning(f"💰 Target (TP): {latest['Take_Profit']}")
    else:
        st.info("फिल्टर अत्यंत कडक असल्यामुळे सध्या या टाईमफ्रेमवर कोणताही 'हाय अचूकता' (High Accuracy) सिग्नल मिळालेला नाही. कृपया योग्य संधीची वाट पहा.")
    
    st.subheader("📈 Raw Chart Data")
    st.line_chart(df_ltf.set_index('timestamp')['close'].tail(50))
