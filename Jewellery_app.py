import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import urllib.parse
import os
import base64
from datetime import datetime

# ==============================================================================
# १. डेटाबेस सेटअप (Database Setup)
# ==============================================================================
DB_FILE = "jewellery_erp_fixed.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

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
    alert_limit REAL,
    item_size TEXT
)
""")
conn.commit()

# इमेज कंव्हर्टर फंक्शन
def get_image_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            return f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
        except:
            return None
    return None

# ==============================================================================
# २. मॉडर्न इंटरफेस डिझाईन आणि थीम (Modern UI & Theme Settings)
# ==============================================================================
st.set_page_config(page_title="साईप्रसाद ज्वेलर्स ERP", page_icon="👑", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #2C3E50; }
    
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-left: 5px solid #D4AF37;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(212,175,55,0.15); }
    .metric-title { font-size: 14px; color: #7F8C8D; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 24px; color: #2C3E50; font-weight: bold; margin-top: 5px; }
    
    .stButton>button {
        background: linear-gradient(135deg, #D4AF37 0%, #AA7C11 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# साइडबार कॉन्फिगरेशन
st.sidebar.markdown("<h2 style='text-align: center; color: #AA7C11;'>⚙️ सेटिंग्स पॅनेल</h2>", unsafe_allow_html=True)
shop_name = st.sidebar.text_input("दुकानाचे नाव:", value="साईप्रसाद ज्वेलर्स")
shop_prop = st.sidebar.text_input("प्रोप्रायटर:", value="धनंजय कालिदास पंडित")
shop_address = st.sidebar.text_area("दुकानाचा पत्ता:", value="मुख्य पेठ, मारुती मंदिराजवळ, महूद बु॥, ता. सांगोला. मो. ९९७५७५०१२७")
gst_number = st.sidebar.text_input("GSTIN नंबर:", value="27AAAAA0000A1Z1")

logo_file_1 = st.sidebar.file_uploader("१. मुख्य लोगो (Main Logo):", type=["png", "jpg", "jpeg"])
logo_file_2 = st.sidebar.file_uploader("२. Hallmark लोगो (Optional):", type=["png", "jpg", "jpeg"])
show_hallmark_logo = st.sidebar.checkbox("बिलावर Hallmark दाखवा?", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #AA7C11;'>💰 आजचे बाजार भाव</h3>", unsafe_allow_html=True)
gold_24k_rate = st.sidebar.number_input("24K सोने दर (/gm):", value=7500.0)
gold_22k_rate = st.sidebar.number_input("22K सोने दर (/gm):", value=6875.0)
gold_18k_rate = st.sidebar.number_input("18K सोने दर (/gm):", value=5625.0)
silver_rate = st.sidebar.number_input("चांदी दर (/gm):", value=90.0)

# ==============================================================================
# ३. मॉडर्न नेव्हिगेशन मेनू
# ==============================================================================
menu = [
    "🏠 मुख्य डॅशबोर्ड / Home",
    "🧾 नवीन बिल काउंटर / New Bill", 
    "📦 स्टॉक आणि बारकोड / Stock & Barcode", 
    "📊 ग्राहक लेजर व उधारी / Ledger",
    "⚙️ बॅकअप / Backup"
]
choice = st.radio(" ", menu, horizontal=True)

if "last_bill" not in st.session_state:
    st.session_state.last_bill = None

logo64_1 = get_image_base64(logo_file_1)
logo64_2 = get_image_base64(logo_file_2)

# ==============================================================================
# विभाग १: मुख्य डॅशबोर्ड
# ==============================================================================
if choice == "🏠 मुख्य डॅशबोर्ड / Home":
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #111 0%, #2c3e50 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);">
        <h1 style="color: #D4AF37; margin: 0; font-size: 36px; font-weight: bold; letter-spacing: 1px;">👑 {shop_name} 👑</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 16px;">स्मार्ट ज्वेलरी मॅनेजमेंट ERP सिस्टीम | प्रोप्रायटर: {shop_prop}</p>
        <p style="margin: 5px 0 0 0; font-size: 13px; font-style: italic; opacity: 0.6;">{shop_address}</p>
    </div>
    """, unsafe_allow_html=True)

    df_bills_count = pd.read_sql_query("SELECT COUNT(id) as total_bills, SUM(balance_amount) as total_udhari FROM billing_v4", conn)
    df_stock_count = pd.read_sql_query("SELECT SUM(stock_grams) as total_gold FROM items_stock WHERE metal_category='Gold'", conn)
    df_silver_count = pd.read_sql_query("SELECT SUM(stock_grams) as total_silver FROM items_stock WHERE metal_category='Silver'", conn)

    total_b = df_bills_count['total_bills'].values[0] if df_bills_count['total_bills'].values[0] else 0
    total_u = df_bills_count['total_udhari'].values[0] if df_bills_count['total_udhari'].values[0] else 0.0
    total_g_stock = df_stock_count['total_gold'].values[0] if df_stock_count['total_gold'].values[0] else 0.0
    total_s_stock = df_silver_count['total_silver'].values[0] if df_silver_count['total_silver'].values[0] else 0.0

    st.markdown("<h3 style='margin-bottom:15px; color:#2c3e50;'>📈 लाईव्ह दुकानाचा अहवाल (Live Shop Report)</h3>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">🧾 एकूण बनवलेली बिले</div><div class="metric-value">{total_b} टॅग्ज</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card" style="border-left-color: #e74c3c;"><div class="metric-title">🔴 एकूण Market उधारी</div><div class="metric-value">₹{total_u:,.2f}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">👑 सोने एकूण स्टॉक</div><div class="metric-value">{total_g_stock:.3f} g</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card" style="border-left-color: #bdc3c7;"><div class="metric-title">🥈 चांदी एकूण स्टॉक</div><div class="metric-value">{total_s_stock:.3f} g</div></div>', unsafe_allow_html=True)

# ==============================================================================
# विभाग २: नवीन बिल काउंटर
# ==============================================================================
elif choice == "🧾 नवीन बिल काउंटर / New Bill":
    st.title("🧾 Advanced Jewellery Billing Counter")
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 ग्राहकाची माहिती / Customer Info")
        cust_name = st.text_input("ग्राहकाचे नाव (Customer Name):")
        cust_phone = st.text_input("मोबाईल नंबर (WhatsApp No):")
        bill_note = st.text_area("बिलाच्या खालील टीप / नियम व अटी (Custom Notes/Terms):", 
                                value="१. घडणावळ परत मिळणार नाही.\n२. हॉलमार्क दागिन्यांची १००% गॅरंटी.\n३. उधारीची रक्कम वेळेत जमा करावी.")
        
    with col2:
        st.subheader("🛍️ दागिन्याची निवड / Select Jewellery")
        filter_category = st.selectbox("कॅटेगरी निवडा (Filter Category):", ["सर्व (All)", "Gold", "Silver"])
        
        if filter_category == "सर्व (All)":
            query = "SELECT id, metal_category, metal_type, item_name, company_name, stock_grams, item_size FROM items_stock WHERE stock_grams > 0"
            df_avail = pd.read_sql_query(query, conn)
        else:
            query = "SELECT id, metal_category, metal_type, item_name, company_name, stock_grams, item_size FROM items_stock WHERE stock_grams > 0 AND metal_category = ?"
            df_avail = pd.read_sql_query(query, conn, params=(filter_category,))
        
        if df_avail.empty:
            st.warning(f"⚠️ {filter_category} कॅटेगरीमध्ये एकही दागिना उपलब्ध नाही! कृपया आधी स्टॉक जोडा.")
            selected_item_id = None
        else:
            item_options = {row['id']: f"Code #{row['id']} | {row['item_name']} [Size: {row['item_size']}] [वजन: {row['stock_grams']}g] ({row['metal_type']})" for idx, row in df_avail.iterrows()}
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
            weight = st.number_input(f"वजन ग्रॅममध्ये / Weight (Max: {s_grams}g):", min_value=0.0, max_value=s_grams, step=0.01, value=s_grams)
            making_charge = st.number_input("मजुरी / Labour Charge:", min_value=0.0)
            
        with col4:
            gst_select = st.selectbox("GST टक्केवारी / GST %:", [0.0, 3.0, 1.0])
            st.write("**🔀 जुनी मोड वजावट (Old Gold/Silver Exchange)**")
            old_gold_allow = st.checkbox("जुनी मोड घ्यायची आहे का?")
            
            if old_gold_allow:
                old_gold_type = st.selectbox("मोडीचा धातू प्रकार:", ["Gold (सोने)", "Silver (चांदी)"])
                old_gold_item = st.text_input("मोडीच्या वस्तूचे नाव:", value="जुनी मोड")
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
            max_cash_allowed = float(max(0.0, grand_total - old_value))
            cash_paid = st.number_input("जमा रोकड (Cash Paid):", min_value=0.0, max_value=max_cash_allowed, value=0.0)
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
                
                inserted_bill_id = cursor.lastrowid
                cursor.execute("UPDATE items_stock SET stock_grams = stock_grams - ? WHERE id=?", (weight, selected_item_id))
                conn.commit()
                
                st.session_state.last_bill = {
                    "bill_id": inserted_bill_id, "today_now": today_now, "cust_name": cust_name, "cust_phone": cust_phone,
                    "i_name": i_name, "m_cat": m_cat, "m_type": m_type, "c_name": c_name,
                    "weight": weight, "live_rate": live_rate, "metal_total": metal_total,
                    "making_charge": making_charge, "gst_select": gst_select, "gst_amt": gst_amt,
                    "old_gold_type": old_gold_type, "old_gold_item": old_gold_item,
                    "grand_total": grand_total, "old_value": old_value, "cash_paid": cash_paid,
                    "balance_amount": balance_amount, "reminder_date": reminder_date, "bill_note": bill_note
                }
                st.success(f"✅ बिल यशस्वीरित्या सेव्ह झाले! (बिल नंबर: #{inserted_bill_id})")

        if st.session_state.last_bill:
            b = st.session_state.last_bill
            st.write("---")
            st.subheader("𖏉 व्हॉट्सॲप आणि प्रिंट पर्याय")
            
            old_gold_details_msg = f"\n🔄 *जुनी मोड वजा:* {b['old_gold_item']} ({b['old_gold_type']}) - ₹{b['old_value']:,.2f}" if b['old_value'] > 0 else ""
            default_msg = f"✨ *{shop_name}* ✨\n\nHello *{b['cust_name']}*,\nतुमचे बिल यशस्वीरित्या तयार झाले आहे:\n\n🧾 *बिल नंबर:* #{b['bill_id']}\n💍 *दागिना:* {b['i_name']} ({b['m_cat']})\n⚖️ *वजन:* {b['weight']}g\n💰 *एकूण बिल:* ₹{b['grand_total']:,.2f}{old_gold_details_msg}\n💵 *जमा रोकड:* ₹{b['cash_paid']:,.2f}\n🔴 *बाकी उधारी:* ₹{b['balance_amount']:,.2f}\n\nआमच्या दुकानाला भेट दिल्याबद्दल धन्यवाद! 🙏"
            
            custom_wp_text = st.text_area("💬 व्हॉट्सॲप मेसेज एडिट करा (Customize Message):", value=default_msg, height=150)
            encoded_text = urllib.parse.quote(custom_wp_text)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{b['cust_phone']}&text={encoded_text}"
            
            st.link_button("📲 WhatsApp वर मेसेज पाठवा", url=whatsapp_url, use_container_width=True, type="primary")
            st.write("")

            with st.expander("⚙️ बिल कस्टमाइज करा"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    custom_font_size = st.slider("बिलाचा फॉन्ट साईझ बदला (Font Size px):", min_value=11, max_value=20, value=14)
                    custom_border_style = st.selectbox("बिलाची बॉर्डर डिझाईनं निवड:", ["solid", "dashed", "double", "none"], index=0)
                with col_c2:
                    custom_footer_msg = st.text_input("बिलाच्या अगदी शेवटी काय दाखवायचे?:", value="धन्यवाद! पुन्हा भेट द्या.")
                    custom_bg_color = st.color_picker("बिलाचा बॅकग्राउंड रंग निवडा:", value="#FFFFFF")

            print_style = st.radio("बिलाचा आकार निवडा:", ["A4 Size Paper", "80mm Thermal Paper"], horizontal=True)
            
            html_logo_section = "<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>"
            if logo64_1:
                html_logo_section += f"<img src='{logo64_1}' style='max-height: 70px; max-width: 130px; object-fit: contain;'>"
            else:
                html_logo_section += "<span style='font-size:25px;'>👑</span>"
            if logo64_2:
                html_logo_section += f"<img src='{logo64_2}' style='max-height: 70px; max-width: 130px; object-fit: contain;'>"
            else:
                html_logo_section += "<span></span>"
            html_logo_section += "</div>"
            
            hallmark_str = "<br>[ BIS HALLMARK ]" if show_hallmark_logo else ""
            formatted_bill_note = b['bill_note'].replace('\n', '<br>')
            old_gold_tr = f"<tr><td style='padding: 5px 0;'>जुनी मोड वजा ({b['old_gold_item']}):</td><td style='text-align: right; padding: 5px 0;'>- ₹{b['old_value']:.2f}</td></tr>" if b['old_value'] > 0 else ""
            due_date_div = f"<div style='font-weight: bold; margin-top: 5px;'>वायदा तारीख: {b['reminder_date']}</div>" if b['balance_amount'] > 0 else ""
            gst_row_thermal = f"<tr><td style='padding: 5px 0;'>GST ({b['gst_select']}%):</td><td style='text-align: right; padding: 5px 0;'>₹{b['gst_amt']:.2f}</td></tr>" if b['gst_select'] > 0 else ""
            gst_row_a4 = f"<tr><td style='padding: 5px 0;'><b>GST ({b['gst_select']}%):</b></td><td style='text-align: right; padding: 5px 0;'>₹{b['gst_amt']:.2f}</td></tr>" if b['gst_select'] > 0 else ""
            gstin_div_thermal = f"<div style='text-align: center; font-weight: bold; margin-top: 2px;'>GSTIN: {gst_number}</div>" if b['gst_select'] > 0 else ""
            gstin_p_a4 = f"<b>GSTIN:</b> {gst_number}" if b['gst_select'] > 0 else ""

            bill_html = ""
            component_height = 480

            if print_style == "80mm Thermal Paper":
                component_height = 620
                bill_html = f"""
                <div style="width: 320px; font-family: 'Courier New', monospace; font-size: {custom_font_size}px; border: 2px {custom_border_style} #000; padding: 12px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold; font-size: 12px;">॥ श्री गणेश प्रसन्न ॥</div>
                    {html_logo_section}
                    <div style="text-align: center; font-weight: bold; font-size: 18px; margin-top: 5px;">{shop_name}</div>
                    <div style="text-align: center; font-size: 11px; font-style: italic;">प्रोप्रायटर: {shop_prop}</div>
                    <div style="text-align: center; font-size: 12px;">{shop_address}</div>
                    {gstin_div_thermal}
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    <div><b>बिल नंबर:</b> #{b['bill_id']}</div>
                    <div><b>तारीख:</b> {b['today_now']}</div>
                    <div><b>ग्राहक नाव:</b> {b['cust_name']}</div>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    <div style="font-weight: bold;">{b['i_name']} ({b['m_cat']})</div>
                    <div>वजन: {b['weight']}g | दर: ₹{b['live_rate']}</div>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    <table style="width:100%; font-size: {custom_font_size}px;">
                        <tr><td>धातू मूल्य:</td><td style="text-align: right;">₹{b['metal_total']:.2f}</td></tr>
                        <tr><td>मजुरी:</td><td style="text-align: right;">₹{b['making_charge']:.2f}</td></tr>
                        {gst_row_thermal}
                        <tr style="font-weight: bold; border-top: 1px dashed #000;"><td>एकूण बिल:</td><td style="text-align: right;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td>जमा रोकड:</td><td style="text-align: right;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; border-top: 1px solid #000; font-size: 15px;"><td>बाकी उधारी:</td><td style="text-align: right;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    {due_date_div}
                    <div style="margin-top: 5px; font-size: 12px; border: 1px solid #ddd; padding: 5px; background:#f9f9f9;"><b>टीप:</b><br>{formatted_bill_note}</div>
                    <div style="text-align: center; margin-top: 8px; font-weight: bold;">{custom_footer_msg}{hallmark_str}</div>
                </div>
                """
            elif print_style == "A4 Size Paper":
                component_height = 760
                subtotal_val = b['metal_total'] + b['making_charge']
                bill_html = f"""
                <div style="width: 95%; max-width: 720px; font-family: Arial, sans-serif; font-size: {custom_font_size}px; border: 2px {custom_border_style} #000; padding: 20px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    {html_logo_section}
                    <table style="width: 100%; margin-bottom: 10px;">
                        <tr>
                            <td style="font-size: 11px; text-align: left; width: 40%;">* Subject to Sangola Jurisdiction *</td>
                            <td style="font-size: 14px; font-weight: bold; text-align: center; width: 30%;">॥ श्री गणेश प्रसन्न ॥</td>
                            <td style="width: 30%;"></td>
                        </tr>
                    </table>
                    <table style="width: 100%;">
                        <tr>
                            <td>
                                <h2 style="margin: 0; font-size: 24px;">{shop_name}</h2>
                                <p style="margin: 3px 0;"><b>प्रोप्रायटर:</b> {shop_prop}</p>
                                <p style="margin: 0; font-size: 13px;">{shop_address}<br>{gstin_p_a4}</p>
                            </td>
                            <td style="text-align: right; vertical-align: top;">
                                <h1 style="margin: 0; font-size: 28px; color: #222;">INVOICE</h1>
                                <p style="margin: 0;"><b>बिल नंबर:</b> #{b['bill_id']}</p>
                                <p style="margin: 3px 0;"><b>तारीख:</b> {b['today_now']}</p>
                            </td>
                        </tr>
                    </table>
                    <div style="border-top: 2px solid #000; margin: 15px 0;"></div>
                    <p style="font-size: 15px;"><b>ग्राहक नाव:</b> {b['cust_name']} &nbsp;&nbsp;&nbsp;&nbsp; <b>मोबाईल:</b> {b['cust_phone']}</p>
                    <table style="width: 100%; border: 1px solid #000; border-collapse: collapse; font-size: {custom_font_size}px;">
                        <tr style="background-color: #f2f2f2; font-weight: bold;">
                            <th style="border: 1px solid #000; padding: 8px; text-align: left;">तपशील (Item)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">वजन</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">दर</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">मजुरी</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">एकूण</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #000; padding: 8px; font-weight: bold;">{b['i_name']} ({b['m_cat']})</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">{b['weight']}g</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['live_rate']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['making_charge']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right; font-weight: bold;">₹{subtotal_val:.2f}</td>
                        </tr>
                    </table>
                    <table style="width: 50%; margin-left: 50%; margin-top: 15px; font-size: {custom_font_size}px;">
                        <tr><td><b>Subtotal:</b></td><td style="text-align: right;">₹{subtotal_val:.2f}</td></tr>
                        {gst_row_a4}
                        <tr style="font-weight: bold; border-top: 1px solid #000;"><td>Grand Total:</td><td style="text-align: right;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td>जमा रोकड:</td><td style="text-align: right;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; font-size: 16px; border-top: 2px double #000;"><td>बाकी रक्कम:</td><td style="text-align: right; color: red;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="margin-top: 20px; font-size: 13px; border: 1px solid #ccc; padding: 10px; background:#fafafa;"><b>📜 नियम व अटी:</b><br>{formatted_bill_note}</div>
                    <div style="margin-top: 20px; font-size: 13px; text-align: center; border-top: 1px solid #ccc; padding-top: 10px; font-weight: bold;">{custom_footer_msg}{hallmark_str}</div>
                </div>
                """
            components.html(bill_html, height=component_height, scrolling=True)

# ==============================================================================
# विभाग ३: स्टॉक मॅनेजमेंट आणि बारकोड जनरेटर
# ==============================================================================
elif choice == "📦 स्टॉक आणि बारकोड / Stock & Barcode":
    st.title("📦 स्टॉक मॅनेजमेंट आणि बारकोड जनरेटर")
    st.write("---")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.subheader("➕ नवीन स्टॉक आणि साईझ जोडा")
        s_category = st.selectbox("कॅटेगरी / Category:", ["Gold", "Silver"])
        if s_category == "Gold":
            s_type = st.selectbox("प्रकार / Type:", ["Gold 24K", "Gold 22K", "Gold 18K"])
        else:
            s_type = st.selectbox("प्रकार / Type:", ["Silver 99.9", "Silver Ornament"])
            
        s_item_name = st.text_input("दागिन्याचे नाव (उदा. Ear Tops, चैन):")
        s_size = st.text_input("दागिन्याची साईझ (उदा. Small, Medium, 2.4):", value="-")
        s_company = st.text_input("उत्पादक कंपनी:", value="Own Manufacture")
        s_grams = st.number_input("दागिन्याचे वजन ग्रॅममध्ये:", min_value=0.0, step=0.01, format="%.3f")
        s_alert = st.number_input("कमी स्टॉक अलर्ट मर्यादा (g):", min_value=0.0, value=1.0)
        
        if st.button("📥 स्टॉक सुरक्षित करा"):
            if s_item_name == "":
                st.error("❌ दागिन्याचे नाव आवश्यक आहे!")
            else:
                cursor.execute("INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit, item_size) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                               (s_category, s_type, s_item_name, s_company, s_grams, s_alert, s_size))
                conn.commit()
                inserted_id = cursor.lastrowid
                st.success(f"✅ {s_item_name} (ID: #{inserted_id}) स्टॉकमध्ये यशस्वीरित्या जोडले!")
                st.rerun()

    with col_s2:
        st.subheader("🔍 प्रगत स्टॉक सर्च")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_name = st.text_input("🔎 नाव / प्रकार शोधा:")
        with col_f2:
            search_size = st.text_input("📏 विशिष्ट साईझ शोधा:")
            
        query_str = "SELECT id, metal_category, metal_type, item_name, item_size, stock_grams, alert_limit FROM items_stock WHERE 1=1"
        params = []
        if search_name:
            query_str += " AND (item_name LIKE ? OR metal_type LIKE ?)"
            params.extend([f"%{search_name}%", f"%{search_name}%"])
        if search_size:
            query_str += " AND item_size LIKE ?"
            params.append(f"%{search_size}%")
            
        df_stock = pd.read_sql_query(query_str, conn, params=params)
        
        if df_stock.empty:
            st.info("ℹ️ स्टॉक खाली आहे.")
        else:
            display_df = df_stock.rename(columns={
                'id': 'आयटम ID', 'metal_category': 'कॅटेगरी', 'metal_type': 'प्रकार',
                'item_name': 'नाव', 'item_size': 'साईझ', 'stock_grams': 'वजन (g)'
            })
            st.dataframe(display_df.drop(columns=['alert_limit']), use_container_width=True)
            
            st.write("---")
            st.markdown("### 🖨️ बारकोड कस्टमायझेशन पॅनेल (Customize Barcode)")
            
            barcode_options = {row['id']: f"ID: #{row['id']} | {row['item_name']} ({row['stock_grams']}g)" for idx, row in df_stock.iterrows()}
            selected_b_id = st.selectbox("बारकोड लेबल प्रिंट करण्यासाठी निवडा:", options=list(barcode_options.keys()), format_func=lambda x: barcode_options[x])
            
            if selected_b_id:
                item_row = df_stock[df_stock['id'] == selected_b_id].iloc[0]
                
                # कस्टमायझेशन ऑप्शन्स (नवे पर्याय)
                st.write("**🎛️ स्टिकरवर काय प्रिंट करायचे ते निवडा:**")
                bc_1, bc_2, bc_3, bc_4 = st.columns(4)
                with bc_1:
                    b_size_opt = st.selectbox("बारकोड स्टिकर साईझ (Size):", ["Small (Ear Tops)", "Medium (Standard)", "Large"], index=0)
                with bc_2:
                    inc_shop = st.checkbox("दुकानाचे नाव दाखवा?", value=True)
                with bc_3:
                    inc_size = st.checkbox("साईझ (Size) दाखवा?", value=True)
                with bc_4:
                    inc_weight = st.checkbox("वजन (Weight) दाखवा?", value=True)
                
                # साईझनुसार CSS विड्थ सेट करणे
                sticker_width = "190px" if "Small" in b_size_opt else ("260px" if "Medium" in b_size_opt else "340px")
                font_base = "10px" if "Small" in b_size_opt else ("12px" if "Medium" in b_size_opt else "14px")
                bar_height = "18px" if "Small" in b_size_opt else "30px"
                
                # HTML घटक तयार करणे
                shop_html = f"<div style='font-size: {font_base}; font-weight: bold; text-transform: uppercase;'>{shop_name}</div>" if inc_shop else ""
                size_str = f" [{item_row['item_size']}]" if inc_size else ""
                
                weight_section = ""
                if inc_weight:
                    weight_section = f"""
                    <div style="display: flex; justify-content: space-between; font-size: 9px; margin-top: 3px; padding: 0 2px; border-top: 1px dashed #ccc;">
                        <span><b>Type:</b> {item_row['metal_type']}</span>
                        <span><b>Wt:</b> {item_row['stock_grams']} g</span>
                    </div>
                    """
                
                barcode_html = f"""
                <div id="barcode-sticker" style="width: {sticker_width}; border: 1px solid #000; padding: 6px; font-family: Arial, sans-serif; text-align: center; background: #fff; color: #000; margin: 10px auto;">
                    {shop_html}
                    <div style="font-size: {font_base}; margin: 1px 0;"><b>{item_row['item_name']}</b>{size_str}</div>
                    <div style="letter-spacing: 2px; background: repeating-linear-gradient(90deg, #000, #000 2px, #fff 2px, #fff 5px); height: {bar_height}; width: 90%; margin-left:5%;"></div>
                    <div style="font-size: 9px; font-weight: bold; margin-top: 2px;">CODE: *J{item_row['id']:05d}*</div>
                    {weight_section}
                    <button onclick="window.print();" style="margin-top: 5px; font-size: 9px; padding: 2px 6px; cursor: pointer;">🖨️ Print Label</button>
                </div>
                """
                components.html(barcode_html, height=180)

# ==============================================================================
# विभाग ४: ग्राहक लेजर व उधारी (सुधारित विभाग - सर्च व हिस्ट्री)
# ==============================================================================
elif choice == "📊 ग्राहक लेजर व उधारी / Ledger":
    st.title("📊 ग्राहक लेजर उधारी आणि कस्टमर हिस्ट्री")
    st.write("---")
    
    st.subheader("🔍 ग्राहक किंवा बिल सर्च करा")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        search_bill_id = st.text_input("🔎 बिल नंबरने शोधा (उदा. 1, 2):")
    with col_l2:
        search_cust_name = st.text_input("👤 ग्राहकाच्या नावाने शोधा:")
        
    # डेटाबेस मधून फिल्टर करणे
    ledger_query = "SELECT id, date, customer_name, customer_phone, grand_total, cash_paid, balance_amount FROM billing_v4 WHERE 1=1"
    ledger_params = []
    
    if search_bill_id:
        ledger_query += " AND id = ?"
        ledger_params.append(search_bill_id)
    if search_cust_name:
        ledger_query += " AND customer_name LIKE ?"
        ledger_params.append(f"%{search_cust_name}%")
        
    df_ledger = pd.read_sql_query(ledger_query, conn, params=ledger_params)
    
    if df_ledger.empty:
        st.warning("ℹ️ दिलेल्या माहितीनुसार कोणताही रेकॉर्ड सापडला नाही.")
    else:
        # सुंदर फॉरमॅट मध्ये दाखवणे
        disp_ledger = df_ledger.rename(columns={
            'id': 'बिल नंबर', 'date': 'तारीख', 'customer_name': 'ग्राहक नाव',
            'customer_phone': 'मोबाईल', 'grand_total': 'एकूण बिल', 
            'cash_paid': 'जमा रोकड', 'balance_amount': 'बाकी उधारी'
        })
        st.dataframe(disp_ledger, use_container_width=True)
        
        st.write("---")
        # उधारी जमा करण्याचा नवा पर्याय
        st.subheader("💰 उधारीचे पैसे जमा करा (Add Payment to Ledger)")
        
        # फक्त उधारी बाकी असलेली बिले ड्रॉपडाऊनमध्ये आणणे
        df_active_udhari = df_ledger[df_ledger['balance_amount'] > 0]
        
        if df_active_udhari.empty:
            st.success("🎉 सर्च केलेल्या रेकॉर्डमध्ये कोणाचीही उधारी शिल्लक नाही!")
        else:
            udhari_options = {row['id']: f"बिल #{row['id']} | {row['customer_name']} (बाकी: ₹{row['balance_amount']:.2f})" for idx, row in df_active_udhari.iterrows()}
            selected_bill_to_pay = st.selectbox("ज्या बिलाचे पैसे जमा करायचे आहेत ते निवडा:", options=list(udhari_options.keys()), format_func=lambda x: udhari_options[x])
            
            if selected_bill_to_pay:
                row_to_pay = df_active_udhari[df_active_udhari['id'] == selected_bill_to_pay].iloc[0]
                max_pay_allowed = float(row_to_pay['balance_amount'])
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    received_amt = st.number_input("💵 जमा झालेली रक्कम भरा (₹):", min_value=0.0, max_value=max_pay_allowed, step=10.0, value=max_pay_allowed)
                with col_p2:
                    st.write("")
                    st.write("")
                    if st.button("✅ रक्कम जमा करा (Update Payment)"):
                        new_balance = max_pay_allowed - received_amt
                        new_cash_paid = float(row_to_pay['cash_paid']) + received_amt
                        
                        cursor.execute("UPDATE billing_v4 SET cash_paid = ?, balance_amount = ? WHERE id = ?", (new_cash_paid, new_balance, selected_bill_to_pay))
                        conn.commit()
                        st.success(f"🎉 यशस्वी! बिल #{selected_bill_to_pay} मध्ये ₹{received_amt} जमा झाले. नवीन बाकी: ₹{new_balance:.2f}")
                        st.rerun()

        # ग्राहक हिस्ट्री दाखवणे
        if search_cust_name:
            st.write("---")
            st.subheader(f"📜 {search_cust_name} यांची संपूर्ण व्यवहार हिस्ट्री (Customer History)")
            for idx, row in df_ledger.iterrows():
                st.markdown(f"""
                * **बिल नंबर:** #{row['id']} | **तारीख:** {row['date']}
                * **खरेदी केलेला दागिना:** {row['grand_total']} रुपयांची एकूण खरेदी. (जमा: ₹{row['cash_paid']} | बाकी उधारी: ₹{row['balance_amount']})
                ---
                """)

# ==============================================================================
# विभाग ५: बॅकअप आणि रिस्टोर
# ==============================================================================
elif choice == "⚙️ बॅकअप / Backup":
    st.title("⚙️ डेटाबेस बॅकअप आणि रिस्टोर पॅनेल")
    st.write("---")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.subheader("📥 डेटाबेस बॅकअप घ्या (Download Backup)")
        try:
            with open(DB_FILE, "rb") as f:
                db_bytes = f.read()
            current_date = datetime.now().strftime("%d-%m-%Y")
            backup_filename = f"jewellery_erp_backup_{current_date}.db"
            
            st.download_button(
                label="💾 बॅकअप फाईल डाउनलोड करा",
                data=db_bytes,
                file_name=backup_filename,
                mime="application/octet-stream",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ बॅकअप एरर: {e}")

    with col_b2:
        st.subheader("📤 जुना बॅकअप रिस्टोर करा (Restore Backup)")
        uploaded_backup_file = st.file_uploader("तुमची बॅकअप (.db) फाईल निवडा:", type=["db"])
        if uploaded_backup_file is not None:
            confirm_restore = st.checkbox("होय, मला जुना डेटा रिस्टोर करायचा आहे.")
            if st.button("🔄 डेटा रिस्टोर करा (Confirm Restore)", type="primary", use_container_width=True):
                if confirm_restore:
                    try:
                        conn.close()
                        with open(DB_FILE, "wb") as f:
                            f.write(uploaded_backup_file.getbuffer())
                        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                        cursor = conn.cursor()
                        st.success("🎉 डेटा यशस्वीरित्या रिस्टोर झाला!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ डेटा रिस्टोर करताना समस्या आली: {e}")
                        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                        cursor = conn.cursor()
                else:
                    st.error("❌ कृपया वरील चेकबॉक्सवर टिक करा.")
