import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime

# ==============================================================================
# १. डेटाबेस सेटअप (Database Setup)
# ==============================================================================
conn = sqlite3.connect("jewellery_erp_fixed.db", check_same_thread=False)
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
    alert_limit REAL
)
""")
conn.commit()

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
choice = st.radio("मुख्य मेन्यू निवडा / Select Menu:", menu, horizontal=True)

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
        bill_note = st.text_area("बिलाच्या खालील टीप / नियम व अटी (Custom Notes/Terms):", 
                                value="१. घडणावळ परत मिळणार नाही.\n२. हॉलमार्क दागिन्यांची १००% गॅरंटी.\n३. उधारीची रक्कम वेळेत जमा करावी.")
        
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
            
            # जास्तीत जास्त किती कॅश स्वीकारू शकतो (एकूण बिलातून मोडीची किंमत वजा करून उरलेली रक्कम)
            max_cash_allowed = float(max(0.0, grand_total - old_value))
            cash_paid = st.number_input("जमा रोकड (Cash Paid):", min_value=0.0, max_value=max_cash_allowed, value=0.0)
            
            # अचूक शिल्लक उधारी हिशोब
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
            
            old_gold_details_msg = f"\n🔄 *जुनी मोड वजावट:* {b['old_gold_item']} ({b['old_gold_type']}) - ₹{b['old_value']:,.2f}" if b['old_value'] > 0 else ""
            default_msg = f"✨ *{shop_name}* ✨\n\nप्रिय *{b['cust_name']}*,\nतुमचे बिल यशस्वीरित्या तयार झाले आहे:\n\n🧾 *बिल नंबर:* #{b['bill_id']}\n💍 *दागिना:* {b['i_name']} ({b['m_cat']})\n⚖️ *वजन:* {b['weight']}g\n💰 *एकूण बिल:* ₹{b['grand_total']:,.2f}{old_gold_details_msg}\n💵 *जमा रोकड:* ₹{b['cash_paid']:,.2f}\n🔴 *बाकी उधारी:* ₹{b['balance_amount']:,.2f}\n\nआमच्या दुकानाला भेट दिल्याबद्दल धन्यवाद! 🙏"
            custom_wp_text = st.text_area("💬 व्हॉट्सॲप मेसेज एडिट करा:", value=default_msg, height=150)
            
            encoded_text = urllib.parse.quote(custom_wp_text)
            whatsapp_url = f"https://wa.me/91{b['cust_phone']}?text={encoded_text}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color: #25D366; color: white; padding: 12px; border-radius: 5px; border:none; width:100%; font-size:16px; font-weight:bold; cursor:pointer; margin-bottom: 20px;">📲 WhatsApp वर मेसेज पाठवा</button></a>', unsafe_allow_html=True)

            with st.expander("⚙️ बिल कस्टमाइज करा (Customize Bill Layout)"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    custom_font_size = st.slider("बिलाचा फॉन्ट साईझ बदला (Font Size px):", min_value=11, max_value=20, value=14)
                    custom_border_style = st.selectbox("बिलाची बॉर्डर डिझाईन निवड:", ["solid (सलग रेघ)", "dashed (तुटक रेघ)", "double (डबल रेघ)", "none (बॉर्डर नाही)"], index=0).split(" ")[0]
                with col_c2:
                    custom_footer_msg = st.text_input("बिलाच्या अगदी शेवटी काय दाखवायचे? (Footer Custom Text):", value="धन्यवाद! पुन्हा भेट द्या.")
                    custom_bg_color = st.color_picker("बिलाचा बॅकग्राउंड रंग निवडा:", value="#FFFFFF")

            print_style = st.radio("बिलाचा आकार निवडा:", ["A4 Size Paper", "80mm Thermal Paper", "Manual Layout (No Tax/Plain)"], horizontal=True)
            
            logo_str = "👑<br>" if show_shop_logo else ""
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
            component_height = 450

            if print_style == "80mm Thermal Paper":
                component_height = 570
                bill_html = f"""
                <div style="width: 320px; font-family: 'Courier New', monospace; font-size: {custom_font_size}px; border: 2px {custom_border_style} #000; padding: 12px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold; font-size: 14px;">॥ श्री गणेश प्रसन्न ॥</div>
                    <div style="text-align: center; font-weight: bold; font-size: 18px; margin-top: 5px;">{logo_str}{shop_name}</div>
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
                    <div style="text-align: center; font-size: 11px; margin-top: 8px; font-weight: bold;">* Subject to Sangola Jurisdiction *</div>
                    <div style="margin-top: 5px; font-size: 12px; border: 1px solid #ddd; padding: 5px; background:#f9f9f9;"><b>टीप / नियम:</b><br>{formatted_bill_note}</div>
                    <div style="text-align: center; margin-top: 8px; font-weight: bold; font-size: 12px;">{custom_footer_msg}{hallmark_str}</div>
                </div>
                """
                
            elif print_style == "A4 Size Paper":
                component_height = 720
                subtotal_val = b['metal_total'] + b['making_charge']
                bill_html = f"""
                <div style="width: 95%; max-width: 720px; font-family: Arial, sans-serif; font-size: {custom_font_size}px; border: 2px {custom_border_style} #000; padding: 20px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                        <tr>
                            <td style="font-size: 11px; font-weight: bold; text-align: left; color: #333; width: 35%;">* Subject to Sangola Jurisdiction *</td>
                            <td style="font-size: 14px; font-weight: bold; text-align: center; width: 30%;">॥ श्री गणेश प्रसन्न ॥</td>
                            <td style="width: 35%;"></td>
                        </tr>
                    </table>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 50%; vertical-align: top;">
                                <h2 style="margin: 0 0 5px 0; font-size: 24px;">{logo_str}{shop_name}</h2>
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
                component_height = 520
                bill_html = f"""
                <div style="width: 420px; font-family: 'Courier New', monospace; font-size: {custom_font_size}px; border: 2px {custom_border_style} #888; padding: 15px; background: {custom_bg_color}; color: #000; margin: 0 auto;">
                    <div style="text-align: center; font-weight: bold;">॥ श्री गणेश प्रसन्न ॥</div>
                    <h3 style="text-align: center; margin:5px 0 0 0;">{shop_name} (अंदाजे बिल)</h3>
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
            st.info("💡 प्रिटींगसाठी बिलाच्या भागावर उजवे (Right) क्लिक करून Print दाबा किंवा Ctrl + P दाबा.")

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
        metric_cols = st.columns(3)
        metric_cols[0].metric("📊 एकूण विक्री", f"₹{df_all_ledger['grand_total'].sum():,.2f}")
        metric_cols[1].metric("🟢 एकूण जमा रोकड", f"₹{df_all_ledger['cash_paid'].sum():,.2f}")
        metric_cols[2].metric("🔴 एकूण मार्केट उधारी", f"₹{df_all_ledger['balance_amount'].sum():,.2f}", delta_color="inverse")
        st.write("---")
        
        st.subheader("💵 उधारी जमा काउंटर")
        df_debtors = pd.read_sql_query("SELECT id, customer_name, balance_amount FROM billing_v4 WHERE balance_amount > 0", conn)
        if not df_debtors.empty:
            debtor_options = {row['id']: f"बिल ID: {row['id']} | {row['customer_name']} (बाकी: ₹{row['balance_amount']:.2f})" for idx, row in df_debtors.iterrows()}
            with st.form("pay_form"):
                st.write("💸 **थेट बिल नंबर सिलेक्ट करून उधारी जमा करा:**")
                sb_id = st.selectbox("बिल नंबर आणि ग्राहक निवडा:", options=list(debtor_options.keys()), format_func=lambda x: debtor_options[x])
                amt_pay = st.number_input("रक्कम जमा करा (₹):", min_value=0.0)
                if st.form_submit_button("✅ अपडेट पेमेंट"):
                    cursor.execute("SELECT customer_name, cash_paid, balance_amount FROM billing_v4 WHERE id=?", (sb_id,))
                    c_name, c_paid, c_bal = cursor.fetchone()
                    if 0 < amt_pay <= c_bal:
                        cursor.execute("UPDATE billing_v4 SET cash_paid=?, balance_amount=? WHERE id=?", (c_paid+amt_pay, c_bal-amt_pay, sb_id))
                        conn.commit()
                        st.success(f"✅ बिल नंबर #{sb_id} साठी पेमेंट अपडेट झाले!")
                        st.rerun()
                    else: st.error("❌ केलेली रक्कमेत चूक आहे किंवा उधारीपेक्षा जास्त आहे!")

        st.write("---")
        
        st.subheader("🔍 ग्राहक आणि बिलांचा इतिहास शोधा")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            search_cust_name = st.text_input("👤 ग्राहक नाव / नंबर / बिल नंबरने शोधा:")
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
            query_l += " AND (customer_name LIKE ? OR customer_phone LIKE ? OR id = ?)"
            params_l.extend([f"%{search_cust_name}%", f"%{search_cust_name}%", search_cust_name])
        if search_bill_item:
            query_l += " AND item_name LIKE ?"
            params_l.append(f"%{search_bill_item}%")
            
        query_l += " ORDER BY id DESC"
        
        df_ledger = pd.read_sql_query(query_l, conn, params=params_l)
        st.dataframe(df_ledger, use_container_width=True)
