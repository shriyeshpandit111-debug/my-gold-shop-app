import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import urllib.parse
import requests
import os
from datetime import datetime

# ==============================================================================
# १. प्रगत डेटाबेस सेटअप
# ==============================================================================
DB_FILE = "jewellery_erp_fixed.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# बिलांचा आणि ग्राहक CRM डेटाबेस टेबल
cursor.execute("""
CREATE TABLE IF NOT EXISTS billing_v4 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    customer_name TEXT,
    customer_phone TEXT,
    item_name TEXT,
    metal_type TEXT,
    company_name TEXT,
    weight REAL,
    rate_per_gm REAL,
    making_charge REAL,
    gst_percent REAL,
    old_gold_type TEXT,
    old_gold_item TEXT,
    old_value REAL,
    grand_total REAL,
    cash_paid REAL,
    balance_amount REAL,
    reminder_date TEXT,
    bill_note TEXT,
    item_size TEXT DEFAULT '',
    customer_dob TEXT DEFAULT ''
)
""")

# स्टॉक आणि कमी स्टॉक अलर्ट टेबल
cursor.execute("""
CREATE TABLE IF NOT EXISTS items_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metal_category TEXT,
    metal_type TEXT,
    item_name TEXT,
    company_name TEXT,
    stock_grams REAL,
    alert_limit REAL,
    item_size TEXT
)
""")

# कारागीर लेजर टेबल
cursor.execute("""
CREATE TABLE IF NOT EXISTS karigar_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    karigar_name TEXT,
    given_gold REAL,
    received_ornament_weight REAL,
    wastage_grams REAL,
    making_charges_paid REAL,
    status TEXT
)
""")

# जुनी मोड लेजर टेबल
cursor.execute("""
CREATE TABLE IF NOT EXISTS old_gold_melting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    total_weight_sent REAL,
    received_pure_weight REAL,
    refinery_name TEXT,
    status TEXT
)
""")
conn.commit()

# ==============================================================================
# २. लाइव्ह मार्केट डेटा ओढणे (Actual Live Metal Rate API)
# ==============================================================================
@st.cache_data(ttl=3600)  # दर एका तासाला भाव रिफ्रेश होतील
def fetch_live_metal_rates():
    try:
        # मोफत जागतिक मेटल रेट API
        url = "https://api.metals.dev/v1/latest?api_key=DEMO_KEY&currency=INR&unit=g"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            api_gold = data['rates']['gold']
            api_silver = data['rates']['silver']
            return round(api_gold, 2), round(api_silver, 2)
    except:
        pass
    return 7650.0, 93.0  # इंटरनेट नसल्यास चालू अंदाजे बॅकअप भाव

live_gold_24k, live_silver_rate = fetch_live_metal_rates()

# ==============================================================================
# ३. प्रगत लक्झरी इंटरफेस डिझाईन (Premium CSS UI)
# ==============================================================================
st.set_page_config(page_title="साईप्रसाद ज्वेलर्स AI SUPER PRO ERP", page_icon="👑", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; background-color: #fcfbf7; }
    .brand-header {
        background: linear-gradient(135deg, #111111 0%, #2c2512 100%);
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        border-bottom: 4px solid #D4AF37;
    }
    .luxury-card {
        background: #ffffff;
        border: 1px solid #eae5d8;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(170, 124, 17, 0.05);
    }
    .cart-summary-box {
        background: linear-gradient(135deg, #fdfbf7 0%, #f5eedc 100%);
        border: 2px dashed #D4AF37;
        border-radius: 12px;
        padding: 20px;
        color: #333;
    }
    .metric-box {
        background: #ffffff;
        border-left: 5px solid #AA7C11;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02);
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #111; }
    .red-alert-card { background: #FFF5F5; border-left: 5px solid #E74C3C; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #c0392b; }
    .stock-alert-card { background: #FFFDF3; border-left: 5px solid #F39C12; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #d35400; }
    .bday-card { background: #F3F8FF; border-left: 5px solid #3B82F6; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# साइडबार - चालू भाव व्यवस्थापन
st.sidebar.markdown("<h2 style='text-align: center; color: #AA7C11;'>👑 शॉप प्रोफाईल</h2>", unsafe_allow_html=True)
shop_name = st.sidebar.text_input("दुकानाचे नाव:", value="साईप्रसाद ज्वेलर्स")
shop_prop = st.sidebar.text_input("प्रोप्रायटर:", value="धनंजय कालिदास पंडित")
shop_address = st.sidebar.text_area("पत्ता:", value="मुख्य पेठ, महूद बु॥, ता. सांगोला.")

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #AA7C11;'>📈 थेट बाजारभाव (Live Market API)</h3>", unsafe_allow_html=True)
gold_24k_rate = st.sidebar.number_input("24K सोने दर प्रति ग्रॅम (Live):", value=float(live_gold_24k))
gold_22k_rate = round(gold_24k_rate * 0.916, 2)
gold_18k_rate = round(gold_24k_rate * 0.750, 2)
silver_rate = st.sidebar.number_input("चांदी दर प्रति ग्रॅम (Live):", value=float(live_silver_rate))

st.sidebar.info(f"स्वयंचलित कॅल्क्युलेट झालेले दर:\n- 22K सोने: ₹{gold_22k_rate}/gm\n- 18K सोने: ₹{gold_18k_rate}/gm")

# टॉप ब्रँड हेडर
st.markdown(f"""
<div class="brand-header">
    <h1 style="color: #D4AF37; margin: 0; font-size: 38px; letter-spacing: 1px;">👑 {shop_name} 👑</h1>
    <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px; color: #f5eedc;">AI-POWERED ULTRA SMART MANAGEMENT SYSTEM PRO</p>
</div>
""", unsafe_allow_html=True)

# सुधारित मुख्य मेनू बार
menu = [
    "🏠 डॅशबोर्ड व स्मार्ट अलर्ट्स", "🧾 बिलिंग काउंटर", "👤 ग्राहक लेजर खाते", "📦 स्टॉक व्यवस्थापन", 
    "🔨 कारागीर लेजर", "🔄 जुनी मोड लेजर", "📈 GST व नफा-तोटा", "⚙️ बॅकअप व रिस्टोर"
]
choice = st.radio("मुख्य मेनू निवडा:", menu, horizontal=True, label_visibility="collapsed")

# ==============================================================================
# विभाग १: डॅशबोर्ड व स्मार्ट अलर्ट्स
# ==============================================================================
if choice == "🏠 डॅशबोर्ड व स्मार्ट अलर्ट्स":
    df_bills_count = pd.read_sql_query("SELECT COUNT(id) as total_bills, SUM(balance_amount) as total_udhari FROM billing_v4", conn)
    df_stock_count = pd.read_sql_query("SELECT SUM(stock_grams) as total_gold FROM items_stock WHERE metal_category='Gold'", conn)
    df_silver_count = pd.read_sql_query("SELECT SUM(stock_grams) as total_silver FROM items_stock WHERE metal_category='Silver'", conn)

    total_b = df_bills_count['total_bills'].values[0] or 0
    total_u = df_bills_count['total_udhari'].values[0] or 0.0
    total_g_stock = df_stock_count['total_gold'].values[0] or 0.0
    total_s_stock = df_silver_count['total_silver'].values[0] or 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-box" style="border-left-color: #D4AF37;"><div style="color:#777; font-size:14px;">🧾 एकूण बिले</div><div class="metric-val">{total_b} नग</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-box" style="border-left-color: #E74C3C;"><div style="color:#777; font-size:14px;">🔴 एकूण थकीत उधारी</div><div class="metric-val">₹{total_u:,.2f}</div></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-box" style="border-left-color: #2ECC71;"><div style="color:#777; font-size:14px;">👑 सोने एकूण स्टॉक</div><div class="metric-val">{total_g_stock:.3f} g</div></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-box" style="border-left-color: #9B59B6;"><div style="color:#777; font-size:14px;">🥈 चांदी एकूण स्टॉक</div><div class="metric-val">{total_s_stock:.3f} g</div></div>', unsafe_allow_html=True)

    st.write("---")
    al1, al2, al3 = st.columns(3)
    
    with al1:
        st.markdown("<h3 style='color: #E74C3C;'>🚨 उधारी रेड अलर्ट</h3>", unsafe_allow_html=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        df_overdue = pd.read_sql_query("SELECT customer_name, balance_amount, reminder_date FROM billing_v4 WHERE balance_amount > 0 AND reminder_date < ?", conn, params=(today_str,))
        if df_overdue.empty:
            st.success("सर्व उधारी वेळेत जमा आहेत!")
        else:
            for idx, row in df_overdue.iterrows():
                st.markdown(f'<div class="red-alert-card">⚠️ <b>{row["customer_name"]}</b><br>थकीत: <b>₹{row["balance_amount"]:.2f}</b> (वायदा: {row["reminder_date"]})</div>', unsafe_allow_html=True)

    with al2:
        st.markdown("<h3 style='color: #F39C12;'>⚠️ कमी स्टॉक अलर्ट (Low Stock)</h3>", unsafe_allow_html=True)
        df_low_stock = pd.read_sql_query("SELECT item_name, stock_grams, alert_limit FROM items_stock WHERE stock_grams <= alert_limit", conn)
        if df_low_stock.empty:
            st.success("सर्व वस्तूंचा स्टॉक पुरेसा आहे!")
        else:
            for idx, row in df_low_stock.iterrows():
                st.markdown(f'<div class="stock-alert-card">📦 <b>{row["item_name"]}</b><br>शिल्लक: <span style="color:red;"><b>{row["stock_grams"]}g</b></span> (मर्यादा: {row["alert_limit"]}g)</div>', unsafe_allow_html=True)

    with al3:
        st.markdown("<h3 style='color: #3B82F6;'>🎂 आजचे ग्राहक वाढदिवस (CRM)</h3>", unsafe_allow_html=True)
        today_md = datetime.now().strftime("-%m-%d")
        df_birthdays = pd.read_sql_query("SELECT DISTINCT customer_name, customer_phone FROM billing_v4 WHERE customer_dob LIKE ?", conn, params=(f"%{today_md}",))
        if df_birthdays.empty:
            st.info("आज कोणत्याही ग्राहकाचा वाढदिवस नाही.")
        else:
            for idx, r in df_birthdays.iterrows():
                b_msg = f"✨ *{shop_name}* ✨\n\nप्रिय ग्राहक *{r['customer_name']}*,\nतुम्हाला वाढदिवसाच्या हार्दिक शुभेच्छा! 🎂💐\nशुभेच्छुक: {shop_prop}"
                enc_b_msg = urllib.parse.quote(b_msg)
                wp_b_url = f"https://api.whatsapp.com/send?phone=91{r['customer_phone']}&text={enc_b_msg}"
                st.markdown(f'<div class="bday-card">🎉 <b>{r["customer_name"]}</b></div>', unsafe_allow_html=True)
                st.link_button("🎁 WhatsApp वर शुभेच्छा पाठवा", url=wp_b_url, type="primary")

    st.write("---")
    df_chart_data = pd.read_sql_query("SELECT metal_type, grand_total, date FROM billing_v4", conn)
    if not df_chart_data.empty:
        st.markdown("<h3 style='color: #AA7C11;'>📊 व्यवसाय स्मार्ट आलेख विश्लेषण</h3>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.write("🪙 धातू प्रकारानुसार एकूण विक्री विभागणी")
            st.bar_chart(df_chart_data.groupby('metal_type')['grand_total'].sum())
        with g2:
            st.write("📈 मासिक व्यवसाय प्रगती आलेख")
            df_chart_data['month'] = df_chart_data['date'].str[:7]
            st.line_chart(df_chart_data.groupby('month')['grand_total'].sum())

# ==============================================================================
# विभाग २: डिजिटल बिलिंग काउंटर (कॅमेरा स्कॅनरशिवाय)
# ==============================================================================
elif choice == "🧾 बिलिंग काउंटर":
    st.markdown("<h2 style='color: #AA7C11;'>🧾 प्रगत डिजिटल बिल काउंटर</h2>", unsafe_allow_html=True)
    
    col_bill_left, col_bill_right = st.columns([3, 2])
    
    with col_bill_left:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("👤 ग्राहक नोंदणी (CRM)")
        cl1, cl2, cl3 = st.columns(3)
        with cl1: cust_name = st.text_input("ग्राहकाचे पूर्ण नाव:")
        with cl2: cust_phone = st.text_input("मोबाईल (WhatsApp):")
        with cl3: cust_dob = st.date_input("जन्मतारीख (वाढदिवस अलर्टसाठी):", value=None)
        bill_note = st.text_area("बिलावरील विशेष नोट:", value="१. हॉलमार्क दागिन्यांची १००% शुद्धतेची हमी.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("🛍️ दागिन्याची माहिती व मजुरी")
        df_avail = pd.read_sql_query("SELECT id, metal_category, metal_type, item_name, stock_grams, item_size FROM items_stock WHERE stock_grams > 0", conn)
        
        if df_avail.empty:
            st.error("स्टॉकमध्ये दागिने उपलब्ध नाहीत! कृपया आधी स्टॉक भरा.")
            selected_item_id = None
        else:
            item_options = {row['id']: f"आयडी #{row['id']} | {row['item_name']} [साइज: {row['item_size']} | शिल्लक: {row['stock_grams']}g]" for idx, row in df_avail.iterrows()}
            selected_item_id = st.selectbox("वस्तू निवड करा:", options=list(item_options.keys()), format_func=lambda x: item_options[x])
            
        if selected_item_id:
            cursor.execute("SELECT metal_type, item_name, company_name, stock_grams, metal_category, item_size FROM items_stock WHERE id=?", (selected_item_id,))
            m_type, i_name, c_name, s_grams, m_cat, i_size = cursor.fetchone()
            
            w1, w2, w3 = st.columns(3)
            with w1:
                default_rate = silver_rate if m_cat == "Silver" else (gold_22k_rate if m_type == "Gold 22K" else gold_24k_rate)
                live_rate = st.number_input("आजचा विक्री दर प्रति ग्रॅम (₹):", value=default_rate)
            with w2:
                weight = st.number_input(f"दागिन्याचे वजन (Max {s_grams}g):", min_value=0.0, max_value=s_grams, value=s_grams)
            with w3:
                making_charge = st.number_input("मजुरी / घडणावळ (₹):", min_value=0.0)
                
            st.markdown("---")
            st.subheader("🔀 टॅक्स व जुनी मोड वजावट")
            tx1, tx2 = st.columns(2)
            with tx1: gst_select = st.selectbox("GST टक्केवारी (%):", [0.0, 3.0, 1.0])
            with tx2: old_value = st.number_input("जुन्या मोडीचे मूल्य (वजा करायची रक्कम) ₹:", min_value=0.0)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_bill_right:
        if selected_item_id:
            st.markdown("<div class='cart-summary-box'>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center; color:#AA7C11; margin-top:0;'>🛒 बिलाचा लाइव्ह डिजिटल हिशोब</h3>", unsafe_allow_html=True)
            
            metal_cost = weight * live_rate
            subtotal = metal_cost + making_charge
            gst_cost = subtotal * (gst_select / 100)
            grand_total = subtotal + gst_cost
            payable_amt = max(0.0, grand_total - old_value)
            
            st.markdown(f"""
            • <b>वस्तू:</b> {i_name} ({m_type})<br>
            • <b>माप / साइज:</b> {i_size}<br>
            • <b>वजन:</b> {weight} ग्रॅम<br>
            • <b>धातू मूल्य:</b> ₹{metal_cost:,.2f}<br>
            • <b>मजुरी:</b> ₹{making_charge:,.2f}<br>
            • <b>GST ({gst_select}%):</b> ₹{gst_cost:,.2f}<br>
            <hr style='border:1px dashed #D4AF37;'>
            • <b>एकूण मूल्य:</b> ₹{grand_total:,.2f}<br>
            • <b>जुनी मोड वजावट:</b> - ₹{old_value:,.2f}<br>
            <h3 style='color:#AA7C11; margin:10px 0;'>देय रक्कम: ₹{payable_amt:,.2f}</h3>
            """, unsafe_allow_html=True)
            
            cash_paid = st.number_input("भरलेली रोकड/जमा रक्कम:", min_value=0.0, max_value=float(payable_amt), value=float(payable_amt))
            balance_amount = payable_amt - cash_paid
            
            st.markdown(f"<h4 style='color:red;'>बाकी उधारी: ₹{balance_amount:,.2f}</h4>", unsafe_allow_html=True)
            reminder_date = st.date_input("उधारी परत करण्याची वायदा तारीख:")
            
            st.write(" ")
            if st.button("👑 फायनल बिल सुरक्षित सेव्ह करा", type="primary", use_container_width=True):
                if cust_name == "" or cust_phone == "":
                    st.error("ग्राहकाचे नाव व फोन नंबर आवश्यक आहे!")
                else:
                    today_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    dob_str = str(cust_dob) if cust_dob else ""
                    cursor.execute("""
                    INSERT INTO billing_v4 (date, customer_name, customer_phone, item_name, metal_type, company_name, weight, rate_per_gm, making_charge, gst_percent, old_value, grand_total, cash_paid, balance_amount, reminder_date, bill_note, item_size, customer_dob)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today_now, cust_name, cust_phone, i_name, m_type, c_name, weight, live_rate, making_charge, gst_select, old_value, grand_total, cash_paid, balance_amount, str(reminder_date), bill_note, i_size, dob_str))
                    cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                    conn.commit()
                    st.success("🎉 बिल यशस्वीरित्या जमा झाले व स्टॉक अपडेट झाला!")
            st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ३: ग्राहक लेजर खाते (Customer Ledger & Search History)
# ==============================================================================
elif choice == "👤 ग्राहक लेजर खाते":
    st.markdown("<h2 style='color: #AA7C11;'>👤 ग्राहक लेजर, उधारी पेमेंट आणि संपूर्ण इतिहास</h2>", unsafe_allow_html=True)
    st.write("---")
    
    search_type = st.radio("सर्च प्रकार निवडा:", ["ग्राहकाच्या नावाने सर्च करा", "बिल नंबर (ID) नुसार सर्च करा"], horizontal=True)
    
    df_all_c = pd.read_sql_query("SELECT id, customer_name, balance_amount FROM billing_v4", conn)
    
    if df_all_c.empty:
        st.info("डेटाबेसमध्ये सध्या एकही ग्राहक उपलब्ध नाही.")
    else:
        selected_cust_name = None
        selected_bill_id = None
        
        if search_type == "ग्राहकाच्या नावाने सर्च करा":
            names_list = df_all_c['customer_name'].unique()
            selected_cust_name = st.selectbox("ग्राहक निवडा:", names_list)
            df_cust_history = pd.read_sql_query("SELECT id, date, item_name, metal_type, weight, grand_total, cash_paid, balance_amount, reminder_date FROM billing_v4 WHERE customer_name = ?", conn, params=(selected_cust_name,))
        else:
            id_list = df_all_c['id'].tolist()
            selected_bill_id = st.selectbox("बिल आयडी (ID) निवडा:", id_list)
            df_cust_history = pd.read_sql_query("SELECT id, date, customer_name, item_name, metal_type, weight, grand_total, cash_paid, balance_amount, reminder_date FROM billing_v4 WHERE id = ?", conn, params=(selected_bill_id,))
            if not df_cust_history.empty:
                selected_cust_name = df_cust_history['customer_name'].values[0]

        if selected_cust_name and not df_cust_history.empty:
            st.markdown(f"<div class='luxury-card'><h3>👤 ग्राहक: {selected_cust_name}</h3>", unsafe_allow_html=True)
            
            total_pending = df_cust_history['balance_amount'].sum()
            st.markdown(f"<h4>🔴 एकूण प्रलंबित उधारी: <span style='color:red;'>₹{total_pending:,.2f}</span></h4>", unsafe_allow_html=True)
            
            if total_pending > 0:
                st.write("---")
                st.subheader("💰 उधारी जमा (Payment Split Mode)")
                pay_amt = st.number_input("जमा करायची रक्कम (₹):", min_value=1.0, max_value=float(total_pending))
                if st.button("✅ उधारी खाते जमा करा", type="primary"):
                    # उधारी हिशोब कमी करणे
                    cursor.execute("SELECT id, balance_amount FROM billing_v4 WHERE customer_name=? AND balance_amount > 0 ORDER BY id ASC", (selected_cust_name,))
                    rows = cursor.fetchall()
                    temp_pay = pay_amt
                    for r_id, b_amt in rows:
                        if temp_pay <= 0: break
                        if temp_pay >= b_amt:
                            cursor.execute("UPDATE billing_v4 SET cash_paid = cash_paid + ?, balance_amount = 0 WHERE id=?", (b_amt, r_id))
                            temp_pay -= b_amt
                        else:
                            cursor.execute("UPDATE billing_v4 SET cash_paid = cash_paid + ?, balance_amount = balance_amount - ? WHERE id=?", (temp_pay, temp_pay, r_id))
                            temp_pay = 0
                    conn.commit()
                    st.success(f"Successfully Updated ₹{pay_amt} in accounts!")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.subheader("📜 खरेदी व बिलांचा संपूर्ण इतिहास (All History)")
            st.dataframe(df_cust_history, use_container_width=True)

# ==============================================================================
# विभाग ४: स्टॉक व्यवस्थापन (धातू कस्टमायझेशन आणि आयटम साइजसह)
# ==============================================================================
elif choice == "📦 स्टॉक व्यवस्थापन":
    st.markdown("<h2 style='color: #AA7C11;'>📦 स्टॉक इन्व्हेंटरी (कॅटेगरी वाईज प्रकार आणि साइज सोय)</h2>", unsafe_allow_html=True)
    st.write("---")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("➕ नवीन स्टॉक जोडा")
        s_category = st.selectbox("कॅटेगरी:", ["Gold", "Silver"])
        
        # स्वतंत्र धातू प्रकार फिल्टर
        if s_category == "Gold":
            s_type = st.selectbox("प्रकार (फक्त सोने):", ["Gold 24K", "Gold 22K", "Gold 18K"])
        else:
            s_type = st.selectbox("प्रकार (फक्त चांदी):", ["Silver Pure", "Silver Sterling"])
            
        s_item_name = st.text_input("दागिन्याचे नाव (उदा. अंगठी, चेन):")
        s_size = st.text_input("दागिन्याचा आकार / माप (Item Size):", value="14 No")
        s_grams = st.number_input("एकूण वजन (ग्रॅम):", min_value=0.0, step=0.01)
        s_alert = st.number_input("किमान स्टॉक अलर्ट लिमिट (g):", min_value=0.0, value=2.0)
        
        if st.button("📥 सुरक्षित स्टॉक जमा करा", use_container_width=True):
            cursor.execute("INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit, item_size) VALUES (?, ?, ?, 'Own', ?, ?, ?)", 
                           (s_category, s_type, s_item_name, s_grams, s_alert, s_size))
            conn.commit()
            st.success("स्टॉकमध्ये नवीन दागिना जोडला गेला!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_s2:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("📋 सध्या उपलब्ध स्टॉक यादी")
        df_stock = pd.read_sql_query("SELECT id as कोड, item_name as 'नाव', metal_type as 'प्रकार', item_size as 'साइज/माप', stock_grams as 'वजन (g)', alert_limit as 'अलर्ट मर्यादा' FROM items_stock WHERE stock_grams > 0", conn)
        st.dataframe(df_stock, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ५: कारागीर लेजर
# ==============================================================================
elif choice == "🔨 कारागीर लेजर":
    st.markdown("<h2 style='color: #AA7C11;'>🔨 कारागीर लेजर (Karigar Diary)</h2>", unsafe_allow_html=True)
    col_k1, col_k2 = st.columns([1, 2])
    with col_k1:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("📝 कारागीर हिशोब नोंद")
        k_name = st.text_input("कारागिराचे नाव:")
        g_gold = st.number_input("दिलेले शुद्ध सोने वजन (g):", min_value=0.0)
        r_gold = st.number_input("प्राप्त तयार दागिन्याचे वजन (g):", min_value=0.0)
        wastage = st.number_input("ठरलेले वेस्टेज/घट (g):", min_value=0.0)
        m_paid = st.number_input("दिलेली मजुरी रक्कम (₹):", min_value=0.0)
        
        if st.button("💾 कारागीर खात्यात नोंदवा", use_container_width=True):
            t_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO karigar_ledger (date, karigar_name, given_gold, received_ornament_weight, wastage_grams, making_charges_paid, status) VALUES (?, ?, ?, ?, ?, ?, 'Completed')", (t_date, k_name, g_gold, r_gold, wastage, m_paid))
            conn.commit()
            st.success("कारागीर लेजर नोंद यशस्वी झाली!")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_k2:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        df_k = pd.read_sql_query("SELECT date as तारीख, karigar_name as कारागीर, given_gold as 'दिलेले सोने (g)', received_ornament_weight as 'प्राप्त दागिना (g)', wastage_grams as 'वेस्टेज घट (g)', making_charges_paid as 'मजुरी दिली' FROM karigar_ledger", conn)
        st.dataframe(df_k, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ६: जुनी मोड लेजर
# ==============================================================================
elif choice == "🔄 जुनी मोड लेजर":
    st.markdown("<h2 style='color: #AA7C11;'>🔄 जमा जुनी मोड खरेदी व रिफायनरी हिशोब</h2>", unsafe_allow_html=True)
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("📥 वितळवण्यासाठी पाठवलेली मोड")
        ref_name = st.text_input("रिफायनरी / पेढीचे नाव:")
        w_sent = st.number_input("एकूण पाठवलेले मोडीचे वजन (g):", min_value=0.0)
        w_recv = st.number_input("परत मिळालेले २४K शुद्ध सोने वजन (g):", min_value=0.0)
        
        if st.button("🔄 मोडीची स्वतंत्र नोंद करा", use_container_width=True):
            t_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO old_gold_melting (date, total_weight_sent, received_pure_weight, refinery_name, status) VALUES (?, ?, ?, ?, 'Melted')", (t_date, w_sent, w_recv, ref_name))
            conn.commit()
            st.success("जुनी मोड लेजर सुरक्षित अपडेट झाले!")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_m2:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        df_m = pd.read_sql_query("SELECT date as तारीख, refinery_name as 'रिफायनरी पेढी', total_weight_sent as 'पाठवलेले वजन (g)', received_pure_weight as 'मिळालेले शुद्ध सोने (g)' FROM old_gold_melting", conn)
        st.dataframe(df_m, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ७: GST आणि नफा-तोटा विभाग
# ==============================================================================
elif choice == "📈 GST व नफा-तोटा":
    st.markdown("<h2 style='color: #AA7C11;'>📈 महिन्याचा GST रिपोर्ट आणि निव्वळ नफा (Profit) ट्रॅकर</h2>", unsafe_allow_html=True)
    df_bills = pd.read_sql_query("SELECT date, grand_total, weight, rate_per_gm, making_charge, gst_percent FROM billing_v4", conn)
    
    if df_bills.empty:
        st.info("नफा आणि GST रिपोर्ट ट्रॅक करण्यासाठी आधी बिले बनवा.")
    else:
        df_bills['विक्री धातू किंमत'] = df_bills['weight'] * df_bills['rate_per_gm']
        df_bills['निव्वळ नफा (Profit)'] = df_bills['making_charge'] # मजुरी हा मुख्य नफा
        df_bills['जमा GST कर'] = (df_bills['विक्री धातू किंमत'] + df_bills['making_charge']) * (df_bills['gst_percent'] / 100)
        
        g1, g2 = st.columns(2)
        with g1: st.markdown(f'<div class="metric-box" style="border-left-color:#2ECC71;"><div style="color:#777;">💸 एकूण मजुरी निव्वळ नफा</div><div class="metric-val">₹{df_bills["निव्वळ नफा (Profit)"].sum():,.2f}</div></div>', unsafe_allow_html=True)
        with g2: st.markdown(f'<div class="metric-box" style="border-left-color:#3498DB;"><div style="color:#777;">🏛️ गोळा झालेला एकूण GST कर</div><div class="metric-val">₹{df_bills["जमा GST कर"].sum():,.2f}</div></div>', unsafe_allow_html=True)
        st.write("---")
        st.dataframe(df_bills[['date', 'weight', 'grand_total', 'निव्वळ नफा (Profit)', 'जमा GST कर']], use_container_width=True)

# ==============================================================================
# विभाग ८: डेटाबेस बॅकअप आणि रिस्टोर सोय (Backup & Restore Option)
# ==============================================================================
elif choice == "⚙️ बॅकअप व रिस्टोर":
    st.markdown("<h2 style='color: #AA7C11;'>⚙️ डेटाबेस क्लाउड सुरक्षितता (Backup & Restore Panel)</h2>", unsafe_allow_html=True)
    st.write("---")
    
    c_back, c_rest = st.columns(2)
    
    with c_back:
        st.markdown("<div class='luxury-card'><h3>📥 १. बॅकअप डाउनलोड करा</h3>", unsafe_allow_html=True)
        st.write("तुमचा संपूर्ण सुरक्षित डेटा एका फाईलमध्ये डाउनलोड करून कॉम्प्युटर किंवा गुगल ड्राइव्हवर सुरक्षित ठेवा.")
        with open(DB_FILE, "rb") as f:
            st.download_button(label="💾 डाउनलोड सुरक्षित बॅकअप (.DB File)", data=f.read(), file_name="sai_prasad_jewellers_master.db", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c_rest:
        st.markdown("<div class='luxury-card'><h3>📤 २. जुना डेटा रिस्टोर करा (Restore Data)</h3>", unsafe_allow_html=True)
        st.write("कॉम्प्युटर बदलल्यास किंवा जुना डेटा परत सॉफ्टवेअरमध्ये आणण्यासाठी बॅकअप फाईल येथे अपलोड करा.")
        uploaded_file = st.file_uploader("तुमची जुनी .db बॅकअप फाईल निवडा:", type=["db"])
        if uploaded_file is not None:
            if st.button("⚠️ रिस्टोर प्रक्रिया सुरू करा", type="primary", use_container_width=True):
                with open(DB_FILE, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("🎉 डेटा यशस्वीरित्या रिस्टोर (Restore) झाला आहे! कृपया सर्व पेजेस रिफ्रेश करा.")
        st.markdown("</div>", unsafe_allow_html=True)
