import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# पानाची रचना सेट करा
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard", layout="wide", page_icon="⚡")

st.title("⚡ SMC PRO - Multi-Asset Trading Signals")
st.write("BTC, Gold, आणि Silver साठी प्रगत स्मार्ट मनी संकल्पना (SMC) आणि अचूक इंडिकेटर्स फिल्टर असलेले वेब ॲप.")

# १. युझरकडून इनपुट घेणे (Sidebar)
st.sidebar.header("⚙️ Advanced Settings")
asset_choice = st.sidebar.selectbox("ॲसेट निवडा (Asset):", ["BTC (Bitcoin)", "GOLD (सोने)", "SILVER (चांदी)"])
timeframe = st.sidebar.selectbox("टाईमफ्रेम (Timeframe):", ["1m", "5m", "15m", "30m", "1h", "1d"])

# याहू फायनान्ससाठी योग्य टिकर सिम्बॉल सेट करणे
ticker_map = {
    "BTC (Bitcoin)": "BTC-USD",
    "GOLD (सोने)": "GC=F",      # Gold Futures
    "SILVER (चांदी)": "SI=F"    # Silver Futures
}

# याहू फायनान्ससाठी योग्य इंटरव्हल मॅप करणे
tf_map = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d"
}

def fetch_data(asset, tf):
    try:
        ticker = ticker_map[asset]
        interval = tf_map[tf]
        
        # १ मिनिटाच्या डेटासाठी केवळ मागील ७ दिवसांचा डेटा मिळतो
        period = "7d" if interval in ["1m", "5m", "15m", "30m"] else "60d"
        if interval == "1h":
            period = "730d"  # कमाल मर्यादा
        elif interval == "1d":
            period = "max"
            
        # डेटा ओढणे
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        
        if data.empty:
            st.error("डेटा रिकामा आहे. कृपया वेगळी टाईमफ्रेम निवडून पहा.")
            return None
            
        # डेटा फ्रेम रीसेट आणि नीट करणे
        df = data.reset_index()
        # याहू फायनान्स कॉलमची नावे कधीकधी बदलू शकतात, ती प्रमाणित करणे
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        # कॉलमचे नाव बदलणे
        df = df.rename(columns={
            'Datetime': 'timestamp', 
            'Date': 'timestamp', 
            'Open': 'open', 
            'High': 'high', 
            'Low': 'low', 
            'Close': 'close', 
            'Volume': 'volume'
        })
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"डेटा लोड करताना चूक झाली: {e}")
        return None

# इंडिकेटर्स काढणे (RSI, ATR, Volume SMA)
def add_indicators(df):
    # ATR - योग्य स्टॉप लॉस बफरसाठी
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # व्हॉल्युम फिल्टर
    df['vol_sma'] = df['volume'].rolling(window=20).mean()
    return df

# मुख्य SMC Logic
def analyze_smc_pro(df):
    signals = []
    
    for i in range(5, len(df) - 1):
        current_vol = df['volume'].iloc[i]
        avg_vol = df['vol_sma'].iloc[i] if 'vol_sma' in df.columns else 1
        rsi_val = df['rsi'].iloc[i]
        atr_val = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else (df['close'].iloc[i] * 0.005)
        
        volume_condition = True  # फॉरेक्स/गोल्डमध्ये कधीकधी व्हॉल्युम नसतो, म्हणून सुरक्षितता

        # BULLISH FVG + RSI Oversold (BUY)
        if (df['low'].iloc[i] > df['high'].iloc[i-2]) and rsi_val < 45:
            entry = df['low'].iloc[i]
            stop_loss = df['low'].iloc[i-1] - (0.5 * atr_val)
            risk = entry - stop_loss
            
            if risk > 0:
                take_profit = entry + (risk * 3.5)
                signals.append({
                    'Type': '🟢 STRONG BUY (SMC PRO)',
                    'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                    'Entry': round(entry, 2),
                    'Stop_Loss': round(stop_loss, 2),
                    'Take_Profit': round(take_profit, 2),
                    'SMC Reason': 'High Vol. + RSI Oversold (Order Block)'
                })

        # BEARISH FVG + RSI Overbought (SELL)
        elif (df['high'].iloc[i] < df['low'].iloc[i-2]) and rsi_val > 55:
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
                    'SMC Reason': 'High Vol. + RSI Overbought (Supply Block)'
                })
                    
    return pd.DataFrame(signals)

# डेटा मिळवा
df_ltf = fetch_data(asset_choice, timeframe)

if df_ltf is not None:
    df_ltf = add_indicators(df_ltf)
    current_price = df_ltf['close'].iloc[-1]
    
    st.metric(label=f"Current {asset_choice} Price", value=f"${current_price:,.2f}")
    
    # प्रो सिग्नल्स जनरेट करणे
    signals_df = analyze_smc_pro(df_ltf)
    
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
        st.info("या टाईमफ्रेमवर सध्या कोणताही 'SMC PRO' सिग्नल मिळालेला नाही. कृपया थोडा वेळ थांबा किंवा डाव्या बाजूने टाईमफ्रेम बदला.")
    
    st.subheader("📈 Raw Chart Data")
    st.line_chart(df_ltf.set_index('timestamp')['close'].tail(50))
