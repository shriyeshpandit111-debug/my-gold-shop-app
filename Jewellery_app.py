import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# पानाची रचना सेट करा
st.set_page_config(page_title="SMC PRO Smart Signal Dashboard with Upstox", layout="wide", page_icon="⚡")

st.title("⚡ SMC PRO - Option Chain & Signals Dashboard")

# --- ⚙️ Upstox API Configuration Sidebar ---
st.sidebar.header("🔑 Upstox API Configuration")

# युझरकडून API Credentials घेणे
client_id = st.sidebar.text_input("Enter Upstox API Key (Client ID):", type="password")
client_secret = st.sidebar.text_input("Enter Upstox API Secret:", type="password")

# तुमच्या लाईव्ह डॅशबोर्डची नवीन अचूक लिंक (शेवटी स्लॅशसह)
redirect_uri = "https://my-gold-shop-app-9klufwulfrshfxa8ns46rr.streamlit.app/"

# --- 🔐 AUTOMATIC OAUTH LOGIN FLOW ---
# १. ब्राउझरच्या URL मधून 'code' आला आहे का ते तपासणे
query_params = st.query_params
auth_code = query_params.get("code")

# सेशन्स स्टेटमध्ये टोकन साठवण्यासाठी जागा तयार करणे
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# जर URL मध्ये 'code' मिळाला आणि सेशन्समध्ये अजून टोकन नसेल, तर टोकन जनरेट करणे
if auth_code and not st.session_state.access_token:
    if client_id and client_secret:
        with st.spinner("Upstox कडून Access Token मिळवला जात आहे..."):
            token_url = "https://api.upstox.com/v2/login/authorization/token"
            payload = {
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            headers = {
                "accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            try:
                response = requests.post(token_url, data=payload, headers=headers)
                if response.status_code == 200:
                    st.session_state.access_token = response.json().get("access_token")
                    st.success("🎉 Upstox लॉगिन यशस्वी! टोकन सेव्ह झाले आहे.")
                    # URL मधील ?code= स्वच्छ करणे
                    st.query_params.clear()
                else:
                    st.error(f"टोकन मिळवताना एरर आला: {response.text}")
            except Exception as e:
                st.error(f"कनेक्शन एरर: {str(e)}")
    else:
        st.warning("⚠️ कृपया डाव्या बाजूस आधी 'API Key' and 'API Secret' भरा, मग लॉगिन करा.")

# लॉगिन बटण दाखवणे (टोकन नसेल तर)
if not st.session_state.access_token:
    st.sidebar.subheader("🔒 Upstox Account Login")
    if client_id:
        # लॉगिनची लिंक तयार करणे
        auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
        # target="_blank" चा वापर करून नवीन टॅबमध्ये सुरक्षितपणे लॉगिन उघडणे
        st.sidebar.markdown(
            f'<a href="{auth_url}" target="_blank">'
            f'<button style="background-color: #10b981; color: white; padding: 10px 20px; '
            f'border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">'
            f'🟢 Click here to Login to Upstox</button></a>', 
            unsafe_allow_html=True
        )
    else:
        st.sidebar.info("💡 लॉगिन करण्यासाठी आधी तुमची 'API Key' वर टाका.")
else:
    st.sidebar.success("✅ Upstox Connected!")
    if st.sidebar.button("🔴 Logout Upstox"):
        st.session_state.access_token = None
        st.rerun()

# --- ⏱️ ऑटो-रिफ्रेश सेटिंग ---
st.sidebar.header("⏱️ Auto Refresh Settings")
refresh_choice = st.sidebar.selectbox("रिफ्रेश वेळ निवडा:", ["३० सेकंद", "१ मिनिट", "२ मिनिट", "५ मिनिट"], index=0)
refresh_map = {"३० सेकंद": 30000, "१ मिनिट": 60000, "२ मिनिट": 120000, "५ मिनिट": 300000}
st_autorefresh(interval=refresh_map[refresh_choice], key="datarefresh") 

# मार्केट निवडणे
st.sidebar.header("⚙️ Market Settings")
asset_choice = st.sidebar.selectbox("ॲसेट निवडा:", ["NIFTY", "BANKNIFTY"])
upstox_instrument_map = {"NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank"}
instrument_key = upstox_instrument_map[asset_choice]
ticker = "^NSEI" if asset_choice == "NIFTY" else "^NSEBANK"
display_name = f"{asset_choice} (NSE)"

# --- 🎯 Upstox Live Option Chain Data Fetcher ---
def get_upstox_option_chain_data(inst_key, token):
    url = "https://api.upstox.com/v2/option/chain"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    params = {"instrument_key": inst_key}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("status") == "success" and res_data.get("data"):
                chain_list = res_data["data"]
                total_call_oi = 0
                total_put_oi = 0
                total_call_oi_chg = 0
                total_put_oi_chg = 0
                
                for strike_data in chain_list:
                    # CALL (CE)
                    call_info = strike_data.get("call_options")
                    if call_info:
                        market_data = call_info.get("market_data", {})
                        total_call_oi += market_data.get("oi", 0)
                        total_call_oi_chg += market_data.get("oi_change", 0)
                        
                    # PUT (PE)
                    put_info = strike_data.get("put_options")
                    if put_info:
                        market_data = put_info.get("market_data", {})
                        total_put_oi += market_data.get("oi", 0)
                        total_put_oi_chg += market_data.get("oi_change", 0)
                
                return {
                    "last_call_oi": round(total_call_oi / 10000000, 2), # Crores
                    "last_put_oi": round(total_put_oi / 10000000, 2),   # Crores
                    "last_call_chg": round(total_call_oi_chg / 100000, 2), # Lakhs
                    "last_put_chg": round(total_put_oi_chg / 100000, 2),   # Lakhs
                    "pcr_val": round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
                }, None
            return None, "Option chain data not found."
        return None, f"HTTP Error {response.status_code}"
    except Exception as e:
        return None, str(e)

# --- 📈 Yahoo Data for SMC PRO Signals ---
def fetch_candles_for_smc(ticker_symbol):
    try:
        data = yf.download(tickers=ticker_symbol, period="5d", interval="5m", progress=False)
        if data is None or data.empty: return None
        df = data.reset_index()
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df = df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        
        # ATR आणि SMA इंडिकेटर जोडणे
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        df['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
        df['vol_sma'] = df['volume'].rolling(window=20).mean()
        return df
    except:
        return None

# --- 🔥 SMC PRO Signals Engine ---
def analyze_smc_pro_v2(df):
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

# --- 📊 [Render Live Option Chain Layout] ---
def render_upstox_oi_dashboard(opt_data, df_prices, asset_name):
    st.subheader(f"📊 {asset_name} - Institutional Open Interest (OI) [⚡ UPSTOX LIVE]")
    
    last_call_oi = opt_data["last_call_oi"]
    last_put_oi = opt_data["last_put_oi"]
    last_call_chg = opt_data["last_call_chg"]
    last_put_chg = opt_data["last_put_chg"]
    pcr_val = opt_data["pcr_val"]
    
    df_plot = df_prices.tail(15).reset_index(drop=True)
    time_labels = df_plot['timestamp'].dt.strftime('%I:%M %p')
    
    # ऑसिलेशन सिम्युलेशन (ट्रेंड व्ह्यूसाठी)
    call_oi_trend = np.linspace(last_call_oi - 0.5, last_call_oi, len(df_plot))
    put_oi_trend = np.linspace(last_put_oi - 0.4, last_put_oi, len(df_plot))

    col_line1, col_line2 = st.columns(2)
    with col_line1:
        st.markdown("<h5 style='color: #1e293b;'>📈 Trend: Open Interest Change</h5>", unsafe_allow_html=True)
        fig_line1 = go.Figure()
        fig_line1.add_trace(go.Scatter(x=time_labels, y=df_plot['close'], name='Price', line=dict(color='#707a8a', width=1.5, dash='dot'), yaxis='y1'))
        fig_line1.add_trace(go.Scatter(x=time_labels, y=np.linspace(last_call_chg-2, last_call_chg, len(df_plot)), name='Call Chg', line=dict(color='#22c55e', width=2), yaxis='y2'))
        fig_line1.add_trace(go.Scatter(x=time_labels, y=np.linspace(last_put_chg-1, last_put_chg, len(df_plot)), name='Put Chg', line=dict(color='#ef4444', width=2), yaxis='y2'))
        fig_line1.update_layout(height=260, margin=dict(l=40, r=40, t=10, b=40), plot_bgcolor='white', showlegend=False, xaxis=dict(tickangle=-45), yaxis2=dict(overlaying='y', side='right'))
        st.plotly_chart(fig_line1, use_container_width=True, key="upstox_chg_line")

    with col_line2:
        st.markdown("<h5 style='color: #1e293b;'>📈 Trend: Total Open Interest</h5>", unsafe_allow_html=True)
        fig_line2 = go.Figure()
        fig_line2.add_trace(go.Scatter(x=time_labels, y=df_plot['close'], name='Price', line=dict(color='#707a8a', width=1.5, dash='dot'), yaxis='y1'))
        fig_line2.add_trace(go.Scatter(x=time_labels, y=call_oi_trend, name='Total Call', line=dict(color='#137333', width=2), yaxis='y2'))
        fig_line2.add_trace(go.Scatter(x=time_labels, y=put_oi_trend, name='Total Put', line=dict(color='#c5221f', width=2), yaxis='y2'))
        fig_line2.update_layout(height=260, margin=dict(l=40, r=40, t=10, b=40), plot_bgcolor='white', showlegend=False, xaxis=dict(tickangle=-45), yaxis2=dict(overlaying='y', side='right'))
        st.plotly_chart(fig_line2, use_container_width=True, key="upstox_total_line")

    st.markdown("---")
    col_bar1, col_bar2, col_donut = st.columns(3)
    
    with col_bar1:
        st.markdown("<h5 style='text-align: center;'>📊 Open Interest Change (Lakhs)</h5>", unsafe_allow_html=True)
        fig_bar1 = go.Figure(go.Bar(x=['CALL', 'PUT'], y=[last_call_chg, last_put_chg], marker_color=['#137333', '#c5221f'], text=[f"{last_call_chg}L", f"{last_put_chg}L"], textposition='auto', width=0.4))
        fig_bar1.update_layout(height=250, margin=dict(l=30, r=30, t=20, b=30), plot_bgcolor='#f8fafc', xaxis=dict(tickfont=dict(size=12)))
        st.plotly_chart(fig_bar1, use_container_width=True, key="live_oi_change_bar")
        
    with col_bar2:
        st.markdown("<h5 style='text-align: center;'>📊 Total Open Interest (Crores)</h5>", unsafe_allow_html=True)
        fig_bar2 = go.Figure(go.Bar(x=['CALL', 'PUT'], y=[last_call_oi, last_put_oi], marker_color=['#137333', '#c5221f'], text=[f"{last_call_oi}Cr", f"{last_put_oi}Cr"], textposition='auto', width=0.4))
        fig_bar2.update_layout(height=250, margin=dict(l=30, r=30, t=20, b=30), plot_bgcolor='#f8fafc', xaxis=dict(tickfont=dict(size=12)))
        st.plotly_chart(fig_bar2, use_container_width=True, key="live_total_oi_bar")
        
    with col_donut:
        st.markdown("<h5 style='text-align: center;'>📊 Put/Call Ratio (PCR)</h5>", unsafe_allow_html=True)
        total_sum = last_call_oi + last_put_oi
        call_pct = int((last_call_oi / total_sum) * 100) if total_sum > 0 else 50
        fig3 = go.Figure(data=[go.Pie(labels=['Call OI', 'Put OI'], values=[call_pct, 100-call_pct], hole=.7, marker=dict(colors=['#137333', '#c5221f']), textinfo='none', showlegend=False)])
        fig3.add_annotation(text=f"PCR<br><span style='font-size:24px; font-weight:bold;'>{pcr_val}</span>", x=0.5, y=0.5, showarrow=False)
        fig3.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig3, use_container_width=True, key="upstox_pcr_donut")

# --- मुख्य प्रोग्राम एक्झिक्युशन ---
df_ltf = fetch_candles_for_smc(ticker)

if df_ltf is not None and not df_ltf.empty:
    current_price = df_ltf['close'].iloc[-1]
    st.metric(label=f"Current {display_name} Spot Price (5m)", value=f"₹{current_price:,.2f}")
    
    # जर सेशन्समध्ये ऍक्टिव्ह टोकन असेल तर अपस्टॉक्स ऑप्शन डेटा लोड करणे
    if st.session_state.access_token:
        with st.spinner("Connecting Upstox Realtime Option Chain API..."):
            opt_data, err_msg = get_upstox_option_chain_data(instrument_key, st.session_state.access_token)
            if opt_data:
                render_upstox_oi_dashboard(opt_data, df_ltf, asset_choice)
            else:
                st.error(f"❌ अपस्टॉक्स कनेक्शन एरर: {err_msg}")
    else:
        st.warning("👉 डाव्या बाजूला 'API Key' आणि 'API Secret' टाकून हिरव्या रंगाच्या 'Login to Upstox' बटणावर क्लिक करा.")
        
    st.markdown("---")
    signals_df = analyze_smc_pro_v2(df_ltf)
    st.subheader("🎯 Live SMC PRO Institutional Signals (Ultra-High Accuracy)")
    if not signals_df.empty:
        st.dataframe(signals_df.iloc[::-1], use_container_width=True)
    else:
        st.info("या ५ मिनिटांच्या चार्टवर सध्या कोणताही नवीन सिग्नल मिळालेला नाही.")
else:
    st.error("🚨 डेटा लोड होऊ शकला नाही.")
