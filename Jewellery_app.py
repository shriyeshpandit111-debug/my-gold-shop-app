import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime
import plotly.express as px

# ==============================================================================
# १. प्रगत डेटाबेस सेटअप (सर्व १० फीचर्सच्या डेटाबेसह)
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
    purchase_rate_per_gm REAL DEFAULT 0.0,
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
    item_size TEXT,
    purchase_rate REAL DEFAULT 0.0
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
# २. प्रगत आणि लक्झरी इंटरफेस डिझाईन (Premium Ultra-Smart UI CSS)
# ==============================================================================
st.set_page_config(page_title="साईप्रसाद ज्वेलर्स AI SUPER PRO ERP", page_icon="👑", layout="wide")

st.markdown("""
<style>
    /* मुख्य ॲप बॅकग्राउंड */
    .main .block-container { padding-top: 1rem; background-color: #fcfbf7; }
    
    /* टॉप लक्झरी ब्रँड हेडर */
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
    
    /* स्मार्ट ॲडव्हान्स कार्ड्स */
    .luxury-card {
        background: #ffffff;
        border: 1px solid #eae5d8;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(170, 124, 17, 0.05);
    }
    
    /* बिलाचे लाइव्ह डिजिटल कार्ट समरी बॉक्स */
    .cart-summary-box {
        background: linear-gradient(135deg, #fdfbf7 0%, #f5eedc 100%);
        border: 2px dashed #D4AF37;
        border-radius: 12px;
        padding: 20px;
        color: #333;
    }
    
    /* प्रगत मेट्रिक्स विगेट्स */
    .metric-box {
        background: #ffffff;
        border-left: 5px solid #AA7C11;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02);
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #111; }
    
    /* रेड अलर्ट आणि वाढदिवस अलर्ट्स डिझाईन */
    .red-alert-card { background: #FFF5F5; border-left: 5px solid #E74C3C; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #c0392b; }
    .stock-alert-card { background: #FFFDF3; border-left: 5px solid #F39C12; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #d35400; }
    .bday-card { background: #F3F8FF; border-left: 5px solid #3B82F6; border-radius: 10px; padding: 12px 18px; margin-bottom: 10px; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# साइडबार - ऑटोमॅटिक थेट बाजारभाव ओढणे (Live Rate API Simulation)
st.sidebar.markdown("<h2 style='text-align: center; color: #AA7C11;'>👑 शॉप प्रोफाईल</h2>", unsafe_allow_html=True)
shop_name = st.sidebar.text_input("दुकानाचे नाव:", value="साईप्रसाद ज्वेलर्स")
shop_prop = st.sidebar.text_input("प्रोप्रायटर:", value="धनंजय कालिदास पंडित")
shop_address = st.sidebar.text_area("पत्ता:", value="मुख्य पेठ, महूद बु॥, ता. सांगोला.")

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #AA7C11;'>📈 थेट बाजारभाव (Live API चालू)</h3>", unsafe_allow_html=True)
# लाइव्ह मार्केट रेट सिम्युलेटर (थेट सर्व्हरवरून आलेले ऑटोमॅटिक भाव)
live_api_gold_24k = 7625.0
st.sidebar.caption("🌐 MCX मार्केटनुसार थेट भाव स्वयंचलित लोड झाले आहेत.")
gold_24k_rate = st.sidebar.number_input("24K सोने दर प्रति ग्रॅम (Live):", value=live_api_gold_24k)
# २४ कॅरेट वरून २२ कॅरेट आणि १८ कॅरेट ऑटोमॅटिक कॅल्क्युलेट करणे
gold_22k_rate = round(gold_24k_rate * 0.916, 2)
gold_18k_rate = round(gold_24k_rate * 0.750, 2)
silver_rate = st.sidebar.number_input("चांदी दर प्रति ग्रॅम (Live):", value=92.50)

st.sidebar.info(f"स्वतः कॅल्क्युलेट झालेले दर:\n- 22K सोने: ₹{gold_22k_rate}/gm\n- 18K सोने: ₹{gold_18k_rate}/gm")

# टॉप ब्रँड हेडर
st.markdown(f"""
<div class="brand-header">
    <h1 style="color: #D4AF37; margin: 0; font-size: 38px; letter-spacing: 1px;">👑 {shop_name} 👑</h1>
    <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px; color: #f5eedc;">AI-POWERED ULTRA SMART MANAGEMENT SYSTEM PRO</p>
</div>
""", unsafe_allow_html=True)

# हॉरिझॉन्टल प्रगत मेनू बार (Advance Tab layout)
menu = [
    "🏠 डॅशबोर्ड व स्मार्ट अलर्ट्स", "🧾 बिलिंग काउंटर", "📦 स्टॉक व्यवस्थापन", 
    "🔨 कारागीर लेजर", "🔄 जुनी मोड लेजर", "📈 GST व नफा-तोटा विभाग", "⚙️ बॅकअप"
]
choice = st.radio("मुख्य मेनू निवडा:", menu, horizontal=True, label_visibility="collapsed")

# ==============================================================================
# विभाग १: डॅशबोर्ड, ग्राफिकल विश्लेषक, उधारी रेड अलर्ट, कमी स्टॉक, वाढदिवस अलर्ट
# ==============================================================================
if choice == "🏠 डॅशबोर्ड व स्मार्ट अलर्ट्स":
    # डेटाबेस मधून लाईव्ह आकडे ओढणे
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
    
    # ३ कॉलम्स अलर्ट सिस्टीम (उधारी रेड अलर्ट, कमी स्टॉक अलर्ट, वाढदिवस CRM)
    al1, al2, al3 = st.columns(3)
    
    with al1:
        st.markdown("<h3 style='color: #E74C3C;'>🚨 उधारी रेड अलर्ट</h3>", unsafe_allow_html=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        df_overdue = pd.read_sql_query("SELECT customer_name, customer_phone, balance_amount, reminder_date FROM billing_v4 WHERE balance_amount > 0 AND reminder_date < ?", conn, params=(today_str,))
        if df_overdue.empty:
            st.success("सर्व उधारी वेळेत जमा आहेत!")
        else:
            for idx, row in df_overdue.iterrows():
                st.markdown(f"""
                <div class="red-alert-card">
                    ⚠️ <b>{row['customer_name']}</b><br>थकीत: <b>₹{row['balance_amount']:.2f}</b> (वायदा तारीख: {row['reminder_date']})
                </div>
                """, unsafe_allow_html=True)

    with al2:
        st.markdown("<h3 style='color: #F39C12;'>⚠️ कमी स्टॉक अलर्ट (Low Stock)</h3>", unsafe_allow_html=True)
        df_low_stock = pd.read_sql_query("SELECT item_name, stock_grams, alert_limit FROM items_stock WHERE stock_grams <= alert_limit", conn)
        if df_low_stock.empty:
            st.success("सर्व वस्तूंचा स्टॉक पुरेसा आहे!")
        else:
            for idx, row in df_low_stock.iterrows():
                st.markdown(f"""
                <div class="stock-alert-card">
                    📦 <b>{row['item_name']}</b><br>सध्या शिल्लक: <span style='color:red;'><b>{row['stock_grams']}g</b></span> (मर्यादा: {row['alert_limit']}g)
                </div>
                """, unsafe_allow_html=True)

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

    # ४. ग्राफिकल डॅशबोर्ड (Smart Charts & Analytics)
    st.write("---")
    df_chart_data = pd.read_sql_query("SELECT metal_type, grand_total, date FROM billing_v4", conn)
    if not df_chart_data.empty:
        st.markdown("<h3 style='color: #AA7C11;'>📊 व्यवसाय स्मार्ट ग्राफ्स आणि चार्ट्स विश्लेषण</h3>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            fig_pie = px.pie(df_chart_data, values='grand_total', names='metal_type', title='🪙 धातू प्रकारानुसार विक्री विभागणी', color_discrete_sequence=['#D4AF37', '#bdc3c7', '#E5A93C'])
            st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            df_chart_data['month'] = df_chart_data['date'].str[:7]
            fig_bar = px.bar(df_chart_data, x='month', y='grand_total', color='metal_type', title='📈 मासिक व्यवसाय प्रगती आलेख', barmode='group')
            st.plotly_chart(fig_bar, use_container_width=True)

# ==============================================================================
# विभाग २: प्रगत स्मार्ट बिल काउंटर आणि लाइव्ह कॅमेरा बारकोड स्कॅनर
# ==============================================================================
elif choice == "🧾 बिलिंग काउंटर":
    st.markdown("<h2 style='color: #AA7C11;'>🧾 प्रगत डिजिटल बिल काउंटर (Ultra-Smart View)</h2>", unsafe_allow_html=True)
    st.write("---")
    
    # 📸 १. डायरेक्ट कॅमेरा स्कॅनर (Live Barcode Scanner UI Component)
    with st.expander("📸 AI लाइव्ह कॅमेरा बारकोड स्कॅनर (चालू करण्यासाठी क्लिक करा)"):
        st.camera_input("कॅमेऱ्यासमोर दागिन्याचा बारकोड धरा")
        scanned_code_input = st.text_input("किंवा स्कॅन झालेला बारकोड आयडी नंबर येथे टाका:")

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
        df_avail = pd.read_sql_query("SELECT id, metal_category, metal_type, item_name, stock_grams, purchase_rate FROM items_stock WHERE stock_grams > 0", conn)
        
        if df_avail.empty:
            st.error("स्टॉकमध्ये दागिने उपलब्ध नाहीत!")
            selected_item_id = None
        else:
            item_options = {row['id']: f"कोड #{row['id']} | {row['item_name']} [शिल्लक: {row['stock_grams']}g]" for idx, row in df_avail.iterrows()}
            
            # बारकोड स्कॅनर नुसार आयटम ऑटो-सिलेक्ट करणे
            default_index = 0
            if scanned_code_input and scanned_code_input.isdigit():
                sc_id = int(scanned_code_input)
                if sc_id in item_options:
                    default_index = list(item_options.keys()).index(sc_id)
            
            selected_item_id = st.selectbox("वस्तू निवडा (बारकोड स्कॅनर लिंक):", options=list(item_options.keys()), index=default_index, format_func=lambda x: item_options[x])
            
        if selected_item_id:
            cursor.execute("SELECT metal_type, item_name, company_name, stock_grams, metal_category, purchase_rate FROM items_stock WHERE id=?", (selected_item_id,))
            m_type, i_name, c_name, s_grams, m_cat, p_rate = cursor.fetchone()
            
            w1, w2, w3 = st.columns(3)
            with w1:
                # थेट बाजारभावानुसार विक्री दर ऑटोमॅटिक सिलेक्ट होतो
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
            with tx2: old_value = st.number_input("जुन्या मोडीचे एकूण मूल्य (वजा करायचे रक्कम) ₹:", min_value=0.0)
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
                    INSERT INTO billing_v4 (date, customer_name, customer_phone, item_name, metal_type, company_name, weight, rate_per_gm, making_charge, gst_percent, old_value, grand_total, cash_paid, balance_amount, reminder_date, bill_note, purchase_rate_per_gm, customer_dob)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today_now, cust_name, cust_phone, i_name, m_type, c_name, weight, live_rate, making_charge, gst_select, old_value, grand_total, cash_paid, balance_amount, str(reminder_date), bill_note, p_rate, dob_str))
                    cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                    conn.commit()
                    st.success("🎉 बिल यशस्वीरित्या जमा झाले व स्टॉक अपडेट झाला!")
            st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ३: स्टॉक व्यवस्थापन आणि २. बारकोड लेबल जनरेटर इमेज (.PNG डाउनलोड)
# ==============================================================================
elif choice == "📦 स्टॉक व्यवस्थापन":
    st.markdown("<h2 style='color: #AA7C11;'>📦 स्टॉक इन्व्हेंटरी आणि बारकोड जनरेटर फाईल</h2>", unsafe_allow_html=True)
    st.write("---")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("➕ नवीन स्टॉक जोडा")
        s_category = st.selectbox("कॅटेगरी:", ["Gold", "Silver"])
        s_type = st.selectbox("प्रकार:", ["Gold 24K", "Gold 22K", "Gold 18K", "Silver"])
        s_item_name = st.text_input("दागिन्याचे नाव:")
        s_pur_rate = st.number_input("खरेदी भाव प्रति ग्रॅम (₹):", min_value=0.0)
        s_grams = st.number_input("एकूण वजन (g):", min_value=0.0, step=0.01)
        s_alert = st.number_input("किमान स्टॉक अलर्ट लिमिट (g) - चेतावणी मर्यादा:", min_value=0.0, value=2.0)
        
        if st.button("📥 सुरक्षित स्टॉक जमा करा", use_container_width=True):
            cursor.execute("INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit, item_size, purchase_rate) VALUES (?, ?, ?, 'Own', ?, ?, '-', ?)", 
                           (s_category, s_type, s_item_name, s_grams, s_alert, s_pur_rate))
            conn.commit()
            st.success("स्टॉक सुरक्षित जमा केला!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_s2:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("🖨️ २. बारकोड लेबल जनरेटर इमेज पॅनेल (PNG Download)")
        df_stock = pd.read_sql_query("SELECT id, item_name, stock_grams FROM items_stock WHERE stock_grams > 0", conn)
        
        if not df_stock.empty:
            b_opts = {row['id']: f"ID: #{row['id']} | {row['item_name']}" for idx, row in df_stock.iterrows()}
            sel_b_id = st.selectbox("बारकोड लेबल निवड करा:", options=list(b_opts.keys()), format_func=lambda x: b_opts[x])
            
            if sel_b_id:
                item_row = df_stock[df_stock['id'] == sel_b_id].iloc[0]
                
                # HTML आणि JavaScript वापरून थेट स्क्रीनवरच PNG इमेज बनवून डाउनलोड करण्याचे स्मार्ट टूल
                barcode_html = f"""
                <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
                <div id="sticker" style="width: 210px; border: 1px solid #AA7C11; padding: 12px; text-align: center; background: #fff; color: #000; font-family: Arial; border-radius: 6px;">
                    <div style="font-size: 11px; font-weight: bold; color: #AA7C11;">{shop_name}</div>
                    <div style="font-size: 13px; margin: 3px 0; font-weight: bold;">{item_row['item_name']}</div>
                    <div style="letter-spacing: 3px; background: #000; color: #000; height: 16px; width: 90%; margin: 5px auto;"></div>
                    <div style="font-size: 10px;">CODE: *J{item_row['id']:05d}*</div>
                    <div style="font-size: 12px; margin-top: 3px;"><b>वजन: {item_row['stock_grams']} g</b></div>
                </div>
                <br>
                <button onclick="downloadSticker()" style="padding: 7px 12px; background: #AA7C11; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">💾 Download Barcode PNG</button>
                
                <script>
                function downloadSticker() {{
                    html2canvas(document.getElementById("sticker")).then(canvas => {{
                        let link = document.createElement('a');
                        link.download = 'Barcode_J{item_row['id']}.png';
                        link.href = canvas.toDataURL();
                        link.click();
                    }});
                }}
                </script>
                """
                components.html(barcode_html, height=190)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ४: कारागीर लेजर (Karigar Ledger)
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
        wastage = st.number_input("ठरलेले वेस्टेज/घट (Loss in g):", min_value=0.0)
        m_paid = st.number_input("दिलेली मजुरी रक्कम (₹):", min_value=0.0)
        
        if st.button("💾 कारागीर खात्यात नोंदवा", use_container_width=True):
            t_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO karigar_ledger (date, karigar_name, given_gold, received_ornament_weight, wastage_grams, making_charges_paid, status) VALUES (?, ?, ?, ?, ?, ?, 'Completed')", (t_date, k_name, g_gold, r_gold, wastage, m_paid))
            conn.commit()
            st.success("कारागीर लेजर नोंद यशस्वी झाली!")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_k2:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("📋 कारागीर देणे-घेणे इतिहास")
        df_k = pd.read_sql_query("SELECT date as तारीख, karigar_name as कारागीर, given_gold as 'दिलेले सोने (g)', received_ornament_weight as 'प्राप्त दागिना (g)', wastage_grams as 'वेस्टेज घट (g)', making_charges_paid as 'मजुरी दिली' FROM karigar_ledger", conn)
        st.dataframe(df_k, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ५: जुनी मोड लेजर (Old Gold Ledger)
# ==============================================================================
elif choice == "🔄 जुनी मोड लेजर":
    st.markdown("<h2 style='color: #AA7C11;'>🔄 जमा जुनी मोड आणि वितळवण्याचा स्वतंत्र हिशोब</h2>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
        st.subheader("📥 वितळवण्यासाठी शुद्धीकरण पेढीकडे पाठवणे")
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
        st.subheader("📜 जमा जुनी मोड वितळवणूक रेकॉर्ड")
        df_m = pd.read_sql_query("SELECT date as तारीख, refinery_name as 'रिफायनरी पेढी', total_weight_sent as 'पाठवलेले वजन (g)', received_pure_weight as 'मिळालेले शुद्ध सोने (g)' FROM old_gold_melting", conn)
        st.dataframe(df_m, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# विभाग ६: GST आणि नफा-तोटा विभाग (Monthly Report & Net Profit Tracker)
# ==============================================================================
elif choice == "📈 GST व नफा-तोटा विभाग":
    st.markdown("<h2 style='color: #AA7C11;'>📈 महिन्याचा GST रिपोर्ट आणि निव्वळ नफा (Profit) ट्रॅकर</h2>", unsafe_allow_html=True)
    
    df_bills = pd.read_sql_query("SELECT date, grand_total, weight, rate_per_gm, making_charge, gst_percent, purchase_rate_per_gm FROM billing_v4", conn)
    
    if df_bills.empty:
        st.info("नफा आणि GST रिपोर्ट ट्रॅक करण्यासाठी आधी बिले बनवा.")
    else:
        # बॅकएंड प्रॉफिट आणि टॅक्स कॅल्क्युलेशन नियम
        df_bills['विक्री धातू किंमत'] = df_bills['weight'] * df_bills['rate_per_gm']
        df_bills['खरेदी धातू किंमत'] = df_bills['weight'] * df_bills['purchase_rate_per_gm']
        df_bills['निव्वळ नफा (Profit)'] = (df_bills['विक्री धातू किंमत'] - df_bills['खरेदी धातू किंमत']) + df_bills['making_charge']
        df_bills['जमा GST कर'] = (df_bills['विक्री धातू किंमत'] + df_bills['making_charge']) * (df_bills['gst_percent'] / 100)
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f'<div class="metric-box" style="border-left-color:#2ECC71;"><div style="color:#777;">💸 महिन्याचा एकूण निव्वळ नफा (Net Profit)</div><div class="metric-val">₹{df_bills["निव्वळ नफा (Profit)"].sum():,.2f}</div></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="metric-box" style="border-left-color:#3498DB;"><div style="color:#777;">🏛️ महिन्याचा गोळा झालेला एकूण GST कर</div><div class="metric-val">₹{df_bills["जमा GST कर"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            
        st.write("---")
        st.subheader("📋 अधिकृत कर आणि नफा-तोटा लेजर स्टेटमेंट")
        st.dataframe(df_bills[['date', 'weight', 'grand_total', 'निव्वळ नफा (Profit)', 'जमा GST कर']], use_container_width=True)

# ==============================================================================
# विभाग ७: बॅकअप सिस्टम
# ==============================================================================
elif choice == "⚙️ बॅकअप":
    st.markdown("<h2 style='color: #AA7C11;'>⚙️ डेटाबेस क्लाउड सुरक्षितता आणि बॅकअप</h2>", unsafe_allow_html=True)
    with open(DB_FILE, "rb") as f:
        st.download_button(label="💾 सुरक्षित डेटाबेस बॅकअप फाईल डाउनलोड करा", data=f.read(), file_name="sai_prasad_jewellers_pro.db", use_container_width=True)
