import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import urllib.parse

# पानाची रचना सेट करा
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard", layout="wide", page_icon="⚡")

st.title("⚡ SMC PRO - Multi-Asset & Multi-Timeframe Signals")

# --- ⚙️ Upstox API Configuration Sidebar ---
st.sidebar.header("🔑 Upstox API Configuration")

# URL मधून टोकन वाचण्याचा प्रयत्न करणे
query_params = st.query_params
url_token = query_params.get("token", "")

# टोकन इनपुट बॉक्स
access_token = st.sidebar.text_input(
    "Enter Upstox Access Token:", 
    value=url_token,
    type="password", 
    help="Upstox Developer Console वरून जनरेट केलेला Access Token इथे पेस्ट करा."
)

# --- ⏱️ ऑटो-रिफ्रेश सेटिंग ---
st.sidebar.header("⏱️ Auto Refresh Settings")
refresh_choice = st.sidebar.selectbox("रिफ्रेश वेळ निवडा:", ["३० सेकंद", "१ मिनिट", "२ मिनिट", "५ मिनिट"], index=0)
refresh_map = {"३० सेकंद": 30000, "१ मिनिट": 60000, "२ मिनिट": 120000, "५ मिनिट": 300000}
st_autorefresh(interval=refresh_map[refresh_choice], key="datarefresh") 

# --- ⚙️ Market Settings ---
st.sidebar.header("⚙️ Market Settings")
asset_choice = st.sidebar.selectbox("ॲसेट निवडा:", ["NIFTY", "BANKNIFTY", "GOLD", "SILVER", "BTC"])

# --- ⏳ Time Frame Selection (नवीन जोडलेले) ---
st.sidebar.header("⏳ Time Frame Settings")
tf_choice = st.sidebar.selectbox(
    "टाईम फ्रेम निवडा (Time Frame):", 
    ["1 min", "2 min", "3 min", "5 min", "10 min", "15 min", "30 min", "1 hr", "2 hr", "4 hr", "1 Day", "1 Week"],
    index=3 # बाय-डीफॉल्ट 5 Min सिलेक्ट राहील
)

# टाइमफ्रेमला Pandas च्या सुसंगत कोडमध्ये मॅप करणे
tf_map = {
    "1 min": "1T", "2 min": "2T", "3 min": "3T", "5 min": "5T", "10 min": "10T", 
    "15 min": "15T", "30 min": "30T", "1 hr": "1H", "2 hr": "2H", "4 hr": "4H", 
    "1 Day": "1D", "1 Week": "1W"
}

# Upstox आणि Binance साठी सर्व इन्स्ट्रुमेंट्सची माहिती
instrument_map = {
    "NIFTY": {"history_key": "NSE_INDEX|Nifty 50", "type": "equity"},
    "BANKNIFTY": {"history_key": "NSE_INDEX|Nifty Bank", "type": "equity"},
    "GOLD": {"history_key": "MCX_FO|GOLD", "type": "commodity"},       # MCX Gold Future
    "SILVER": {"history_key": "MCX_FO|SILVER", "type": "commodity"},   # MCX Silver Future
    "BTC": {"symbol": "BTCUSDT", "type": "crypto"}                     # Binance Crypto
}

asset_info = instrument_map[asset_choice]

# --- 🔄 डेटा रि-सॅम्पलिंग फंक्शन (Re-sampling for Custom Timeframes) ---
def resample_data(df, interval_code):
    """
    1-मिनिटाच्या डेटाला युझरने निवडलेल्या टाइमफ्रेममध्ये रूपांतरित करते.
    """
    if df is None or df.empty:
        return df
    
    # इंडेक्स म्हणून टाइमस्टॅम्प सेट करणे
    df = df.set_index('timestamp')
    
    # OHLC आणि Volume रि-सँपल करणे
    resampled = df.resample(interval_code).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    resampled = resampled.reset_index()
    
    # तांत्रिक इंडिकेटर्स पुन्हा तयार करणे
    high_low = resampled['high'] - resampled['low']
    high_close = np.abs(resampled['high'] - resampled['close'].shift())
    low_close = np.abs(resampled['low'] - resampled['close'].shift())
    resampled['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
    resampled['vol_sma'] = resampled['volume'].rolling(window=20).mean()
    
    return resampled

# --- 📅 एक्सपायरी कॅल्क्युलेटर ---
def get_upcoming_expiry_date():
    today = datetime.now().date()
    days_ahead = (3 - today.weekday()) % 7
    upcoming_thursday = today + timedelta(days=days_ahead)
    return upcoming_thursday.strftime('%Y-%m-%d')

# --- 🌐 Binance API कडून BTC चा डेटा मिळवणे ---
@st.cache_data(ttl=30)
def fetch_btc_from_binance():
    try:
        url = "https://api.binance.com/api/v3/klines"
        # जास्तीत जास्त डेटा ओढणे जेणेकरून मोठ्या टाइमफ्रेमसाठी पुरेसा डेटा मिळेल
        params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 1000}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df, None
        return None, "Binance API कडून डेटा मिळाला नाही."
    except Exception as e:
        return None, str(e)

# --- 📈 Upstox कडून चार्ट डेटा मिळवणे ---
def fetch_candles_from_upstox(instrument_key, token):
    try:
        today = datetime.now()
        # १ दिवसापेक्षा मोठी टाइमफ्रेम असेल तर मागील ३० दिवसांचा डेटा घेणे, अन्यथा ७ दिवसांचा घेणे
        days_to_fetch = 30 if "Day" in tf_choice or "Week" in tf_choice else 7
        start_date = today - timedelta(days=days_to_fetch)
        
        to_date_str = today.strftime('%Y-%m-%d')
        from_date_str = start_date.strftime('%Y-%m-%d')
        
        safe_key = urllib.parse.quote(instrument_key)
        
        # Upstox कडून बेस १-मिनिटाचा डेटा मागवणे (मोठ्या टाईमफ्रेमसाठी आपण 'day' पॅरामीटर थेट वापरू शकतो)
        api_interval = "1minute"
        if tf_choice == "1 Day":
            api_interval = "day"
        elif tf_choice == "1 Week":
            api_interval = "week"
            
        url = f"https://api.upstox.com/v2/historical-candle/{safe_key}/{api_interval}/{to_date_str}/{from_date_str}"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("status") == "success" and res_data.get("data", {}).get("candles"):
                candles = res_data["data"]["candles"]
                
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
                return df, None
            else:
                return None, "API कडून डेटा रिकामा मिळाला (मार्केट बंद असू शकते)."
        else:
            try:
                err_details = response.json().get("errors", [{}])[0].get("message", "Unknown API Error")
            except:
                err_details = response.text
            return None, f"HTTP Error {response.status_code}: {err_details}"
    except Exception as e:
        return None, str(e)

# --- 📊 Render Price Chart ---
def render_price_chart(df, asset_name, tf_name):
    st.subheader(f"📈 {asset_name} ({tf_name}) - Realtime Candle Trend")
    # चार्टवर शेवटच्या ५० कॅंडल्स दाखवणे
    df_plot = df.tail(50).reset_index(drop=True)
    
    # टाईम फॉरमॅट सेट करणे (दिवस/आठवड्यासाठी तारीख आणि मिनिटांसाठी वेळ)
    if "Day" in tf_name or "Week" in tf_name:
        x_format = df_plot['timestamp'].dt.strftime('%d-%b')
    else:
        x_format = df_plot['timestamp'].dt.strftime('%d %b, %I:%M %p')
        
    fig = go.Figure(data=[go.Candlestick(
        x=x_format,
        open=df_plot['open'],
        high=df_plot['high'],
        low=df_plot['low'],
        close=df_plot['close'],
        increasing_line_color='#22c55e', 
        decreasing_line_color='#ef4444'
    )])
    fig.update_layout(height=380, margin=dict(l=40, r=40, t=10, b=40), plot_bgcolor='white', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{asset_name}_{tf_name}")

# --- 🔥 SMC PRO Signals Engine ---
def analyze_smc_pro_v2(df):
    signals = []
    if len(df) < 15:
        return pd.DataFrame(signals)
        
    for i in range(12, len(df)):
        atr_val = df['atr'].iloc[i] if not pd.isna(df['atr'].iloc[i]) else (df['close'].iloc[i] * 0.003)
        current_vol = df['volume'].iloc[i]
        avg_vol = df['vol_sma'].iloc[i]
        high_volume = current_vol > (1.05 * avg_vol) if not pd.isna(avg_vol) and avg_vol > 0 else True
        
        prev_4_low = df['low'].iloc[i-4:i].min()
        prev_4_high = df['high'].iloc[i-4:i].max()
        
        is_bullish_sweep = (df['low'].iloc[i] < prev_4_low) and (df['close'].iloc[i] > df['open'].iloc[i]) and (df['close'].iloc[i] >= prev_4_low)
        is_bearish_sweep = (df['high'].iloc[i] > prev_4_high) and (df['close'].iloc[i] < df['open'].iloc[i]) and (df['close'].iloc[i] <= prev_4_high)

        if is_bullish_sweep and high_volume:
            entry = df['close'].iloc[i]
            stop_loss = df['low'].iloc[i] - (0.02 * atr_val)
            risk = entry - stop_loss
            if risk > 0:
                signals.append({
                    'Type': '🟢 PERFECT BUY',
                    'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                    'Entry': round(entry, 2),
                    'Stop_Loss': round(stop_loss, 2),
                    'Take_Profit': round(entry + (risk * 2.5), 2),
                    'Trigger': 'Liquidity Sweep Verified'
                })
        elif is_bearish_sweep and high_volume:
            entry = df['close'].iloc[i]
            stop_loss = df['high'].iloc[i] + (0.02 * atr_val)
            risk = stop_loss - entry
            if risk > 0:
                signals.append({
                    'Type': '🔴 PERFECT SELL',
                    'Time': df['timestamp'].iloc[i].strftime('%Y-%m-%d %H:%M'),
                    'Entry': round(entry, 2),
                    'Stop_Loss': round(stop_loss, 2),
                    'Take_Profit': round(entry - (risk * 2.5), 2),
                    'Trigger': 'Supply Sweep Verified'
                })
    return pd.DataFrame(signals)

# --- मुख्य प्रोग्राम एक्झिक्युशन ---
df_raw = None
error_msg = None

# १. जर BTC निवडले असेल तर थेट Binance कडून डेटा घेणे (टोकनची गरज नाही)
if asset_info["type"] == "crypto":
    with st.spinner("Binance वरून BTC लाइव्ह डेटा लोड होत आहे..."):
        df_raw, error_msg = fetch_btc_from_binance()
else:
    # २. इतर ऍसेट्ससाठी Upstox टोकन तपासणे
    if access_token:
        with st.spinner(f"Upstox वरून {asset_choice} चा मूळ डेटा लोड केला जात आहे..."):
            df_raw, error_msg = fetch_candles_from_upstox(asset_info["history_key"], access_token)
    else:
        st.warning(f"👈 डाव्या बाजूला आधी तुमचा 'Upstox Access Token' टाका, म्हणजे {asset_choice} चा डेटा लोड होईल.")

# ३. डेटावर टाईम फ्रेम प्रोसेसिंग करणे (Resampling)
if df_raw is not None and not df_raw.empty:
    
    # जर युझरने '1 min' किंवा थेट '1 Day/Week' निवडले नसेल, तर आपण मूळ १-मिनिटाच्या डेटाला रि-सँपल करणार
    if tf_choice not in ["1 min", "1 Day", "1 Week"]:
        with st.spinner(f"डेटाला {tf_choice} टाईम फ्रेम मध्ये बदलले जात आहे..."):
            df_data = resample_data(df_raw, tf_map[tf_choice])
    else:
        # जर १ मिनिट किंवा डे/वीक असेल तर डेटा जसा आहे तसाच वापरून इंडिकेटर्स कॅल्क्युलेट करणार
        df_data = df_raw.copy()
        high_low = df_data['high'] - df_data['low']
        high_close = np.abs(df_data['high'] - df_data['close'].shift())
        low_close = np.abs(df_data['low'] - df_data['close'].shift())
        df_data['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
        df_data['vol_sma'] = df_data['volume'].rolling(window=20).mean()

    # ४. चार्ट आणि सिग्नल्स दाखवणे
    if df_data is not None and not df_data.empty:
        current_price = df_data['close'].iloc[-1]
        currency_symbol = "$" if asset_info["type"] == "crypto" else "₹"
        
        # मुख्य मॅट्रिक्स बॉक्स
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label=f"Current {asset_choice} Price", value=f"{currency_symbol}{current_price:,.2f}")
        with col2:
            st.metric(label="Selected Time Frame", value=tf_choice)
            
        # कॅंडलस्टिक चार्ट दाखवणे
        render_price_chart(df_data, asset_choice, tf_choice)
                
        st.markdown("---")
        
        # सिग्नल्स इंजिन चालवणे
        signals_df = analyze_smc_pro_v2(df_data)
        st.subheader(f"🎯 Live SMC PRO Signals for {asset_choice} ({tf_choice})")
        if not signals_df.empty:
            st.dataframe(signals_df.iloc[::-1], use_container_width=True)
        else:
            st.info(f"सध्या {tf_choice} टाइमफ्रेमवर कोणताही नवीन सिग्नल मिळालेला नाही. तुम्ही दुसरी टाईमफ्रेम बदलून पाहू शकता.")
    else:
        st.warning("या टाईमफ्रेमसाठी पुरेसा डेटा उपलब्ध नाही.")
elif error_msg:
    st.error(f"🚨 डेटा लोड होऊ शकला नाही.\n\nकारण: {error_msg}")
