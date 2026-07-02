import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import urllib.parse
import os
import base64
from datetime import datetime
from PIL import Image
import io

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

# items_stock टेबलमध्ये item_size कॉलम जोडला (नसल्यास)
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

# जुन्या डेटाबेसमध्ये जर कॉलम नसेल तर तो ॲड करण्यासाठी सेफ्टी चेक
try:
    cursor.execute("ALTER TABLE items_stock ADD COLUMN item_size TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass # कॉलम आधीपासूनच उपलब्ध आहे

# Image la HTML madhe dakhvanyasathi Base64 madhe convert karnare function
def get_image_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            return f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
        except:
            return None
    return None

# ==============================================================================
# २. प्राथमिक डिझाईन आणि साइडबार (UI Design & Sidebar)
# ==============================================================================
st.set_page_config(page_title="साईप्रसाद ज्वेलर्स ERP", page_icon="👑", layout="wide")

st.sidebar.header("🏪 मास्टर सेटिंग्ज / Master Settings")

shop_name = st.sidebar.text_input("दुकानाचे नाव (Shop Name):", value="साईप्रसाद ज्वेलर्स")
shop_prop = st.sidebar.text_input("प्रोप्रायटर (Proprietor):", value="धनंजय कालिदास पंडित")
shop_address = st.sidebar.text_area("दुकानाचा पत्ता (Address):", value="मुख्य पेठ, मारुती मंदिराजवळ, महूद बु॥, ता. सांगोला. मो. ९९७५७५०१२७")
gst_number = st.sidebar.text_input("GSTIN (GST नंबर):", value="27AAAAA0000A1Z1")

st.sidebar.subheader("🖼️ दुकानाचे लोगो अपलोड (Shop Logos)")
logo_file_1 = st.sidebar.file_uploader("१. मुख्य लोगो अपलोड करा (Main Logo):", type=["png", "jpg", "jpeg"])
logo_file_2 = st.sidebar.file_uploader("२. दुसरा लोगो / Hallmark लोगो (Optional):", type=["png", "jpg", "jpeg"])

show_hallmark_logo = st.sidebar.checkbox("बिलावर Hallmark मजकूर दाखवा?", value=True)

st.sidebar.header("💰 आजचे बाजार भाव / Daily Rates")
gold_24k_rate = st.sidebar.number_input("24K सोने दर (प्रति ग्रॅम):", value=7500.0)
gold_22k_rate = st.sidebar.number_input("22K सोने दर (प्रति ग्रॅम):", value=6875.0)
gold_18k_rate = st.sidebar.number_input("18K सोने दर (प्रति ग्रॅम):", value=5625.0)
silver_rate = st.sidebar.number_input("चांदी दर (प्रति ग्रॅम):", value=90.0)

menu = [
    "🧾 नवीन बिल काउंटर / New Bill", 
    "📦 स्टॉक मॅनेजमेंट / Stock & Barcode", 
    "📊 ग्राहक उधारी व इतिहास / Customer Ledger",
    "⚙️ बॅकअप आणि रिस्टोर / Database Backup"
]
choice = st.radio("मुख्य मेन्यू निवडा / Select Menu:", menu, horizontal=True)

if "last_bill" not in st.session_state:
    st.session_state.last_bill = None

logo64_1 = get_image_base64(logo_file_1)
logo64_2 = get_image_base64(logo_file_2)

# ==============================================================================
# विभाग १: नवीन बिल काउंटर (Billing Counter)
# ==============================================================================
if choice == "🧾 नवीन बिल काउंटर / New Bill":
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
            st.subheader("𖏉 व्हॉट्सॲप आणि प्रिंट पर्याय (WhatsApp & Print Options)")
            
            old_gold_details_msg = f"\n🔄 *जुनी मोड वजा:* {b['old_gold_item']} ({b['old_gold_type']}) - ₹{b['old_value']:,.2f}" if b['old_value'] > 0 else ""
            default_msg = f"✨ *{shop_name}* ✨\n\nप्रिय *{b['cust_name']}*,\nतुमचे बिल यशस्वीरित्या तयार झाले आहे:\n\n🧾 *बिल नंबर:* #{b['bill_id']}\n💍 *दागिना:* {b['i_name']} ({b['m_cat']})\n⚖️ *वजन:* {b['weight']}g\n💰 *एकूण बिल:* ₹{b['grand_total']:,.2f}{old_gold_details_msg}\n💵 *जमा रोकड:* ₹{b['cash_paid']:,.2f}\n🔴 *बाकी उधारी:* ₹{b['balance_amount']:,.2f}\n\nआमच्या दुकानाला भेट दिल्याबद्दल धन्यवाद! 🙏"
            custom_wp_text = st.text_area("💬 व्हॉट्सॲप मेसेज एडिट करा:", value=default_msg, height=150)
            
            encoded_text = urllib.parse.quote(custom_wp_text)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{b['cust_phone']}&text={encoded_text}"
            
            st.link_button("📲 WhatsApp वर मेसेज पाठवा (Mobile & Laptop Friendly)", url=whatsapp_url, use_container_width=True, type="primary")
            st.write("")

            with st.expander("⚙️ बिल कस्टमाइज करा (Customize Bill Layout)"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    custom_font_size = st.slider("बिलाचा फॉन्ट साईझ बदला (Font Size px):", min_value=11, max_value=20, value=14)
                    custom_border_style = st.selectbox("बिलाची बॉर्डर डिझाईन निवड:", ["solid (सलग रेघ)", "dashed (तुटक रेघ)", "double (डबल रेघ)", "none (बॉर्डर नाही)"], index=0).split(" ")[0]
                with col_c2:
                    custom_footer_msg = st.text_input("बिलाच्या अगदी शेवटी काय दाखवायचे? (Footer Custom Text):", value="धन्यवाद! पुन्हा भेट द्या.")
                    custom_bg_color = st.color_picker("बिलाचा बॅकग्राउंड रंग निवडा:", value="#FFFFFF")

            print_style = st.radio("बिलाचा आकार निवडा:", ["A4 Size Paper", "80mm Thermal Paper", "Manual Layout (No Tax/Plain)"], horizontal=True)
            
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

            old_gold_tr = ""
            if b['old_value'] > 0:
                old_gold_tr = f"<tr><td style='padding: 5px 0;'>जुनी मोड वजा ({b['old_gold_item']}):</td><td style='text-align: right; padding: 5px 0;'>- ₹{b['old_value']:.2f}</td></tr>"

            due_date_div = ""
            if b['balance_amount'] > 0:
                due_date_div = f"<div style='font-weight: bold; margin-top: 5px;'>वायदा तारीख: {b['reminder_date']}</div>"

            gst_row_thermal = ""
            if b['gst_select'] > 0:
                gst_row_thermal = f"<tr><td style='padding: 5px 0;'>GST ({b['gst_select']}%):</td><td style='text-align: right; padding: 5px 0;'>₹{b['gst_amt']:.2f}</td></tr>"

            gst_row_a4 = ""
            if b['gst_select'] > 0:
                gst_row_a4 = f"<tr><td style='padding: 5px 0;'><b>GST ({b['gst_select']}%):</b></td><td style='text-align: right; padding: 5px 0;'>₹{b['gst_amt']:.2f}</td></tr>"
            
            gstin_div_thermal = ""
            if b['gst_select'] > 0:
                gstin_div_thermal = f"<div style='text-align: center; font-weight: bold; margin-top: 2px;'>GSTIN: {gst_number}</div>"

            gstin_p_a4 = ""
            if b['gst_select'] > 0:
                gstin_p_a4 = f"<b>GSTIN:</b> {gst_number}"

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
                    <div><b>बिल नंबर (Bill No):</b> #{b['bill_id']}</div>
                    <div><b>तारीख:</b> {b['today_now']}</div>
                    <div><b>ग्राहक:</b> {b['cust_name']} [{b['cust_phone']}]</div>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    <div style="font-weight: bold;">{b['i_name']} ({b['m_cat']})</div>
                    <div>वजन: {b['weight']}g | दर: ₹{b['live_rate']}</div>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    <table style="width:100%; border-collapse: collapse; font-size: {custom_font_size}px;">
                        <tr><td style="padding: 3px 0;">धातू मूल्य:</td><td style="text-align: right; padding: 3px 0;">₹{b['metal_total']:.2f}</td></tr>
                        <tr><td style="padding: 3px 0;">मजुरी:</td><td style="text-align: right; padding: 3px 0;">₹{b['making_charge']:.2f}</td></tr>
                        {gst_row_thermal}
                        <tr style="font-weight: bold; border-top: 1px dashed #000;"><td style="padding: 5px 0;">एकूण बिल:</td><td style="text-align: right; padding: 5px 0;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td style="padding: 3px 0;">जमा रोकड:</td><td style="text-align: right; padding: 3px 0;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; border-top: 1px solid #000;"><td style="padding: 5px 0; font-size: 15px;">बाकी उधारी:</td><td style="text-align: right; padding: 5px 0; font-size: 15px;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="border-top: 1px dashed #000; margin: 8px 0;"></div>
                    {due_date_div}
                    <div style="text-align: center; font-size: 11px; margin-top: 8px; font-weight: bold;">* Subject to Jurisdiction *</div>
                    <div style="margin-top: 5px; font-size: 12px; border: 1px solid #ddd; padding: 5px; background:#f9f9f9;"><b>टीप / नियम:</b><br>{formatted_bill_note}</div>
                    <div style="text-align: center; margin-top: 8px; font-weight: bold; font-size: 12px;">{custom_footer_msg}{hallmark_str}</div>
                </div>
                """
                
            elif print_style == "A4 Size Paper":
                component_height = 760
                subtotal_val = b['metal_total'] + b['making_charge']
                bill_html = f"""
                <div style="width: 95%; max-width: 720px; font-family: Arial, sans-serif; font-size: {custom_font_size}px; border: 2px {custom_border_style} #000; padding: 20px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    {html_logo_section}
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                        <tr>
                            <td style="font-size: 11px; font-weight: bold; text-align: left; color: #333; width: 35%;">* Subject to Jurisdiction *</td>
                            <td style="font-size: 14px; font-weight: bold; text-align: center; width: 30%;">॥ श्री गणेश प्रसन्न ॥</td>
                            <td style="width: 35%;"></td>
                        </tr>
                    </table>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 50%; vertical-align: top;">
                                <h2 style="margin: 0 0 2px 0; font-size: 24px;">{shop_name}</h2>
                                <p style="margin: 0 0 5px 0; font-size: 13px; color: #55px;"><b>प्रोप्रायटर:</b> {shop_prop}</p>
                                <p style="margin: 0; font-size: 13px; line-height: 1.4;">{shop_address}<br>{gstin_p_a4}</p>
                            </td>
                            <td style="text-align: right; width: 50%; vertical-align: top;">
                                <h1 style="margin: 0 0 5px 0; font-size: 28px; color: #222;">INVOICE</h1>
                                <p style="margin: 0; font-size: 13px; line-height: 1.4;"><b>बिल नंबर (Bill No):</b> #{b['bill_id']}</p>
                                <p style="margin: 3px 0; font-size: 13px; line-height: 1.4;"><b>तारीख (Date):</b> {b['today_now']}</p>
                            </td>
                        </tr>
                    </table>
                    <div style="border-top: 2px solid #000; margin: 15px 0;"></div>
                    <p style="font-size: 15px; margin: 0 0 15px 0;"><b>ग्राहक (Customer Name):</b> {b['cust_name']} &nbsp;&nbsp;&nbsp;&nbsp; <b>मोबाईल (WhatsApp No):</b> {b['cust_phone']}</p>
                    <table style="width: 100%; border: 1px solid #000; border-collapse: collapse; font-size: {custom_font_size}px;">
                        <tr style="background-color: #f2f2f2; font-weight: bold;">
                            <th style="border: 1px solid #000; padding: 8px; text-align: left;">तपशील (Item Details)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">वजन (Weight)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">दर (Rate)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">मजुरी (Labour)</th>
                            <th style="border: 1px solid #000; padding: 8px; text-align: right;">एकूण रक्कम</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #000; padding: 8px; font-weight: bold;">{b['i_name']} ({b['m_cat']})</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">{b['weight']}g</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['live_rate']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right;">₹{b['making_charge']:.2f}</td>
                            <td style="border: 1px solid #000; padding: 8px; text-align: right; font-weight: bold;">₹{subtotal_val:.2f}</td>
                        </tr>
                    </table>
                    <table style="width: 50%; margin-left: 50%; margin-top: 15px; border-collapse: collapse; font-size: {custom_font_size}px;">
                        <tr><td style="padding: 4px 0;"><b>Subtotal:</b></td><td style="text-align: right; padding: 4px 0;">₹{subtotal_val:.2f}</td></tr>
                        {gst_row_a4}
                        <tr style="font-weight: bold; border-top: 1px solid #000;"><td style="padding: 5px 0;">Grand Total:</td><td style="text-align: right; padding: 5px 0;">₹{b['grand_total']:.2f}</td></tr>
                        {old_gold_tr}
                        <tr><td style="padding: 4px 0;">जमा रोकड (Paid):</td><td style="text-align: right; padding: 4px 0;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight: bold; font-size: 16px; border-top: 2px double #000;"><td style="padding: 6px 0;">बाकी रक्कम (Balance):</td><td style="text-align: right; padding: 6px 0; color: red;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="margin-top: 20px; font-size: 13px; text-align: left; border: 1px solid #ccc; padding: 10px; background:#fafafa;"><b>📜 नियम व अटी (Terms & Conditions):</b><br>{formatted_bill_note}</div>
                    <div style="margin-top: 20px; font-size: 13px; text-align: center; border-top: 1px solid #ccc; padding-top: 10px; font-weight: bold;">{custom_footer_msg}{hallmark_str}</div>
                </div>
                """
            elif print_style == "Manual Layout (No Tax/Plain)":
                component_height = 560
                bill_html = f"""
                <div style="width: 420px; font-family: 'Courier New', monospace; font-size: {custom_font_size}px; border: 2px {custom_border_style} #888; padding: 15px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold;">॥ श्री गणेश प्रसन्न ॥</div>
                    {html_logo_section}
                    <h3 style="text-align: center; margin:5px 0 0 0;">{shop_name} (अंदाजे बिल)</h3>
                    <p style="text-align: center; margin:0; font-size:11px;">प्रोप्रायटर: {shop_prop}</p>
                    <p style="text-align: center; margin:0; font-size:12px;">{shop_address}</p>
                    <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                    <p style="margin:2px 0;"><b>बिल नंबर:</b> #{b['bill_id']}</p>
                    <p style="margin:2px 0;"><b>ग्राहक:</b> {b['cust_name']} [{b['cust_phone']}]</p>
                    <p style="margin:2px 0;"><b>तारीख:</b> {b['today_now']}</p>
                    <p style="margin:2px 0;"><b>दागिना:</b> {b['i_name']} ({b['m_cat']}) - {b['weight']}g</p>
                    <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                    <table style="width: 100%; border-collapse: collapse; font-size: {custom_font_size}px;">
                        <tr><td style="padding: 3px 0;">दागिना किंमत:</td><td style="text-align: right; padding: 3px 0;">₹{(b['metal_total'] + b['making_charge']):.2f}</td></tr>
                        {old_gold_tr}
                        <tr style="font-weight:bold; border-top: 1px solid #000;"><td style="padding: 5px 0;">एकूण द्यावे:</td><td style="text-align: right; padding: 5px 0;">₹{(b['grand_total'] - b['gst_amt']):.2f}</td></tr>
                        <tr><td style="padding: 3px 0;">जमा केले:</td><td style="text-align: right; padding: 3px 0;">₹{b['cash_paid']:.2f}</td></tr>
                        <tr style="font-weight:bold; font-size:15px; color:blue; border-top: 1px solid #000;"><td style="padding: 5px 0;">बाकी रक्कम:</td><td style="text-align: right; padding: 5px 0;">₹{b['balance_amount']:.2f}</td></tr>
                    </table>
                    <div style="margin-top: 10px; font-size: 11px; border-top: 1px dashed #000; padding-top:5px;"><b>टिप:</b><br>{formatted_bill_note}</div>
                    <p style="text-align: center; font-size:11px; margin-top:10px; font-weight: bold;">{custom_footer_msg}</p>
                </div>
                """
            components.html(bill_html, height=component_height, scrolling=True)

# ==============================================================================
# विभाग २: स्टॉक मॅनेजमेंट आणि बारकोड (Stock Management & Barcode)
# ==============================================================================
elif choice == "📦 स्टॉक मॅनेजमेंट / Stock & Barcode":
    st.title("📦 स्टॉक मॅनेजमेंट आणि बारकोड लेबल जनरेटर")
    st.write("---")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.subheader("➕ नवीन स्टॉक आणि साईझ जोडा / Add Stock")
        s_category = st.selectbox("कॅटेगरी / Category:", ["Gold", "Silver"])
        if s_category == "Gold":
            s_type = st.selectbox("प्रकार / Type:", ["Gold 24K", "Gold 22K", "Gold 18K"])
        else:
            s_type = st.selectbox("प्रकार / Type:", ["Silver 99.9", "Silver Ornament"])
            
        s_item_name = st.text_input("दागिन्याचे नाव (उदा. Ear Tops, राणी हार, तोडे):")
        s_size = st.text_input("दागिन्याची साईझ / आकार (उदा. Small, Medium, 2.4, 6 No, Lahan):", value="-")
        s_company = st.text_input("उत्पादक / कंपनी नाव:", value="Own Manufacture")
        s_grams = st.number_input("दागिन्याचे वजन ग्रॅममध्ये (Weight in Grams):", min_value=0.0, step=0.01, format="%.3f")
        s_alert = st.number_input("अलर्ट मर्यादा ग्रॅम (Low Stock Limit):", min_value=0.0, value=1.0, step=0.1)
        
        if st.button("📥 स्टॉक सुरक्षित करा / Save Stock"):
            if s_item_name == "":
                st.error("❌ दागिन्याचे नाव टाकणे आवश्यक आहे!")
            else:
                cursor.execute("""
                INSERT INTO items_stock (metal_category, metal_type, item_name, company_name, stock_grams, alert_limit, item_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (s_category, s_type, s_item_name, s_company, s_grams, s_alert, s_size))
                conn.commit()
                st.success(f"✅ {s_item_name} (वजन: {s_grams}g, साईझ: {s_size}) यशस्वीरित्या स्टॉक मध्ये जोडले!")
                st.rerun()

    with col_s2:
        st.subheader("🔍 प्रगत स्टॉक सर्च (वजन व साईझनुसार फिल्टर)")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_name = st.text_input("🔎 दागिन्याचे नाव / प्रकार शोधा:")
        with col_f2:
            search_size = st.text_input("📏 विशिष्ट साईझ शोधा (Size Filter):")
            
        # SQL Query for filtering
        query_str = "SELECT id AS 'आयटम ID', metal_category AS 'कॅटेगरी', metal_type AS 'प्रकार', item_name AS 'नाव', item_size AS 'साईझ', company_name AS 'कंपनी', stock_grams AS 'वजन (g)', alert_limit FROM items_stock WHERE 1=1"
        params = []
        
        if search_name:
            query_str += " AND (item_name LIKE ? OR metal_type LIKE ?)"
            params.append(f"%{search_name}%")
            params.append(f"%{search_name}%")
        if search_size:
            query_str += " AND item_size LIKE ?"
            params.append(f"%{search_size}%")
            
        df_stock = pd.read_sql_query(query_str, conn, params=params)
        
        if df_stock.empty:
            st.info("ℹ️ शोधलेला किंवा कोणताही स्टॉक उपलब्ध नाही.")
        else:
            def highlight_low_stock(row):
                return ['background-color: #ffcccc' if row['वजन (g)'] <= row['alert_limit'] else '' for _ in row]
            st.dataframe(df_stock.style.apply(highlight_low_stock, axis=1), use_container_width=True)
            
            # --- बारकोड कस्टमायझेशन विभाग ---
            st.write("---")
            st.subheader("🏷️ कस्टमाईज्ड बारकोड प्रिंट करा / Customize Barcode Size")
            
            barcode_id = st.selectbox("ज्या दागिन्याचा बारकोड पाहिजे तो आयटम निवडा:", 
                                      options=df_stock['आयटम ID'].tolist(),
                                      format_func=lambda x: f"ID: {x} - " + df_stock[df_stock['आयटम ID']==x]['नाव'].values[0] + " (" + str(df_stock[df_stock['आयटम ID']==x]['वजन (g)'].values[0]) + "g)")
            
            if barcode_id:
                selected_row = df_stock[df_stock['आयटम ID'] == barcode_id].iloc[0]
                b_id = str(selected_row['आयटम ID']).zfill(5) # ५ अंकी युनिक कोड बनवण्यासाठी
                b_name = selected_row['नाव']
                b_weight = selected_row['वजन (g)']
                b_size = selected_row['साईझ']
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    bc_layout = st.radio("बारकोडचा आकार निवडा (Ear Tops साठी लहान निवडा):", ["लहान साईझ (Small - for Ear Tops)", "मोठी साईझ (Standard)"], horizontal=True)
                with col_b2:
                    st.write("💡 *टिप: कंट्रोल + P (Ctrl+P) दाबून प्रिंट काढा.*")
                
                # कस्टमाईज साईझ नुसार CSS बदलणे
                if bc_layout == "लहान साईझ (Small - for Ear Tops)":
                    width_px, height_px, font_size, bc_width = "170px", "85px", "9px", "1"
                else:
                    width_px, height_px, font_size, bc_width = "260px", "130px", "12px", "2"
                
                barcode_html = f"""
                <div style="display: flex; justify-content: center; font-family: Arial, sans-serif; margin-top: 10px;">
                    <div id="printArea" style="width: {width_px}; height: {height_px}; border: 1px dotted #888; padding: 4px; text-align: center; background: #fff; color: #000; box-sizing: border-box; overflow: hidden;">
                        <div style="font-size: {font_size}; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.1;">{b_name}</div>
                        <div style="font-size: {font_size}; margin: 2px 0; font-weight: bold; display: flex; justify-content: space-around; line-height: 1.1;">
                            <span>वजन: <b>{b_weight}g</b></span>
                            <span>साईझ: <b>{b_size}</b></span>
                        </div>
                        <div style="display: flex; justify-content: center; align-items: center; margin-top: 1px;">
                            <svg id="barcode"></svg>
                        </div>
                    </div>
                </div>
                
                <!-- JsBarcode Script लोड करणे -->
                <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
                <script>
                    JsBarcode("#barcode", "{b_id}", {{
                        format: "CODE128",
                        width: {bc_width},
                        height: { "20" if bc_layout.startswith("लहान") else "40" },
                        displayValue: true,
                        fontSize: { "8" if bc_layout.startswith("लहान") else "11" },
                        margin: 0
                    }});
                </script>
                """
                components.html(barcode_html, height=180)
            
            st.write("---")
            st.subheader("🗑️ स्टॉक डिलीट करा")
            del_id = st.number_input("डिलीट करण्यासाठी आयटम ID टाका:", min_value=1, step=1)
            if st.button("❌ आयटम कायमचा काढा (Delete Item)"):
                cursor.execute("DELETE FROM items_stock WHERE id=?", (del_id,))
                conn.commit()
                st.warning(f"🗑️ आयटम ID {del_id} डिलीट केला आहे.")
                st.rerun()

# ==============================================================================
# विभाग ३: ग्राहक उधारी व इतिहास (Customer Ledger)
# ==============================================================================
elif choice == "📊 ग्राहक उधारी व इतिहास / Customer Ledger":
    st.title("📊 ग्राहक उधारी खाते आणि इतिहास / Customer Ledger")
    st.write("---")
    
    df_all_bills = pd.read_sql_query("SELECT id AS 'बिल ID', date AS 'तारीख', customer_name AS 'ग्राहक', customer_phone AS 'मोबाईल', item_name AS 'दागिना', grand_total AS 'एकूण बिल', cash_paid AS 'जमा रोकड', balance_amount AS 'बाकी उधारी', reminder_date AS 'वायदा तारीख' FROM billing_v4 ORDER BY id DESC", conn)
    
    if df_all_bills.empty:
        st.info("ℹ️ अद्याप एकही बिलाची नोंद झालेली नाही.")
    else:
        search_cust = st.text_input("🔍 ग्राहकाचे नाव किंवा मोबाईल नंबर टाकून शोधा:")
        if search_cust:
            df_filtered = df_all_bills[df_all_bills['ग्राहक'].str.contains(search_cust, case=False, na=False) | df_all_bills['मोबाईल'].str.contains(search_cust, na=False)]
        else:
            df_filtered = df_all_bills
            
        st.dataframe(df_filtered, use_container_width=True)
        
        total_udhari = df_filtered['बाकी उधारी'].sum()
        st.subheader(f"🔴 एकूण येणे उधारी (Total Outstanding): ₹{total_udhari:,.2f}")
        
        st.write("---")
        st.subheader("💸 उधारी जमा पावती काउंटर / Clear Balance Owed")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            pay_bill_id = st.number_input("ज्या बिलाची उधारी जमा करायची आहे तो 'बिल ID' टाका:", min_value=1, step=1)
            pay_amount = st.number_input("जमा करायची रक्कम (₹):", min_value=0.0, step=100.0)
            
        with col_l2:
            if st.button("💵 उधारी जमा करा (Update Payment)"):
                cursor.execute("SELECT balance_amount, cash_paid, customer_name, customer_phone FROM billing_v4 WHERE id=?", (pay_bill_id,))
                res = cursor.fetchone()
                if res:
                    curr_bal, curr_paid, c_name, c_phone = res[0], res[1], res[2], res[3]
                    if pay_amount > curr_bal:
                        st.error(f"❌ चूक! ग्राहकाची बाकी फक्त ₹{curr_bal} आहे. तुम्ही जास्त रक्कम टाकत आहात.")
                    else:
                        new_bal = curr_bal - pay_amount
                        new_paid = curr_paid + pay_amount
                        cursor.execute("UPDATE billing_v4 SET balance_amount=?, cash_paid=? WHERE id=?", (new_bal, new_paid, pay_bill_id))
                        conn.commit()
                        st.success(f"✅ ₹{pay_amount} जमा झाले! नवीन बाकी: ₹{new_bal}")
                        
                        confirm_msg = f"✨ *{shop_name}* ✨\n\nप्रिय *{c_name}*,\nतुमच्या कडून बिल नंबर *#{pay_bill_id}* साठी ₹{pay_amount:,.2f} ची उधारी रक्कम जमा झाली आहे.\n\n📉 *आता शिल्लक बाकी उधारी:* ₹{new_bal:,.2f}\n\nधन्यवाद! 🙏"
                        encoded_confirm = urllib.parse.quote(confirm_msg)
                        confirm_url = f"https://api.whatsapp.com/send?phone=91{c_phone}&text={encoded_confirm}"
                        st.link_button("📲 जमा पावती WhatsApp वर पाठवा", url=confirm_url, type="primary")
                else:
                    st.error("❌ या आयडीचे कोणतेही बिल सापडले नाही.")

# ==============================================================================
# विभाग ४: बॅकअप आणि रिस्टोर (Backup Menu Anchor)
# ==============================================================================
elif choice == "⚙️ बॅकअप आणि रिस्टोर / Database Backup":
    st.title("⚙️ सिस्टम बॅकअप / Database Management")
    st.write("---")
    st.info("डेटा सुरक्षित ठेवण्यासाठी नियमितपणे तुमच्या डेटाबेस फाईलचा बॅकअप घ्या.")
    with open(DB_FILE, "rb") as f:
        st.download_button("📥 सुरक्षित बॅकअप फाईल डाऊनलोड करा (Download Database)", data=f, file_name=DB_FILE, mime="application/octet-stream")
