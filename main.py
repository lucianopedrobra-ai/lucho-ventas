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

# ==========================================
# 1. CONFIGURACIÓN (APP MÓVIL)
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES DE NEGOCIO (ANCHOR POINTS) ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"

# --- CONEXIÓN GOOGLE SHEETS ---
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

# --- LOGS GOOGLE FORMS ---
URL_FORM_GOOGLE = "" # 🔴 PEGAR TU LINK AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- ZONA DE BENEFICIO LOGÍSTICO (ESTO SÍ LO VENDE EL BOT) ---
CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

# ==========================================
# 2. ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\nCotizo aceros directo de fábrica. Pasame tu lista o subí una foto."}]

# ==========================================
# 3. BACKEND
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try: return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

csv_context = load_data()

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE:
        try: requests.post(URL_FORM_GOOGLE, data={ID_CAMPO_CLIENTE: str(cliente), ID_CAMPO_MONTO: str(monto), ID_CAMPO_OPORTUNIDAD: str(oportunidad)}, timeout=1); except: pass

def log_interaction(user_text, monto):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    op = "ALTA" if monto > 1500000 else "MEDIA" if monto > 500000 else "BAJA"
    st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:30], "Monto": monto})
    threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto, op)).start()

def parsear_ordenes_bot(texto):
    patron = r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto)
    for cant, prod, precio, tipo in coincidencias:
        st.session_state.cart.append({
            "cantidad": float(cant), "producto": prod.strip(),
            "precio_unit": float(precio), "subtotal": float(cant) * float(precio),
            "tipo": tipo.strip().upper()
        })
    return bool(coincidencias)

def calcular_negocio():
    bruto = sum(i['subtotal'] for i in st.session_state.cart)
    desc = 3; color = "#546e7a"; nivel = "INICIAL"
    
    if any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart):
        desc = 15; nivel = "🔥 MAYORISTA"; color = "#d32f2f"
    elif bruto > 3000000: desc = 15; nivel = "👑 PARTNER"; color = "#6200ea"
    elif bruto > 1500000: desc = 10; nivel = "🏗️ OBRA"; color = "#f57c00"
        
    neto = bruto * (1 - (desc/100))
    return neto, desc, color, nivel

def generar_link_wa(total):
    txt = "Hola Martín, confirmar pedido:\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL: ${total:,.0f} + IVA"
    txt += f"\n(Condición: {CONDICION_PAGO})"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 4. UI MÓVIL (HEADER FIJO + FAB)
# ==========================================
total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
pct_barra = min(total_final / 3000000 * 100, 100)

st.markdown(f"""
    <style>
    .block-container {{ padding-top: 130px !important; padding-bottom: 80px !important; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 99999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{ background: #232f3e; color: white; padding: 5px 15px; display: flex; justify-content: space-between; font-size: 0.7rem; }}
    .cart-summary {{ padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; }}
    .price-tag {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
    .badge {{ background: {color_barra}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; }}
    .float-wa {{
        position: fixed; width: 55px; height: 55px; bottom: 80px; right: 20px;
        background-color: #25d366; color: white; border-radius: 50px; text-align: center; 
        font-size: 28px; box-shadow: 2px 2px 10px rgba(0,0,0,0.3); z-index: 10000; 
        display: flex; align-items: center; justify-content: center; transition: transform 0.2s;
    }}
    .float-wa:hover {{ transform: scale(1.1); }}
    </style>
    <div class="fixed-header">
        <div class="top-strip"><span>PEDRO BRAVIN S.A.</span><span>COTIZADOR OFICIAL</span></div>
        <div class="cart-summary">
            <div><span class="badge">{nombre_nivel} {desc_actual}% OFF</span></div>
            <div class="price-tag">${total_final:,.0f} <span style="font-size:0.7rem; font-weight:400; color:#666;">+IVA</span></div>
        </div>
        <div style="width:100%; height:4px; background:#eee;"><div style="height:100%; width:{pct_barra}%; background:{color_barra}; transition:width 0.5s;"></div></div>
    </div>
    <a href="{generar_link_wa(total_final)}" class="float-wa" target="_blank"><i class="fa-brands fa-whatsapp"></i></a>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

with st.sidebar:
    st.header(f"🛒 CARRITO ({len(st.session_state.cart)})")
    for i, item in enumerate(st.session_state.cart):
        c1, c2 = st.columns([4,1])
        c1.markdown(f"**{item['cantidad']}x** {item['producto']}"); c1.caption(f"${item['subtotal']:,.0f}")
        if c2.button("❌", key=f"d{i}"): st.session_state.cart.pop(i); st.rerun()
    st.divider()
    if st.button("🗑️ Vaciar"): st.session_state.cart = []; st.rerun()

# ==========================================
# 5. CEREBRO IA (REGLAS DE NEGOCIO INMUTABLES)
# ==========================================
try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: st.error("Falta API KEY")

# 🔒 SECCIÓN BLINDADA: LOGÍSTICA AJUSTADA A PEDIDO 🔒
sys_prompt = f"""
ROL: Miguel, vendedor técnico Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

📜 REGLAS DE NEGOCIO INMUTABLES (DO NOT TOUCH):
1. **LARGOS COMERCIALES:**
   - **12.00 METROS:** Perfiles C, Hierro Construcción, Lisos AL 220, UPN/IPN (>=80).
   - **6.40 METROS:** Caños y Tubos redondos (Epoxi, Galv, Sched, Mec).
   - **6.00 METROS:** Tubos Estructurales, Ángulos, Planchuelas, UPN/IPN (<80).
2. **UNIDADES:** Clavos/Alambre = KG. Planchuelas/Mallas = UNIDAD. Alambres Agro = ROLLO.
3. **CHAPAS:** Acanalada=COD4. T101=COD6. Sin corte=Metro.
4. **LOGÍSTICA (IMPORTANTE):**
   - **ZONA BENEFICIO ({CIUDADES_GRATIS}):** ¡OFRECE ENVÍO GRATIS! Es tu gancho de venta.
   - **RESTO DEL PAÍS:** Estima costo (KM*2*0.85 USD*{DOLAR_BNA}) pero aclara: "Costo estimado. Martín coordina el envío final."
   - **RETIROS:** No definas el lugar exacto. Di "Retiro en Planta (A coordinar)".
5. **COMERCIAL:** Pago {CONDICION_PAGO}. Acopio 6 Meses.

SALIDA: Breve, Vendedor, Cross-Sell.
FORMATO: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. APLICA REGLAS INMUTABLES. Genera [ADD...]. SOLO CONFIRMA.", img]).text

# ==========================================
# 6. INTERFAZ MÓVIL
# ==========================================

with st.expander("📷 **SUBIR FOTO DE LISTA**", expanded=False):
    up_file = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
    if up_file and st.button("⚡ PROCESAR FOTO", type="primary", use_container_width=True):
        with st.spinner("Analizando reglas..."):
            txt = procesar_vision(Image.open(up_file))
            if parsear_ordenes_bot(txt):
                st.session_state.messages.append({"role": "assistant", "content": txt})
                log_interaction("FOTO", total_final)
                st.rerun()

for m in st.session_state.messages:
    if m["role"] != "system":
        clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
        if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").write(clean)

if p := st.chat_input("Tu pedido..."):
    if p == "#admin": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").write(p)
    
    with st.chat_message("assistant", avatar="👷‍♂️"):
        with st.spinner("..."):
            resp = st.session_state.chat_session.send_message(p).text
            parsear_ordenes_bot(resp)
            clean_resp = re.sub(r'\[ADD:.*?\]', '', resp).strip()
            st.write(clean_resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            log_interaction(p, total_final)
            if "[" in resp: st.rerun()

if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
