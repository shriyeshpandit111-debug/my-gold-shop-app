import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse  # व्हॉट्सॲप लिंकसाठी टेक्स्ट एन्कोड करायला
from datetime import datetime

# ==============================================================================
# १. डेटाबेस सेटअप (Database Setup)
# ==============================================================================
conn = sqlite3.connect("jewellery_erp_fixed.db", check_same_thread=False)
cursor = conn.cursor()

# बिलांचे टेबल
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

# स्टॉकचे टेबल
cursor.execute("""
CREATE TABLE IF NOT EXISTS items_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metal_category TEXT,
    metal_type TEXT,
    item_name TEXT,
    company_name TEXT,
    stock_grams REAL,
    alert_limit REAL
)
""")
conn.commit()

# ==============================================================================
# २. प्राथमिक डिझाईन आणि साइडबार (UI Design & Sidebar)
# ==============================================================================
st.set_page_config(page_title="Jewellery ERP Master", page_icon="👑", layout="wide")

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

# ==============================================================================
# विभाग १: प्रगत थर्मल बिल काउंटर (Billing Counter)
# ==============================================================================
if choice == "🧾 नवीन बिल काउंटर / New Bill":
    st.title("🧾 Standard 80mm Thermal Billing Counter")
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 ग्राहकाची माहिती / Customer Info")
        cust_name = st.text_input("ग्राहकाचे नाव (Customer Name) [मराठी/Eng]:")
        cust_phone = st.text_input("मोबाईल नंबर (WhatsApp No) [उदा. 98XXXXXXXX]:")
        bill_note = st.text_input("बिलाच्या खालील टीप (Terms & Notes):", value="नियम: घडणावळ परत मिळणार नाही. हॉलमार्क गॅरंटी.")
        
    with col2:
        st.subheader("🛍️ दागिन्याची निवड / Select Jewellery")
        filter_category = st.selectbox("कॅटेगरी निवडा (Filter Category):", ["सर्व (All)", "Gold", "Silver"])
        
        if filter_category == "सर्व (All)":
            query = "SELECT id, metal_category, metal_type, item_name, company_name, stock_grams FROM items_stock WHERE stock_grams > 0"
            df_avail = pd.read_sql_query(query, conn)
        else:
            query = "SELECT id, metal_category, metal_type, item_name, company_name, stock_grams FROM items_stock WHERE stock_grams > 0 AND metal_category = ?"
            df_avail = pd.read_sql_query(query, conn, params=(filter_category,))
        
        if df_avail.empty:
            st.warning(f"⚠️ {filter_category} कॅटेगरीमध्ये एकही दागिना उपलब्ध नाही! कृपया आधी स्टॉक जोडा.")
            selected_item_id = None
        else:
            item_options = {row['id']: f"[{row['metal_category']}] {row['item_name']} - {row['metal_type']} ({row['company_name']}) [Stock: {row['stock_grams']}g]" for idx, row in df_avail.iterrows()}
            selected_item_id = st.selectbox("दागिना निवडा (Select Item):", options=list(item_options.keys()), format_func=lambda x: item_options[x])

    if selected_item_id:
        cursor.execute("SELECT metal_type, item_name, company_name, stock_grams, metal_category FROM items_stock WHERE id=?", (selected_item_id,))
        item_details = cursor.fetchone()
        m_type, i_name, c_name, s_grams, m_cat = item_details[0], item_details[1], item_details[2], item_details[3], item_details[4]
        
        st.write("---")
        st.subheader("🧮 हिशोब काउंटर / Calculations")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            if m_cat == "Silver":
                default_rate = silver_rate
            else:
                default_rate = gold_22k_rate if m_type == "Gold 22K" else (gold_24k_rate if m_type == "Gold 24K" else gold_18k_rate)
                
            live_rate = st.number_input("धातूचा आजचा दर / Rate per gm:", value=default_rate)
            weight = st.number_input(f"वजन ग्रॅममध्ये / Weight (Max: {s_grams}g):", min_value=0.0, max_value=s_grams, step=0.01)
            making_charge = st.number_input("मजुरी / Labour Charge (Manual Total Amount):", min_value=0.0)
            
        with col4:
            gst_select = st.selectbox("GST टक्केवारी / GST %:", [3.0, 0.0, 1.0])
            old_gold_allow = st.checkbox("जुनी मोड वजा करायची का? (Old Gold Exchange)")
            old_value = st.number_input("जुन्या मोडीची किंमत / Old Value (₹):", min_value=0.0) if old_gold_allow else 0.0
            
        with col5:
            metal_total = weight * live_rate
            subtotal = metal_total + making_charge
            gst_amt = subtotal * (gst_select / 100)
            grand_total = subtotal + gst_amt
            
            st.metric("दागिन्याची एकूण किंमत (Grand Total)", f"₹{grand_total:,.2f}")
            
            cash_paid = st.number_input("जमा रोकड (Cash/Advance Paid):", min_value=0.0, max_value=grand_total)
            balance_amount = grand_total - old_value - cash_paid
            st.metric("शिल्लक उधारी (Remaining Balance)", f"₹{balance_amount:,.2f}")
            
            reminder_date = st.date_input("उधारी वायदा तारीख (Reminder Date):") if balance_amount > 0 else datetime.today().date()

        # बिल सेव्ह करण्यासाठी बटन
        if st.button("💾 बिल सेव्ह आणि प्रिंट करा (Save & Print)"):
            if cust_name == "" or cust_phone == "":
                st.error("❌ ग्राहकाचे नाव आणि मोबाईल नंबर भरणे अनिवार्य आहे!")
            elif weight <= 0:
                st.error("❌ कृपया दागिन्याचे वजन ० पेक्षा जास्त टाका!")
            else:
                today_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # बिलाची नोंद करणे
                cursor.execute("""
                INSERT INTO billing_v3 (date, customer_name, customer_phone, item_name, metal_type, company_name, weight, rate_per_gm, making_charge, gst_percent, old_value, grand_total, cash_paid, balance_amount, reminder_date, bill_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (today_now, cust_name, cust_phone, i_name, f"{m_cat} ({m_type})", c_name, weight, live_rate, making_charge, gst_select, old_value, grand_total, cash_paid, balance_amount, str(reminder_date), bill_note))
                
                # स्टॉकमधून वजन वजा करणे
                cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                conn.commit()
                st.success("✅ बिल यशस्वीरित्या सेव्ह झाले आणि स्टॉक अपडेट झाला!")
                
                # ---- व्हॉट्सॲप मेसेज मजकूर तयार करणे ----
                # \n म्हणजे नवीन ओळ (New Line)
                wp_text = (
                    f"*✨ {shop_name} ✨*\n"
                    f"पत्ता: {shop_address}\n"
                    f"-------------------------\n"
                    f"प्रिय *{cust_name}*, आपले बिल खालीलप्रमाणे आहे:\n"
                    f"🗓️ तारीख: {today_now}\n"
                    f"🛍️ दागिना: {i_name} ({m_cat} - {m_type})\n"
                    f"⚖️ वजन: {weight}g | दर: ₹{live_rate}/g\n"
                    f"💰 एकूण बिल: *₹{grand_total:,.2f}*\n"
                    f"💵 जमा रोकड: ₹{cash_paid:,.2f}\n"
                    f"🔴 बाकी उधारी: *₹{balance_amount:,.2f}*\n"
                    f"-------------------------\n"
                    f"🙏 आमच्या दुकानाला भेट दिल्याबद्दल धन्यवाद!"
                )
                
                # मजकूर इंटरनेट लिंक फॉरमॅटमध्ये रूपांतरित करणे
                encoded_text = urllib.parse.quote(wp_text)
                
                # भारताचा कोड (+91) मोबाईल नंबरला जोडणे
                clean_phone = cust_phone.strip().replace("+", "").replace(" ", "")
                if len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone
                
                whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_text}"
                
                # स्क्रीनवर व्हॉट्सॲपचे बटन दाखवणे
                st.markdown(f"""
                    <a href="{whatsapp_url}" target="_blank">
                        <button style="background-color: #25D366; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 5px; cursor: pointer; width: 100%; margin-bottom: 20px;">
                            📲 ग्राहकाला WhatsApp वर बिल पाठवा (Send to WhatsApp)
                        </button>
                    </a>
                """, unsafe_allow_html=True)
                
                # ---- 80mm Thermal Print Format ----
                st.write("---")
                st.subheader("📟 Print Preview")
                
                logo_str = "👑<br>" if show_shop_logo else ""
                hallmark_str = "<br>[ BIS 916 HALLMARK ]" if show_hallmark_logo else ""
                old_gold_tr = f"<tr><td>जुनी मोड वजा (Old Gold):</td><td style='text-align: right;'>- ₹{old_value:.2f}</td></tr>" if old_value > 0 else ""
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
                    <div>{i_name} ({m_cat} - {m_type})</div>
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
                </div>
                """
                st.markdown(bill_html, unsafe_allow_html=True)

# ==============================================================================
# विभाग २: कॅटेगरी वाईज स्टॉक मॅनेजमेंट (Category-wise Stock)
# ==============================================================================
elif choice == "📦 स्टॉक मॅनेजमेंट / Stock Management":
    st.title("📦 कॅटेगरी वाईज स्टॉक मॅनेजमेंट / Category-wise Stock")
    st.write("---")
    
    tab1, tab2 = st.tabs(["➕ नवीन स्टॉक जोडा (Add Stock)", "📋 सध्याचा स्टॉक पहा (View Stock)"])
    
    with tab1:
        st.subheader("🆕 नवीन मालाची एंट्री")
        with st.form("stock_form", clear_on_submit=True):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                m_category_input = st.selectbox("मुख्य कॅटेगरी (Category):", ["Gold", "Silver"])
                m_type_input = st.selectbox("प्रकार/टच (Type/Purity):", ["22K", "24K", "18K", "92.5 Sterling", "Fine Silver", "Regular Silver"])
                i_name_input = st.text_input("दागिन्याचे नाव (Item Name) [उदा. अंगठी, पैंजण, चैन]:")
                
            with col_s2:
                c_name_input = st.text_input("कंपनी/ब्रँडचे नाव (Company/Brand Name):", value="Own Stock")
                stock_grams_input = st.number_input("एकूण वजन ग्रॅममध्ये (Weight in Grams):", min_value=0.0, step=0.01)
                alert_limit_input = st.number_input("किमान स्टॉक अलर्ट मर्यादा (Alert Limit Grams):", min_value=0.0, value=5.0, step=0.01)
            
            submit_stock = st.form_submit_button("💾 स्टॉक जतन करा (Save Stock)")
            
            if submit_stock:
                if i_name_input == "" or stock_grams_input <= 0:
                    st.error("❌ कृपया दागिन्याचे नाव आणि अचूक वजन टाका!")
                else:
                    cursor.execute("""
                    INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (m_category_input, m_type_input, i_name_input, c_name_input, stock_grams_input, alert_limit_input))
                    conn.commit()
                    st.success(f"✅ [{m_category_input}] {i_name_input} स्टॉकमध्ये यशस्वीरित्या जोडला गेला!")
                    st.rerun()

    with tab2:
        st.subheader("📋 उपलब्ध सर्व स्टॉक")
        view_cat = st.radio("कोणता स्टॉक पाहायचा आहे?", ["सर्व (All)", "फक्त सोने (Gold Stock Only)", "फक्त चांदी (Silver Stock Only)"], horizontal=True)
        
        if view_cat == "फक्त सोने (Gold Stock Only)":
            q_stock = "SELECT id AS 'ID', metal_category AS 'कॅटेगरी', metal_type AS 'प्रकार', item_name AS 'दागिना', company_name AS 'कंपनी', stock_grams AS 'वजन (ग्रॅम)', alert_limit AS 'अलर्ट लिमिट' FROM items_stock WHERE metal_category = 'Gold'"
        elif view_cat == "फक्त चांदी (Silver Stock Only)":
            q_stock = "SELECT id AS 'ID', metal_category AS 'कॅटेगरी', metal_type AS 'प्रकार', item_name AS 'दागिना', company_name AS 'कंपनी', stock_grams AS 'वजन (ग्रॅम)', alert_limit AS 'अलर्ट लिमिट' FROM items_stock WHERE metal_category = 'Silver'"
        else:
            q_stock = "SELECT id AS 'ID', metal_category AS 'कॅटेगरी', metal_type AS 'प्रकार', item_name AS 'दागिना', company_name AS 'कंपनी', stock_grams AS 'वजन (ग्रॅम)', alert_limit AS 'अलर्ट लिमिट' FROM items_stock"
            
        df_stock = pd.read_sql_query(q_stock, conn)
        
        if df_stock.empty:
            st.info("ℹ️ निवडलेल्या कॅटेगरीमध्ये सध्या कोणताही स्टॉक उपलब्ध नाही.")
        else:
            st.dataframe(df_stock, use_container_width=True)
            
            cursor.execute("SELECT SUM(stock_grams) FROM items_stock WHERE metal_category = 'Gold'")
            total_gold_w = cursor.fetchone()[0] or 0.0
            cursor.execute("SELECT SUM(stock_grams) FROM items_stock WHERE metal_category = 'Silver'")
            total_silver_w = cursor.fetchone()[0] or 0.0
            
            st.write("---")
            sc1, sc2 = st.columns(2)
            sc1.info(f"✨ **एकूण सोन्याचा स्टॉक (Total Gold):** {total_gold_w:.3f} ग्रॅम")
            sc2.info(f"✨ **एकूण चांदीचा स्टॉक (Total Silver):** {total_silver_w:.3f} ग्रॅम")

# ==============================================================================
# विभाग ३: ग्राहक उधारी व इतिहास (Customer Ledger)
# ==============================================================================
elif choice == "📊 ग्राहक उधारी व इतिहास / Customer Ledger":
    st.title("📊 ग्राहक उधारी व इतिहास / Customer Ledger")
    st.write("---")
    
    df_ledger = pd.read_sql_query("""
        SELECT id AS 'बिल ID', date AS 'तारीख', customer_name AS 'ग्राहक', customer_phone AS 'मोबाईल', 
               item_name AS 'दागिना', grand_total AS 'एकूण बिल (₹)', cash_paid AS 'जमा रोकड (₹)', 
               balance_amount AS 'बाकी उधारी (₹)', reminder_date AS 'वायदा तारीख' 
        FROM billing_v3 
        ORDER BY id DESC
    """, conn)
    
    if df_ledger.empty:
        st.info("ℹ️ डेटाबेसमध्ये अजून एकही बिल किंवा उधारीची नोंद नाही.")
    else:
        total_business = df_ledger['एकूण बिल (₹)'].sum()
        total_collected = df_ledger['जमा रोकड (₹)'].sum()
        total_pending = df_ledger['बाकी उधारी (₹)'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📊 एकूण विक्री (Total Sales)", f"₹{total_business:,.2f}")
        m2.metric("🟢 एकूण जमा रोकड (Total Received)", f"₹{total_collected:,.2f}")
        m3.metric("🔴 एकूण脫ारकी उधारी (Total Outstanding)", f"₹{total_pending:,.2f}", delta_color="inverse")
        
        st.write("---")
        
        st.subheader("💵 उधारीची रक्कम जमा करा (Receive Pending Payment)")
        df_debtors = pd.read_sql_query("SELECT id, customer_name, balance_amount FROM billing_v3 WHERE balance_amount > 0", conn)
        
        if df_debtors.empty:
            st.success("🎉 सर्व ग्राहकांची उधारी पूर्ण जमा आहे! कोणतीही उधारी बाकी नाही.")
        else:
            debtor_options = {row['id']: f"बिल ID: {row['id']} | {row['customer_name']} (बाकी: ₹{row['balance_amount']:.2f})" for idx, row in df_debtors.iterrows()}
            
            with st.form("payment_receive_form"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    selected_bill_id = st.selectbox("ग्राहक आणि बिल निवडा:", options=list(debtor_options.keys()), format_func=lambda x: debtor_options[x])
                with col_p2:
                    amount_to_pay = st.number_input("आता जमा करायची रक्कम (₹):", min_value=0.0, step=100.0)
                
                submit_payment = st.form_submit_button("✅ रक्कम जमा करा (Update Payment)")
                
                if submit_payment:
                    cursor.execute("SELECT customer_name, cash_paid, balance_amount FROM billing_v3 WHERE id=?", (selected_bill_id,))
                    current_bill = cursor.fetchone()
                    c_cust, c_paid, c_bal = current_bill[0], current_bill[1], current_bill[2]
                    
                    if amount_to_pay <= 0:
                        st.error("❌ कृपया ० पेक्षा जास्त रक्कम टाका!")
                    elif amount_to_pay > c_bal:
                        st.error(f"❌ रक्कम बाकी उधारीपेक्षा (₹{c_bal:.2f}) जास्त असू शकत नाही!")
                    else:
                        new_paid = c_paid + amount_to_pay
                        new_bal = c_bal - amount_to_pay
                        
                        cursor.execute("UPDATE billing_v3 SET cash_paid=?, balance_amount=? WHERE id=?", (new_paid, new_bal, selected_bill_id))
                        conn.commit()
                        st.success(f"✅ {c_cust} यांचे ₹{amount_to_pay:.2f} जमा झाले. नवीन बाकी: ₹{new_bal:.2f}")
                        st.rerun()

        st.write("---")
        
        st.subheader("📋 सर्व बिलांचा आणि उधारीचा इतिहास")
        search_query = st.text_input("🔍 ग्राहक किंवा मोबाईल नंबरवरून शोधा (Search by Name/Phone):")
        if search_query:
            filtered_df = df_ledger[
                df_ledger['ग्राहक'].str.contains(search_query, case=False, na=False) | 
                df_ledger['मोबाईल'].str.contains(search_query, case=False, na=False)
            ]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df_ledger, use_container_width=True)
