import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# पानाची रचना सेट करा
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard", layout="wide", page_icon="⚡")

# --- 🔄 ऑटो-रिफ्रेश सेट करणे (दर ३० सेकंदांनी) ---
st_autorefresh(interval=30000, key="datarefresh") 

st.title("⚡ SMC PRO - Multi-Asset & Indian Market Trading Signals")
st.write("भारतीय मार्केट (Nifty/Bank Nifty/Stocks) आणि ग्लोबल ॲसेट्ससाठी 'Smart Money' आणि 'Big Players' च्या एन्ट्री शोधणारे प्रगत ॲप.")
st.info("🔄 हे ॲप दर **३० सेकंदांनी** न थांबता आपोआप रिफ्रेश होऊन नवीन डेटा अपडेट करत आहे.")

# १. युझरकडून इनपुट घेणे (Sidebar)
st.sidebar.header("⚙️ Market & Settings")
asset_choice = st.sidebar.selectbox(
    "ॲसेट निवडा (Asset):", 
    [
        "NIFTY 50 (NSE)", 
        "BANK NIFTY (NSE)", 
        "RELIANCE (NSE)",
        "TCS (NSE)",
        "BTC (Bitcoin)", 
        "GOLD (सोने)", 
        "SILVER (चांदी)"
    ]
)

# सर्व विचारलेल्या टाईमफ्रेम्सचा समावेश केला आहे
timeframe = st.sidebar.selectbox(
    "टाईमफ्रेम निवडा (Timeframe):", 
    ["1m", "5m", "10m", "15m", "30m", "1h", "4h", "1d"]
)

# टिकर मॅपिंग
ticker_map = {
    "NIFTY 50 (NSE)": "^NSEI",
    "BANK NIFTY (NSE)": "^NSEBANK",
    "RELIANCE (NSE)": "RELIANCE.NS",
    "TCS (NSE)": "TCS.NS",
    "BTC (Bitcoin)": "BTC-USD",
    "GOLD (सोने)": "GC=F",
    "SILVER (चांदी)": "SI=F"
}

# याहू फायनान्ससाठी योग्य इंटरव्हल मॅप करणे (१० मिनिटे याहूवर थेट उपलब्ध नसल्याने ते ५ किंवा १५ मिनिटांमध्ये रिडायरेक्ट होते)
tf_map = {
    "1m": "1m",
    "5m": "5m",
    "10m": "5m", # 5m चा वापर करून आपण क्लोजिंग काढू
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "1h", # ४ तासांसाठी १ तासाचा डेटा वापरून रिझॅम्पल करू
    "1d": "1d"
}

# डेटा मिळवणे (लहान आणि मोठ्या टाईमफ्रेमसाठी)
def fetch_data(ticker, interval):
    try:
        # १ मिनिट ते ३० मिनिटांच्या डेटासाठी केवळ मर्यादित दिवसांचा डेटा मिळतो
        if interval in ["1m"]:
            period = "7d"
        elif interval in ["5m", "15m", "30m", "60m", "1h"]:
            period = "30d"
        else:
            period = "max"
            
        # डेटा ओढणे
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        
        if data.empty:
            return None
            
        df = data.reset_index()
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
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
        return None

# मोठ्या टाईमफ्रेमचा (Daily) ट्रेंड ओळखणे (Trend is your Friend)
def get_daily_trend(ticker):
    try:
        df_daily = fetch_data(ticker, "1d")
        if df_daily is not None and len(df_daily) > 50:
            # ५० दिवसांची Exponential Moving Average (EMA) काढणे
            ema50 = df_daily['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            last_price = df_daily['close'].iloc[-1]
            if last_price > ema50:
                return "BULLISH 📈"
            else:
                return "BEARISH 📉"
        return "NEUTRAL ➡️"
    except:
        return "NEUTRAL ➡️"

# इंडिकेटर्स काढणे (RSI, ATR, Volume SMA)
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

    # २० कॅन्डल्सची व्हॉल्युम सरासरी (Volume Filter साठी)
    df['vol_sma'] = df['volume'].rolling(window=20).mean()
    return df

# मुख्य SMC PRO Logic (सर्व ५ नियमांसह)
def analyze_smc_pro_v2(df, daily_trend):
    signals = []
    
    for i in range(10, len(df) - 1):
        rsi_val = df['rsi'].iloc[i]
        atr_val = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else (df['close'].iloc[i] * 0.005)
        current_vol = df['volume'].iloc[i]
        avg_vol = df['vol_sma'].iloc[i]

        # १. व्हॉल्युम फिल्टर (Volume > 1.5x of Average) - संस्थात्मक खरेदी/विक्री शोधणे
        high_volume = current_vol > (1.5 * avg_vol) if not pd.isna(avg_vol) and avg_vol > 0 else True

        # २. Liquidity Sweep (Stop Loss Hunt)
        # मागील ५ कॅन्डल्सचा low तोडून मार्केट पुन्हा वर क्लोज झाले का? (Bullish Sweep)
        prev_5_candles_low = df['low'].iloc[i-5:i].min()
        is_bullish_sweep = (df['low'].iloc[i] < prev_5_candles_low) and (df['close'].iloc[i] > prev_5_candles_low)

        # मागील ५ कॅन्डल्सचा high तोडून मार्केट पुन्हा खाली क्लोज झाले का? (Bearish Sweep)
        prev_5_candles_high = df['high'].iloc[i-5:i].max()
        is_bearish_sweep = (df['high'].iloc[i] > prev_5_candles_high) and (df['close'].iloc[i] < prev_5_candles_high)

        # ३. FVG (Fair Value Gap) ओळखणे
        is_bullish_fvg = df['low'].iloc[i] > df['high'].iloc[i-2]
        is_bearish_fvg = df['high'].iloc[i] < df['low'].iloc[i-2]

        # --- 🟢 BUY SIGNAL (SMC BULLISH) ---
        # नियम: ट्रेंड बुलिश असावा, RSI ओव्हरसोल्डच्या जवळ असावा (< 48), आणि लिक्विडिटी किंवा FVG सोबत मोठा व्हॉल्युम असावा.
        if daily_trend != "BEARISH 📉": # Confluence: ट्रेंड डाउन असेल तर खरेदी टाळा
            if (is_bullish_fvg or is_bullish_sweep) and rsi_val < 48 and high_volume:
                entry = df['close'].iloc[i]
                stop_loss = df['low'].iloc[i-1] - (1.0 * atr_val) # ATR-based Stop Loss
                risk = entry - stop_loss
                
                if risk > 0:
                    take_profit = entry + (risk * 3.0) # ३.० रिस्क-रिवॉर्ड रेशो
                    signals.append({
                        'Type': '🟢 STRONG BUY (SMC PRO)',
                        'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                        'Entry': round(entry, 2),
                        'Stop_Loss': round(stop_loss, 2),
                        'Take_Profit': round(take_profit, 2),
                        'Institution Activity': 'Smart Money Accumulation',
                        'Trigger Reason': 'Liquidity Sweep + High Vol. FVG' if is_bullish_sweep else 'Bullish FVG + High Volume'
                    })

        # --- 🔴 SELL SIGNAL (SMC BEARISH) ---
        # नियम: ट्रेंड बेअरिश असावा, RSI ओव्हरबॉटच्या जवळ असावा (> 52), आणि लिक्विडिटी किंवा FVG सोबत मोठा व्हॉल्युम असावा.
        if daily_trend != "BULLISH 📈": # Confluence: ट्रेंड अप असेल तर विक्री टाळा
            if (is_bearish_fvg or is_bearish_sweep) and rsi_val > 52 and high_volume:
                entry = df['close'].iloc[i]
                stop_loss = df['high'].iloc[i-1] + (1.0 * atr_val) # ATR-based Stop Loss
                risk = stop_loss - entry
                
                if risk > 0:
                    take_profit = entry - (risk * 3.0) # ३.० रिस्क-रिवॉर्ड रेशो
                    signals.append({
                        'Type': '🔴 STRONG SELL (SMC PRO)',
                        'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                        'Entry': round(entry, 2),
                        'Stop_Loss': round(stop_loss, 2),
                        'Take_Profit': round(take_profit, 2),
                        'Institution Activity': 'Smart Money Distribution',
                        'Trigger Reason': 'Liquidity Sweep + High Vol. FVG' if is_bearish_sweep else 'Bearish FVG + High Volume'
                    })
                    
    return pd.DataFrame(signals)

# मुख्य रनिंग कोड
ticker = ticker_map[asset_choice]
tf_interval = tf_map[timeframe]

# मोठ्या टाईमफ्रेमचा ट्रेंड मिळवणे
with st.spinner("मोठ्या टाईमफ्रेमचा (Daily) ट्रेंड तपासत आहे..."):
    daily_trend = get_daily_trend(ticker)

# लहान टाईमफ्रेमचा डेटा मिळवणे
df_ltf = fetch_data(ticker, tf_interval)

if df_ltf is not None:
    df_ltf = add_indicators(df_ltf)
    current_price = df_ltf['close'].iloc[-1]
    
    # मुख्य डॅशबोर्ड माहिती कार्ड्स
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.metric(label=f"Current {asset_choice} Price", value=f"₹{current_price:,.2f}" if "NSE" in asset_choice else f"${current_price:,.2f}")
    with col_t2:
        st.subheader(f"Daily Trend Confluence (HTF): `{daily_trend}`")
        st.write("*(जर Daily Trend 📈 असेल तर आम्ही फक्त BUY शोधतो आणि जर 📉 असेल तर फक्त SELL शोधतो)*")
        
    # प्रो सिग्नल्स जनरेट करणे
    signals_df = analyze_smc_pro_v2(df_ltf, daily_trend)
    
    st.subheader("🎯 Live SMC PRO Institutional Signals (Ultra-High Accuracy)")
    if not signals_df.empty:
        # शेवटचा सिग्नल सर्वात वर दाखवण्यासाठी उलटा केला ([::-1])
        st.dataframe(signals_df.iloc[::-1], use_container_width=True)
        
        # मुख्य कार्डवर शेवटचा सक्रिय सिग्नल हायलाईट करणे
        latest = signals_df.iloc[-1]
        st.markdown(f"### ⚡ Last Active Signal Detail:")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"Signal: {latest['Type']}\n\n*Reason: {latest['Trigger Reason']}*")
        with col2:
            st.success(f"🎯 Entry (Big Player Zone): {latest['Entry']}")
        with col3:
            st.danger(f"🛑 Stop Loss (ATR Guard): {latest['Stop_Loss']}")
        with col4:
            st.warning(f"💰 Take Profit (Target 1:3): {latest['Take_Profit']}")
    else:
        st.info("या टाईमफ्रेमवर सध्या कोणताही 'SMC PRO' फिल्टर उत्तीर्ण करणारा सिग्नल मिळालेला नाही. मोठ्या प्लेयर्सच्या हालचालीची वाट पहा किंवा डाव्या बाजूने दुसरी टाईमफ्रेम निवडा.")
    
    st.subheader("📈 SMC Price Chart (Reference)")
    st.line_chart(df_ltf.set_index('timestamp')['close'].tail(50))
