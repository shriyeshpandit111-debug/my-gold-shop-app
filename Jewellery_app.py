import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime

# १. डेटाबेस सेटअप
conn = sqlite3.connect("jewellery_erp_fixed.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS billing_v3 (
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
    old_value REAL,
    grand_total REAL,
    cash_paid REAL,
    balance_amount REAL,
    reminder_date TEXT,
    bill_note TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS items_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metal_type TEXT,
    item_name TEXT,
    company_name TEXT,
    stock_grams REAL,
    alert_limit REAL
)
""")
conn.commit()

# प्राथमिक डिझाईन सेटअप
st.set_page_config(page_title="Jewellery ERP Master", page_icon="👑", layout="wide")

# २. साइडबार - मास्टर सेटिंग्ज
st.sidebar.header("🏪 मास्टर सेटिंग्ज / Master Settings")
shop_name = st.sidebar.text_input("दुकानाचे नाव (Shop Name):", value="श्री गणेश ज्वेलर्स")
shop_address = st.sidebar.text_area("दुकानाचा पत्ता (Address):", value="मेन रोड, बाजार पेठ, महाराष्ट्र.")
gst_number = st.sidebar.text_input("GSTIN (GST नंबर):", value="27AAAAA0000A1Z1")
show_hallmark_logo = st.sidebar.checkbox("बिलावर Hallmark लोगो दाखवा? (Show Hallmark Logo)", value=True)
show_shop_logo = st.sidebar.checkbox("बिलावर दुकानाचा लोगो दाखवा? (Show Shop Logo)", value=True)

st.sidebar.header("💰 आजचे बाजार भाव / Daily Rates (प्रति ग्रॅम)")
gold_24k_rate = st.sidebar.number_input("24K सोने दर (24K Gold Rate):", value=7500.0)
gold_22k_rate = st.sidebar.number_input("22K सोने दर (22K Gold Rate):", value=6875.0)
gold_18k_rate = st.sidebar.number_input("18K सोने दर (18K Gold Rate):", value=5625.0)
silver_rate = st.sidebar.number_input("चांदी दर (Silver Rate):", value=90.0)

# मुख्य मेनू नेव्हिगेशन
menu = ["🧾 नवीन बिल काउंटर / New Bill", "📦 स्टॉक मॅनेजमेंट / Stock Management", "📊 ग्राहक उधारी व इतिहास / Customer Ledger"]
choice = st.radio("मुख्य मेनू निवडा / Select Menu:", menu, horizontal=True)

# ----------------- विभाग १: प्रगत थर्मल बिल काउंटर -----------------
if choice == "🧾 नवीन बिल काउंटर / New Bill":
    st.title("🧾 Standard 80mm Thermal Billing Counter (मराठी / English)")
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 ग्राहकाची माहिती / Customer Info")
        cust_name = st.text_input("ग्राहकाचे नाव (Customer Name) [मराठी/Eng]:")
        cust_phone = st.text_input("मोबाईल नंबर (WhatsApp No):")
        bill_note = st.text_input("बिलाच्या खालील टीप (Terms & Notes):", value="नियम: घडणावळ परत मिळणार नाही. हॉलमार्क गॅरंटी.")
        
    with col2:
        st.subheader("🛍️ दागिन्याची निवड / Select Jewellery")
        df_avail = pd.read_sql_query("SELECT id, metal_type, item_name, company_name, stock_grams FROM items_stock WHERE stock_grams > 0", conn)
        
        if df_avail.empty:
            st.warning("⚠️ स्टॉकमध्ये एकही दागिना उपलब्ध नाही! कृपया आधी स्टॉक मॅनेजमेंटमध्ये आयटम जोडा.")
            selected_item_id = None
        else:
            item_options = {row['id']: f"{row['item_name']} - {row['metal_type']} ({row['company_name']}) [Stock: {row['stock_grams']}g]" for idx, row in df_avail.iterrows()}
            selected_item_id = st.selectbox("दागिना निवडा (Select Item):", options=list(item_options.keys()), format_func=lambda x: item_options[x])

    if selected_item_id:
        cursor.execute("SELECT metal_type, item_name, company_name, stock_grams FROM items_stock WHERE id=?", (selected_item_id,))
        item_details = cursor.fetchone()
        m_type, i_name, c_name, s_grams = item_details[0], item_details[1], item_details[2], item_details[3]
        
        st.write("---")
        st.subheader("🧮 हिशोब काउंटर / Calculations")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            default_rate = gold_22k_rate if m_type == "Gold 22K" else (gold_24k_rate if m_type == "Gold 24K" else (gold_18k_rate if m_type == "Gold 18K" else silver_rate))
            live_rate = st.number_input("धातूचा आजचा दर / Rate per gm:", value=default_rate)
            weight = st.number_input(f"वजन ग्रॅममध्ये / Weight (Max: {s_grams}g):", min_value=0.0, max_value=s_grams, step=0.01)
            making_charge = st.number_input("मजुरी / Labour Charge (Manual Total Amount):", min_value=0.0)
            
        with col4:
            gst_select = st.selectbox("GST टक्केवारी / GST %:", [3.0, 0.0, 1.0])
            old_gold_allow = st.checkbox("जुनी मोड वजा करायची का? (Old Gold Exchange)")
            old_value = st.number_input("जुन्या मोडीची किंमत / Old Gold Value (₹):", min_value=0.0) if old_gold_allow else 0.0
            
        with col5:
            metal_total = weight * live_rate
            subtotal = metal_total + making_charge
            gst_amt = subtotal * (gst_select / 100)
            grand_total = subtotal + gst_amt
            
            st.metric("दागिन्याची एकूण किंमत (Grand Total)", f"₹{grand_total:,.2f}")
            
            cash_paid = st.number_input("जма रोकड (Cash/Advance Paid):", min_value=0.0, max_value=grand_total)
            balance_amount = grand_total - old_value - cash_paid
            st.metric("शिल्लक उधारी (Remaining Balance)", f"₹{balance_amount:,.2f}")
            
            reminder_date = st.date_input("उधारी वायदा तारीख (Reminder Date):") if balance_amount > 0 else datetime.today().date()

        if st.button("💾 बिल सेव्ह आणि प्रिंट करा (Save & Print)"):
            if cust_name == "" or cust_phone == "":
                st.error("❌ ग्राहकाचे नाव आणि मोबाईल नंबर भरणे अनिवार्य आहे!")
            else:
                today_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                INSERT INTO billing_v3 (date, customer_name, customer_phone, item_name, metal_type, company_name, weight, rate_per_gm, making_charge, gst_percent, old_value, grand_total, cash_paid, balance_amount, reminder_date, bill_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (today_now, cust_name, cust_phone, i_name, m_type, c_name, weight, live_rate, making_charge, gst_select, old_value, grand_total, cash_paid, balance_amount, str(reminder_date), bill_note))
                
                cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                conn.commit()
                st.success("✅ बिल यशस्वीरित्या सेव्ह झाले!")
                
                # ---- 80mm Thermal Print Format ----
                st.write("---")
                st.subheader("📟 Print Preview (Ctrl+P दाबून प्रिंट करा)")
                
                logo_str = "👑<br>" if show_shop_logo else ""
                hallmark_str = "<br>[ BIS 916 HALLMARK ]" if show_hallmark_logo else ""
                
                # जुन्या मोडीची लाईन ठरवणे
                old_gold_tr = f"<tr><td>जुनी मोड वजा (Old Gold):</td><td style='text-align: right;'>- ₹{old_value:.2f}</td></tr>" if old_value > 0 else ""
                # वायदा तारीख लाईन ठरवणे
                due_date_div = f"<div style='font-weight: bold;'>वायदा तारीख / Due Date: {reminder_date}</div><div style='border-top: 1px dashed #000; margin: 5px 0;'></div>" if balance_amount > 0 else ""

  bill_html = f"""
                <div style="width: 300px; font-family: 'Courier New', Courier, monospace; font-size: 12px; border: 1px solid #ccc; padding: 10px; background: #fff; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold; font-size:16px;">{logo_str}{shop_name}</div>
                    <div style="text-align: center;">{shop_address}</div>
                    <div style="text-align: center; font-weight: bold;">GSTIN: {gst_number}</div>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <div><b>तारीख / Date:</b> {today_now}</div>
                    <div><b>ग्राहक / Name:</b> {cust_name}</div>
                    <div><b>मोबाईल / Mob:</b> {cust_phone}</div>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <div style="font-weight: bold;">तपशील (Item Details):</div>
                    <div>{i_name} ({m_type})</div>
                    <div>कंपनी / Brand: {c_name}</div>
                    <div>वजन / Weight: {weight}g | दर / Rate: ₹{live_rate}</div>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <table style="width:100%;">
                        <tr><td>धातू मूल्य (Metal Price):</td><td style="text-align: right;">₹{metal_total:.2f}</td></tr>
                        <tr><td>मजुरी (Labour):</td><td style="text-align: right;">₹{making_charge:.2f}</td></tr>
                        <tr><td>GST ({gst_select}%):</td><td style="text-align: right;">₹{gst_amt:.2f}</td></tr>
                        <tr style="font-weight: bold;"><td>एकूण बिल (Total):</td><td style="text-align: right;">₹{grand_total:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td>जमा रोकड (Paid):</td><td style="text-align: right;">₹{cash_paid:.2f}</td></tr>
                        <tr style="font-weight: bold; font-size:13px;"><td>बाकी उधारी (Balance):</td><td style="text-align: right;">₹{balance_amount:.2f}</td></tr>
                    </table>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    {due_date_div}
                    <div style="text-align: center; font-style: italic;">{bill_note}{hallmark_str}</div>
                    <br><br>
                </div>
"""
