import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime

# ==============================================================================
# १. डेटाベース सेटअप (Database Setup)
# ==============================================================================
conn = sqlite3.connect("jewellery_erp_fixed.db", check_same_thread=False)
cursor = conn.cursor()

# नवीन सुधारित टेबल स्ट्रक्चर (V4)
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
    bill_note TEXT
)
""")

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

# पुराना डेटाबेस सिंक करण्यासाठी पॅच
try:
    cursor.execute("ALTER TABLE billing_v4 ADD COLUMN old_gold_type TEXT")
    cursor.execute("ALTER TABLE billing_v4 ADD COLUMN old_gold_item TEXT")
    conn.commit()
except:
    pass

# ==============================================================================
# २. प्राथमिक डिझाईन आणि साइडबार (UI Design & Sidebar)
# ==============================================================================
st.set_page_config(page_title="Jewellery ERP Master", page_icon="👑", layout="wide")

st.sidebar.header("🏪 मास्टर सेटिंग्ज / Master Settings")
shop_name = st.sidebar.text_input("दुकानाचे नाव (Shop Name):", value="श्री गणेश ज्वेलर्स")
shop_address = st.sidebar.text_area("दुकानाचा पत्ता (Address):", value="मेन रोड, बाजार पेठ, Sangola.")
gst_number = st.sidebar.text_input("GSTIN (GST नंबर):", value="27AAAAA0000A1Z1")
show_hallmark_logo = st.sidebar.checkbox("बिलावर Hallmark लोगो दाखवा?", value=True)
show_shop_logo = st.sidebar.checkbox("बिलावर दुकानाचा लोगो दाखवा?", value=True)

st.sidebar.header("💰 आजचे बाजार भाव / Daily Rates")
gold_24k_rate = st.sidebar.number_input("24K सोने दर (प्रति ग्रॅम):", value=7500.0)
gold_22k_rate = st.sidebar.number_input("22K सोने दर (प्रति ग्रॅम):", value=6875.0)
gold_18k_rate = st.sidebar.number_input("18K सोने दर (प्रति ग्रॅम):", value=5625.0)
silver_rate = st.sidebar.number_input("चांदी दर (प्रति ग्रॅम):", value=90.0)

menu = ["🧾 नवीन बिल काउंटर / New Bill", "📦 स्टॉक मॅनेजमेंट / Stock Management", "📊 ग्राहक उधारी व इतिहास / Customer Ledger"]
choice = st.radio("मुख्य मेनू निवडा / Select Menu:", menu, horizontal=True)

if "last_bill" not in st.session_state:
    st.session_state.last_bill = None

# ==============================================================================
# विभाग १: प्रगत बिल काउंटर (Billing Counter)
# ==============================================================================
if choice == "🧾 नवीन बिल काउंटर / New Bill":
    st.title("🧾 Advanced Jewellery Billing Counter")
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 ग्राहकाची माहिती / Customer Info")
        cust_name = st.text_input("ग्राहकाचे नाव (Customer Name):")
        cust_phone = st.text_input("मोबाईल नंबर (WhatsApp No):")
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
            making_charge = st.number_input("मजुरी / Labour Charge:", min_value=0.0)
            
        with col4:
            gst_select = st.selectbox("GST टक्केवारी / GST %:", [0.0, 3.0, 1.0])
            st.write("**🔀 जुनी मोड वजावट (Old Gold/Silver Exchange)**")
            old_gold_allow = st.checkbox("जुनी मोड घ्यायची आहे का?")
            
            if old_gold_allow:
                old_gold_type = st.selectbox("मोडीचा धातू प्रकार:", ["Gold (सोने)", "Silver (चांदी)"])
                old_gold_item = st.text_input("मोडीच्या वस्तूचे नाव (उदा. जुनी अंगठी, चैन):", value="जुनी मोड")
                old_value = st.number_input("जुन्या मोडीची एकूण किंमत (₹):", min_value=0.0)
            else:
                old_gold_type = "-"
                old_gold_item = "-"
                old_value = 0.0
            
        with col5:
            metal_total = weight * live_rate
            subtotal = metal_total + making_charge
            gst_amt = subtotal * (gst_select / 100)
            grand_total = subtotal + gst_amt
            
            st.metric("दागिन्याची एकूण किंमत (Grand Total)", f"₹{grand_total:,.2f}")
            
            cash_paid = st.number_input("जमा रोकड (Cash Paid):", min_value=0.0, max_value=grand_total)
            balance_amount = grand_total - old_value - cash_paid
            st.metric("शिल्लक उधारी (Remaining Balance)", f"₹{balance_amount:,.2f}")
            
            reminder_date = st.date_input("उधारी वायदा तारीख:", value=datetime.today().date())

        if st.button("💾 बिल सेव्ह करा (Save Bill)"):
            if cust_name == "" or cust_phone == "":
                st.error("❌ ग्राहकाचे नाव आणि मोबाईल नंबर भरणे अनिवार्य आहे!")
            elif weight <= 0:
                st.error("❌ कृपया दागिन्याचे वजन ०पेक्षा जास्त टाका!")
            else:
                today_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute("""
                INSERT INTO billing_v4 (date, customer_name, customer_phone, item_name, metal_type, company_name, weight, rate_per_gm, making_charge, gst_percent, old_gold_type, old_gold_item, old_value, grand_total, cash_paid, balance_amount, reminder_date, bill_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (today_now, cust_name, cust_phone, i_name, f"{m_cat}", c_name, weight, live_rate, making_charge, gst_select, old_gold_type, old_gold_item, old_value, grand_total, cash_paid, balance_amount, str(reminder_date), bill_note))
                
                cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                conn.commit()
                
                st.session_state.last_bill = {
                    "today_now": today_now, "cust_name": cust_name, "cust_phone": cust_phone,
                    "i_name": i_name, "m_cat": m_cat, "m_type": m_type, "c_name": c_name,
                    "weight": weight, "live_rate": live_rate, "metal_total": metal_total,
                    "making_charge": making_charge, "gst_select": gst_select, "gst_amt": gst_amt,
                    "old_gold_type": old_gold_type, "old_gold_item": old_gold_item,
                    "grand_total": grand_total, "old_value": old_value, "cash_paid": cash_paid,
                    "balance_amount": balance_amount, "reminder_date": reminder_date, "bill_note": bill_note
                }
                st.success("✅ बिल यशस्वीरित्या सेव्ह झाले!")

        if st.session_state.last_bill:
            b = st.session_state.last_bill
            st.write("---")
            st.subheader("𖏉 व्हॉट्सॲप आणि प्रिंट पर्याय (WhatsApp & Print Options)")
            
            old_gold_details_msg = f"\n🔄 *जुनी मोड वजावट:* {b['old_gold_item']} ({b['old_gold_type']}) - ₹{b['old_value']:,.2f}" if b['old_value'] > 0 else ""
            default_msg = f"✨ *{shop_name}* ✨\n\nप्रिय *{b['cust_name']}*,\nतुमचे बिल यशस्वीरित्या तयार झाले आहे:\n\n💍 *दागिना:* {b['i_name']} ({b['m_cat']})\n⚖️ *वजन:* {b['weight']}g\n💰 *एकूण बिल:* ₹{b['grand_total']:,.2f}{old_gold_details_msg}\n💵 *जमा रोकड:* ₹{b['cash_paid']:,.2f}\n🔴 *बाकी उधारी:* ₹{b['balance_amount']:,.2f}\n\nआमच्या दुकानाला भेट दिल्याबद्दल धन्यवाद! 🙏"
            custom_wp_text = st.text_area("💬 व्हॉट्सॲप मेसेज एडिट करा:", value=default_msg, height=200)
            
            encoded_text = urllib.parse.quote(custom_wp_text)
            whatsapp_url = f"https://wa.me/91{b['cust_phone']}?text={encoded_text}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color: #25D366; color: white; padding: 12px; border-radius: 5px; border:none; width:100%; font-size:16px; font-weight:bold; cursor:pointer; margin-bottom: 20px;">📲 WhatsApp वर मेसेज पाठवा</button></a>', unsafe_allow_html=True)

            print_style = st.radio("बिलाचा आकार निवडा:", ["A4 Size Paper", "80mm Thermal Paper", "Manual Layout (No Tax/Plain)"], horizontal=True)
            
            logo_str = "👑<br>" if show_shop_logo else ""
            hallmark_str = "<br>[ BIS HALLMARK ]" if show_hallmark_logo else ""
            
            # --- HTML स्ट्रिंग्स आधीच व्यवस्थित सेट करून घेतल्या (No nested f-strings with brackets) ---
            old_gold_tr = f"<tr><td>जुनी मोड वजा ({b['old_gold_item']} - {b['old_gold_type']}):</td><td style='text-align: right;'>- ₹{b['old_value']:.2f}</td></tr>" if b['old_value'] > 0 else ""
            due_date_div = f"<div style='font-weight: bold;'>वायदा तारीख: {b['reminder_date']}</div>" if b['balance_amount'] > 0 else ""

            gst_row_thermal = f"<tr><td>GST ({b['gst_select']}%):</td><td style='text-align: right;'>₹{b['gst_amt']:.2f}</td></tr>" if b['gst_select'] > 0 else ""
            gst_row_a4 = f"<tr><td><b>GST ({b['gst_select']}%):</b></td><td style='text-align: right;'>₹{b['gst_amt']:.2f}</td></tr>" if b['gst_select'] > 0 else ""
            
            gstin_div_thermal = f"<div style='text-align: center; font-weight: bold;'>GSTIN: {gst_number}</div>" if b['gst_select'] > 0 else ""
            gstin_p_a4 = f"<b>GSTIN:</b> {gst_number}" if b['gst_select'] > 0 else ""

            if print_style == "80mm Thermal Paper":
                bill_html = f"""
                <div style="width: 300px; font-family: 'Courier New', monospace; font-size: 12px; border: 1px solid #000; padding: 10px; background: #fff; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold; font-size: 12px; letter-spacing: 1px;">॥ श्री गणेश प्रसन्न ॥</div>
                    <div style="text-align: center; font-weight: bold; font-size:16px; margin-top:5px;">{logo_str}{shop_name}</div>
                    <div style="text-align: center;">{shop_address}</div>
                    {gstin_div_thermal}
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <div><b>तारीख:</b> {b['today_now']} | <b>ग्राहक:</b> {b['cust_name']}</div>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <div>{b['i_name']} ({b['m_cat']})</div>
                    <div>वजन: {b['weight']}g | दर: ₹{b['live_rate']}</div>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    <table style="width:100%; border-collapse: collapse;">
                        <tr><td>धातू मूल्य:</td><td style="text-align: right;">₹{b['metal_total']:.2f}</td></tr>
                        <tr><td>मजुरी:</td><td style="text-align: right;">₹{b['making_charge']:.2f}</td></tr>
                        {gst_row_thermal}
                        <tr style="font-weight: bold; border-top: 1px dashed #000;"><td>एकूण बिल:</td><td style="text-align: right;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td>जमा रोकड:</td><td style="text-align: right;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; border-top: 1px solid #000;"><td>बाकी उधारी:</td><td style="text-align: right;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="border-top: 1px dashed #000; margin: 5px 0;"></div>
                    {due_date_div}
                    <div style="text-align: center; font-size: 11px; margin-top: 5px; font-weight: bold;">* Subject to Sangola Jurisdiction *</div>
                    <div style="text-align: center; margin-top: 5px;">{b['bill_note']}{hallmark_str}</div>
                </div>
                """
                st.markdown(bill_html, unsafe_allow_html=True)
                
            elif print_style == "A4 Size Paper":
                bill_html = f"""
                <div style="width: 100%; max-width: 750px; font-family: Arial, sans-serif; border: 2px solid #000; padding: 30px; background: #fff; color: #000; margin: 0 auto;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 5px;">
                        <tr>
                            <td style="font-size: 12px; font-weight: bold; text-align: left; vertical-align: top; color: #333;">* Subject to Sangola Jurisdiction *</td>
                            <td style="font-size: 14px; font-weight: bold; text-align: center; vertical-align: top; letter-spacing: 1px;">॥ श्री गणेश प्रसन्न ॥</td>
                            <td style="width: 30%;"></td>
                        </tr>
                    </table>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 50%;"><h2>{logo_str}{shop_name}</h2><p>{shop_address}<br>{gstin_p_a4}</p></td>
                            <td style="text-align: right; width: 50%;"><h1>INVOICE</h1><p><b>तारीख:</b> {b['today_now']}<br><b>मोबाईल:</b> {b['cust_phone']}</p></td>
                        </tr>
                    </table>
                    <div style="border-top: 2px solid #000; margin: 15px 0;"></div>
                    <p><b>ग्राहक (Customer Name):</b> {b['cust_name']}</p>
                    <table style="width: 100%; border: 1px solid #000; border-collapse: collapse; margin-top: 15px;">
                        <tr style="background-color: #f2f2f2; font-weight: bold;">
                            <th style="border: 1px solid #000; padding: 8px;">तपशील (Item Details)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">वजन (Weight)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">आजचा दर (Rate)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">मजुरी (Labour)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">एकूण रक्कम</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #000; padding: 8px;">{b['i_name']} ({b['m_cat']}) <br><small>Brand: {b['c_name']}</small></td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">{b['weight']}g</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['live_rate']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['making_charge']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{(b['metal_total']+b['making_charge']):.2f}</td>
                        </tr>
                    </table>
                    <table style="width: 50%; margin-left: 50%; margin-top: 20px; border-collapse: collapse;">
                        <tr><td><b>Subtotal:</b></td><td style="text-align: right;">₹{b['metal_total']+b['making_charge']:.2f}</td></tr>
                        {gst_row_a4}
                        <tr style="font-weight: bold; border-top: 1px solid #000;"><td>Grand Total:</td><td style="text-align: right;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td>जमा रोकड (Paid):</td><td style="text-align: right;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; font-size: 16px; border-top: 2px double #000;"><td>बाकी रक्कम (Balance):</td><td style="text-align: right; color: red;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="margin-top: 30px; font-size: 12px; text-align: center; font-style: italic; border-top: 1px solid #ccc; padding-top: 10px;">{b['bill_note']}{hallmark_str}</div>
                </div>
                """
                st.markdown(bill_html, unsafe_allow_html=True)
                
            elif print_style == "Manual Layout (No Tax/Plain)":
                bill_html = f"""
                <div style="width: 100%; max-width: 500px; font-family: 'Courier New', monospace; border: 1px solid #888; padding: 20px; background: #fafafa; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold; font-size: 13px;">॥ श्री गणेश प्रसन्न ॥</div>
                    <h3 style="text-align: center; margin:5px 0 0 0;">{shop_name} (अंदाजे बिल)</h3>
                    <p style="text-align: center; margin:0; font-size:12px;">{shop_address}</p>
                    <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                    <p style="margin:2px 0;"><b>ग्राहक:</b> {b['cust_name']} | <b>तारीख:</b> {b['today_now']}</p>
                    <p style="margin:2px 0;"><b>दागिना:</b> {b['i_name']} ({b['m_cat']}) - {b['weight']}g</p>
                    <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td>दागिना किंमत:</td><td style="text-align: right;">₹{b['metal_total'] + b['making_charge']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr style="font-weight:bold; border-top: 1px solid #000;"><td>एकूण द्यावे:</td><td style="text-align: right;">₹{b['grand_total'] - b['gst_amt']:.2f}</td></tr>
                        <tr><td>जमा केले:</td><td style="text-align: right;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight:bold; font-size:14px; color:blue; border-top: 1px solid #000;"><td>बाकी रक्कम:</td><td style="text-align: right;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <p style="text-align: left; font-size: 11px; font-weight: bold; margin-top: 10px; border-top: 1px dashed #000; padding-top: 5px;">* Subject to Sangola Jurisdiction *</p>
                    <p style="text-align:center; font-size:11px; margin-top:5px;">* हे कच्चे/मॅन्युअल बिल आहे. *</p>
                </div>
                """
                st.markdown(bill_html, unsafe_allow_html=True)
                
            st.info("💡 प्रिटींगसाठी कीबोर्डवर Ctrl + P दाबा.")

# ==============================================================================
# विभाग २: स्टॉक मॅनेजमेंट
# ==============================================================================
elif choice == "📦 स्टॉक मॅनेजमेंट / Stock Management":
    st.title("📦 स्टॉक मॅनेजमेंट आणि प्रगत शोध")
    st.write("---")
    
    tab1, tab2 = st.tabs(["➕ नवीन स्टॉक जोडा (Add Stock)", "📋 सध्याचा स्टॉक व सर्च (View & Search Stock)"])
    
    with tab1:
        st.subheader("🆕 नवीन मालाची एंट्री")
        with st.form("stock_form", clear_on_submit=True):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                m_category_input = st.selectbox("मुख्य कॅटेगरी (Category):", ["Gold", "Silver"])
                m_type_input = st.selectbox("प्रकार/टच (Type/Purity):", ["22K", "24K", "18K", "92.5 Sterling", "Fine Silver", "Regular Silver"])
                i_name_input = st.text_input("दागिन्याचे नाव (Item Name):")
            with col_s2:
                c_name_input = st.text_input("कंपनी/ब्रँडचे नाव:", value="Own Stock")
                stock_grams_input = st.number_input("एकूण वजन ग्रॅममध्ये:", min_value=0.0, step=0.01)
                alert_limit_input = st.number_input("स्टॉक अलर्ट मर्यादा (Grams):", min_value=0.0, value=5.0, step=0.01)
            
            submit_stock = st.form_submit_button("💾 स्टॉक जतन करा")
            if submit_stock:
                if i_name_input == "" or stock_grams_input <= 0:
                    st.error("❌ योग्य माहिती भरा!")
                else:
                    cursor.execute("INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit) VALUES (?, ?, ?, ?, ?, ?)", (m_category_input, m_type_input, i_name_input, c_name_input, stock_grams_input, alert_limit_input))
                    conn.commit()
                    st.success("✅ स्टॉक जोडला!")
                    st.rerun()

    with tab2:
        st.subheader("🔍 स्टॉक शोध पर्याय")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_item = st.text_input("📦 दागिन्याच्या नावाने शोधा:")
        with col_f2:
            search_cat = st.selectbox("कॅटेगरीनुसार फिल्टर:", ["सर्व (All)", "Gold", "Silver"])
            
        query_s = "SELECT id AS 'ID', metal_category AS 'कॅटेगरी', metal_type AS 'प्रकार', item_name AS 'दागिना', company_name AS 'कंपनी', stock_grams AS 'वजन (ग्रॅम)', alert_limit AS 'अलर्ट लिमिट' FROM items_stock WHERE 1=1"
        params_s = []
        
        if search_cat != "सर्व (All)":
            query_s += " AND metal_category = ?"
            params_s.append(search_cat)
        if search_item:
            query_s += " AND item_name LIKE ?"
            params_s.append(f"%{search_item}%")
            
        df_stock = pd.read_sql_query(query_s, conn, params=params_s)
        
        if df_stock.empty:
            st.info("ℹ️ शोधलेला किंवा उपलब्ध कोणताही स्टॉक नाही.")
        else:
            st.dataframe(df_stock, use_container_width=True)

# ==============================================================================
# विभाग ३: ग्राहक उधारी व इतिहास
# ==============================================================================
elif choice == "📊 ग्राहक उधारी व इतिहास / Customer Ledger":
    st.title("📊 ग्राहक उधारी व इतिहास लेजर")
    st.write("---")
    
    df_all_ledger = pd.read_sql_query("SELECT grand_total, cash_paid, balance_amount FROM billing_v4", conn)
    
    if df_all_ledger.empty:
        st.info("ℹ️ अजून एकही बिलाची नोंद नाही.")
    else:
        st.columns(3)[0].metric("📊 एकूण विक्री", f"₹{df_all_ledger['grand_total'].sum():,.2f}")
        st.columns(3)[1].metric("🟢 एकूण जमा रोकड", f"₹{df_all_ledger['cash_paid'].sum():,.2f}")
        st.columns(3)[2].metric("🔴 एकूण मार्केट उधारी", f"₹{df_all_ledger['balance_amount'].sum():,.2f}", delta_color="inverse")
        st.write("---")
        
        st.subheader("💵 उधारी जमा काउंटर")
        df_debtors = pd.read_sql_query("SELECT id, customer_name, balance_amount FROM billing_v4 WHERE balance_amount > 0", conn)
        if not df_debtors.empty:
            debtor_options = {row['id']: f"बिल ID: {row['id']} | {row['customer_name']} (बाकी: ₹{row['balance_amount']:.2f})" for idx, row in df_debtors.iterrows()}
            with st.form("pay_form"):
                sb_id = st.selectbox("ग्राहक निवडा:", options=list(debtor_options.keys()), format_func=lambda x: debtor_options[x])
                amt_pay = st.number_input("रक्कम जमा करा (₹):", min_value=0.0)
                if st.form_submit_button("✅ अपडेट पेमेंट"):
                    cursor.execute("SELECT customer_name, cash_paid, balance_amount FROM billing_v4 WHERE id=?", (sb_id,))
                    c_name, c_paid, c_bal = cursor.fetchone()
                    if 0 < amt_pay <= c_bal:
                        cursor.execute("UPDATE billing_v4 SET cash_paid=?, balance_amount=? WHERE id=?", (c_paid+amt_pay, c_bal-amt_pay, sb_id))
                        conn.commit()
                        st.success("✅ पेमेंट अपडेट झाले!")
                        st.rerun()
                    else: st.error("❌ चुकीची रक्कम!")

        st.write("---")
        
        st.subheader("🔍 ग्राहक आणि बिलांचा इतिहास शोधा")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            search_cust_name = st.text_input("👤 ग्राहकाच्या नावाने किंवा नंबरने शोधा:")
        with col_l2:
            search_bill_item = st.text_input("💍 दागिन्याच्या नावाने बिल शोधा:")
            
        query_l = """
            SELECT id AS 'बिल ID', date AS 'तारीख', customer_name AS 'ग्राहक', customer_phone AS 'मोबाईल', 
                   item_name AS 'दागिना', old_gold_type AS 'मोड धातू', old_gold_item AS 'मोड वस्तू', old_value AS 'मोड किंमत (₹)',
                   grand_total AS 'एकूण बिल (₹)', cash_paid AS 'जमा रोकड (₹)', 
                   balance_amount AS 'बाकी उधारी (₹)'
            FROM billing_v4 WHERE 1=1
        """
        params_l = []
        
        if search_cust_name:
            query_l += " AND (customer_name LIKE ? OR customer_phone LIKE ?)"
            params_l.extend([f"%{search_cust_name}%", f"%{search_cust_name}%"])
        if search_bill_item:
            query_l += " AND item_name LIKE ?"
            params_l.append(f"%{search_bill_item}%")
            
        query_l += " ORDER BY id DESC"
        
        df_ledger = pd.read_sql_query(query_l, conn, params=params_l)
        st.dataframe(df_ledger, use_container_width=True)
