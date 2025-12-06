import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import datetime
import requests
import threading
import time
import random
from PIL import Image
from bs4 import BeautifulSoup

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. INVISIBLE ENGINE (LIVE DOLLAR)
# ==========================================
@st.cache_data(ttl=3600)
def get_dolar_bna():
    url = "https://www.bna.com.ar/Personas"
    backup = 1060.00
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            target = soup.find(string=re.compile("Dolar U.S.A"))
            if target:
                row = target.find_parent('tr')
                cols = row.find_all('td')
                if len(cols) >= 3:
                    return float(cols[2].get_text().replace(',', '.'))
        return backup
    except: return backup

DOLAR_BNA = get_dolar_bna() 
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"
URL_FORM_GOOGLE = "" # 🔴 PASTE YOUR GOOGLE FORM LINK HERE
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

OFFER_MINUTES = 10 

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

TOASTS_SUCCESS = ["🛒 Calculating weight...", "🔥 Price per Bar OK", "✅ Added to order", "🏗️ Load Ready"]

# ==========================================
# 3. STATE
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None

# Fixed Timer
if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=OFFER_MINUTES)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hi, I'm Miguel.**\nI quote steel directly from the factory. Send me your list and take advantage of the limited-time discount."}]

# ==========================================
# 4. BACKEND
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try: return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

csv_context = load_data()

def send_to_google_form_background(client, amount, opportunity):
    if URL_FORM_GOOGLE:
        try: 
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(client), 
                ID_CAMPO_MONTO: str(amount), 
                ID_CAMPO_OPORTUNIDAD: str(opportunity)
            }, timeout=1)
        except: pass

def log_interaction(user_text, amount):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    op = "HIGH" if amount > 1500000 else "MEDIUM" if amount > 500000 else "LOW"
    st.session_state.log_data.append({"Date": ts, "User": user_text[:50], "Amount": amount})
    threading.Thread(target=send_to_google_form_background, args=(user_text, amount, op)).start()

def parse_bot_orders(text):
    new_items = []
    for qty, prod, price, type_ in re.findall(r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]', text):
        item = {
            "quantity": float(qty), 
            "product": prod.strip(), 
            "unit_price": float(price), 
            "subtotal": float(qty)*float(price), 
            "type": type_.strip().upper()
        }
        st.session_state.cart.append(item)
        new_items.append(item)
    return new_items

def calculate_business():
    # Timer Check (Backend)
    now = datetime.datetime.now()
    time_remaining = st.session_state.expiry_time - now
    seconds_remaining = int(time_remaining.total_seconds())
    is_active = seconds_remaining > 0
    
    # Initial Python Format (So it doesn't show --:--)
    if is_active:
        m, s = divmod(seconds_remaining, 60)
        clock_init = f"{m:02d}:{s:02d}"
        clock_color = "#2e7d32" if m > 2 else "#d32f2f"
    else:
        clock_init = "00:00"
        clock_color = "#b0bec5"

    gross = sum(i['subtotal'] for i in st.session_state.cart)
    desc = 0; color = "#546e7a"; level = "LIST PRICE (EXPIRED)"; meta = 1500000
    
    has_hook = any(x['type'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart)
    
    if is_active:
        if gross > 5000000: desc = 18; level = "👑 PARTNER MAX (18%)"; color = "#6200ea"; meta = 0
        elif gross > 3000000: desc = 15; level = "🏗️ CONSTRUCTOR (15%)"; color = "#d32f2f"; meta = 5000000
        elif gross > 1500000:
            if has_hook: desc = 15; level = "🔥 WHOLESALER (15%)"; color = "#d32f2f"; meta = 5000000
            else: desc = 10; level = "🏢 PROJECT (10%)"; color = "#f57c00"; meta = 3000000
        else:
            if has_hook: desc = 15; level = "🔥 WHOLESALER (15%)"; color = "#d32f2f"; meta = 5000000
            else: desc = 3; level = "⚡ 3% EXTRA CASH"; color = "#2e7d32"; meta = 1500000
    else:
        if gross > 5000000: desc = 15; level = "PARTNER (NO BONUS)"; color = "#6200ea"
        else: desc = 0; level = "⚠️ OFFER EXPIRED"; color = "#455a64"

    net = gross * (1 - (desc/100))
    return gross, net, desc, color, level, meta, seconds_remaining, is_active, clock_color, clock_init

def generate_wa_link(total):
    txt = "Hi Martín, confirm order:\n" + "\n".join([f"▪ {i['quantity']}x {i['product']}" for i in st.session_state.cart])
    txt += f"\n💰 FINAL TOTAL: ${total:,.0f} + VAT"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 5. UI: HEADER WITH HYBRID CLOCK (PY+JS)
# ==========================================
subtotal, total_final, desc_actual, color_bar, level_name, next_meta, remaining_sec, offer_alive, timer_color, python_clock = calculate_business()
progress_pct = 100
if next_meta > 0: progress_pct = min((subtotal / next_meta) * 100, 100)

# EMPTY PRICE STATE
display_price = f"${total_final:,.0f}" if subtotal > 0 else "🛒 START QUOTING"
display_vat = "+VAT" if subtotal > 0 else ""
display_badge = level_name if subtotal > 0 else "⚡ START NOW"

# INJECTED JAVASCRIPT FOR THE CLOCK
js_script = f"""
<script>
    function startTimer(duration, display) {{
        var timer = duration, minutes, seconds;
        var interval = setInterval(function () {{
            minutes = parseInt(timer / 60, 10);
            seconds = parseInt(timer % 60, 10);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            display.textContent = minutes + ":" + seconds;

            if (--timer < 0) {{
                clearInterval(interval);
                display.textContent = "00:00";
            }}
        }}, 1000);
    }}
    setTimeout(function() {{
        var display = document.getElementById("countdown_display");
        if (display) {{ startTimer({remaining_sec}, display); }}
    }}, 500);
</script>
"""

st.markdown(f"""
    <style>
    .block-container {{ padding-top: 175px !important; padding-bottom: 60px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 95px; left: 0; width: 100%; background: white; z-index: 9999;
        display: flex; justify-content: space-around; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding-bottom: 5px;
    }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 10px; font-weight: bold; font-size: 0.9rem; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 10000;
        border-bottom: 4px solid {color_bar}; height: 95px;
    }}
    .top-strip {{ background: #111; color: #fff; padding: 5px 15px; display: flex; justify-content: space-between; font-size: 0.75rem; align-items: center; }}
    .cart-summary {{ padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; }}
    .price-tag {{ font-size: 1.5rem; font-weight: 900; color: #333; }}
    .badge {{ background: {color_bar}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 900; text-transform: uppercase; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
    .timer-box {{ color: {timer_color}; font-weight: 900; font-size: 0.8rem; background: #fff; padding: 2px 8px; border-radius: 4px; margin-left: 5px; }}
    .progress-container {{ width: 100%; height: 6px; background: #eee; position: absolute; bottom: 0; }}
    .progress-bar {{ height: 100%; width: {progress_pct}%; background: {color_bar}; transition: width 0.8s ease-out; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>🔥 PEDRO BRAVIN S.A.</span>
            <span>⏱️ EXPIRA EN: <span id="countdown_display" class="timer-box">{python_clock}</span></span>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{display_badge}</span>
                <div style="font-size:0.65rem; color:#666; margin-top:3px;">
                    {f"Extra savings: {desc_actual}%" if offer_alive and subtotal > 0 else "START SAVING NOW"}
                </div>
            </div>
            <div class="price-tag">{display_price} <span style="font-size:0.7rem; color:#666; font-weight:400;">{display_vat}</span></div>
        </div>
        <div class="progress-container"><div class="progress-bar"></div></div>
    </div>
    {js_script}
""", unsafe_allow_html=True)

# ==========================================
# 6. AI BRAIN (CALCULATING PESOS)
# ==========================================
try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: st.error("Missing API KEY")

sys_prompt = f"""
ROLE: Miguel, technical expert salesperson in steel.
DB: {csv_context}
FREE ZONE: {CIUDADES_GRATIS}
# INTERNAL DATA: DOLLAR = {DOLAR_BNA}

🧮 **IMMUTABLE MATH RULES:**
The CSV prices might be in Dollars. Multiply by {DOLAR_BNA} for PESOS.

1. **IPN / UPN / C PROFILE (Length 12m):**
   - CSV: Price per Kilo. Description: Weight per Meter.
   - 🧮 CALC: `(Weight_meter * 12) * CSV_Price * {DOLAR_BNA}`

2. **ANGLES / FLATS / T-BAR / ROUNDS (6m):**
   - CSV: Price per Kilo. Description: **TOTAL BAR WEIGHT**.
   - 🧮 CALC: `Total_Bar_Weight * CSV_Price * {DOLAR_BNA}`

3. **PIPES (Epoxy, Galv, Sched, Mech) (6.40m):**
   - CSV: Price per Kilo. Description: Weight per Meter.
   - 🧮 CALC: `(Weight_meter * 6.40) * CSV_Price * {DOLAR_BNA}`

4. **STRUCTURAL TUBES (6m):**
   - CSV: Price per BAR.
   - 🧮 CALC: `CSV_Price * {DOLAR_BNA}`

5. **FREIGHT:**
   - If far, calculate: `(KM * 2 * {COSTO_FLETE_USD} * {DOLAR_BNA})`.

OUTPUT: [VISIBLE TEXT] [ADD:QUANTITY:PRODUCT:UNIT_PRICE_PESOS:TYPE]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def process_vision(img):
    return st.session_state.chat_session.send_message(["Analyze list. APPLY MATH FORMULAS FOR WEIGHT. Generate [ADD...] commands with final bar price.", img]).text

# ==========================================
# 7. TABS INTERFACE
# ==========================================
tab1, tab2 = st.tabs(["💬 QUOTE", f"🛒 MY ORDER ({len(st.session_state.cart)})"])

with tab1:
    if not offer_alive:
        st.error("⚠️ TIME'S UP. PRICES UPDATED.")
        if st.button("🔄 REACTIVATE BENEFIT (EXTENSION)", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=OFFER_MINUTES)
            st.toast("✅ Time restarted!", icon="😅")
            st.rerun()

    with st.expander("📷 **Upload List Photo**", expanded=False):
        img_val = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
        if img_val is not None:
            file_id = f"{img_val.name}_{img_val.size}"
            if st.session_state.last_processed_file != file_id:
                with st.spinner("👀 Analyzing and calculating..."):
                    full_text = process_vision(Image.open(img_val))
                    news = parse_bot_orders(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    st.session_state.last_processed_file = file_id
                    if news: st.toast("🔥 Prices Calculated", icon='✅')
                    log_interaction("AUTO PHOTO", total_final)
                    st.rerun()

    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    if prompt := st.chat_input("Write your order here..."):
        if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Quoting..."):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    full_text = response.text
                    news = parse_bot_orders(full_text)
                    display = re.sub(r'\[ADD:.*?\]', '', full_text)
                    st.markdown(display)
                    
                    if news:
                        st.toast(random.choice(TOASTS_SUCCESS), icon='🛒')
                        st.markdown(f"""
                        <div style="background:#e8f5e9; padding:10px; border-radius:10px; border:1px solid #25D366; margin-top:5px;">
                            <strong>✅ {len(news)} items added.</strong><br>
                            <span style="font-size:0.85rem">💰 Total: ${total_final:,.0f} | ⏳ {reloj} min left</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if desc_actual >= 15 and len(st.session_state.cart) > 1: st.balloons()

                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    log_interaction(prompt, total_final)
                    if news: time.sleep(1.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    if not st.session_state.cart:
        st.info("Empty cart.")
    else:
        st.markdown(f"### 📋 Confirm Order ({len(st.session_state.cart)} items)")
        
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                with c1:
                    st.markdown(f"**{item['product']}**")
                    st.caption(f"Unit: ${item['unit_price']:,.0f}")
                with c2:
                    new_qty = st.number_input("Qty", min_value=0.0, value=float(item['quantity']), step=1.0, key=f"qty_{i}", label_visibility="collapsed")
                    if new_qty != item['quantity']:
                        if new_qty == 0: st.session_state.cart.pop(i)
                        else:
                            st.session_state.cart[i]['quantity'] = new_qty
                            st.session_state.cart[i]['subtotal'] = new_qty * item['unit_price']
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                st.markdown("---")

        col_res1, col_res2 = st.columns(2)
        col_res1.write("List Subtotal:")
        col_res2.write(f"${subtotal:,.0f}")
        
        if offer_alive and desc_actual > 0:
            col_res1.markdown(f"**Benefit {level_name}:**")
            col_res2.markdown(f"**-${subtotal * (desc_actual/100):,.0f}**")
        elif not offer_alive:
            st.warning("⚠️ DISCOUNT EXPIRED.")
            
        st.markdown(f"""
        <div style="background:{color_bar}; color:white; padding:20px; border-radius:15px; text-align:center; margin-top:15px; box-shadow: 0 4px 15px {color_bar}66; border: 2px solid #fff;">
            <div style="font-size:0.8rem; opacity:0.9;">FINAL CASH TOTAL (+VAT)</div>
            <div style="font-size:2.2rem; font-weight:900;">${total_final:,.0f}</div>
            <div style="font-size:0.8rem; margin-top:5px; background:rgba(0,0,0,0.2); padding:4px 10px; border-radius:10px; display:inline-block;">
                { '⚡ 3% EXTRA APPLIED' if offer_alive else '❌ LIST PRICE' }
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <a href="{generate_wa_link(total_final)}" target="_blank" style="
            display:block; width:100%; background-color:#25D366; color:white; margin-top:15px;
            text-align:center; padding:18px; border-radius:50px; text-decoration:none; 
            font-weight:bold; font-size:1.2rem; box-shadow: 0 4px 15px rgba(37,211,102,0.5);
            animation: pulse-green 2s infinite;">
            🚀 SEND ORDER NOW
        </a>
        <style>@keyframes pulse-green {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); }} }}</style>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("🗑️ EMPTY CART", type="secondary", use_container_width=True): st.session_state.cart = []; st.rerun()

if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
