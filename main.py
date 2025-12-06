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

# INTENTO DE IMPORTAR MICROFONO
try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

# 🔴 PEGAR TU LINK DE GOOGLE FORM AQUI
URL_FORM_GOOGLE = "" 
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

FRASES_FOMO = [
    "🔥 Stock bajo en este ítem.",
    "⚡ 2 clientes están llevando esto.",
    "🚚 Salida de camión programada.",
    "📉 Precio congelado por 1 hora.",
    "💎 Oferta exclusiva web."
]

# ==========================================
# 2. ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\nCotizo aceros directo de fábrica. Hablame, escribí o subí foto."}]

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
        try: 
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(cliente), 
                ID_CAMPO_MONTO: str(monto), 
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }, timeout=1)
        except: 
            pass

def log_interaction(user_text, monto):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    op = "ALTA" if monto > 1500000 else "MEDIA" if monto > 500000 else "BAJA"
    st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Monto": monto})
    threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto, op)).start()

def parsear_ordenes_bot(texto):
    items_nuevos = []
    # Corrección Regex para detectar números decimales mejor
    patron = r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto)
    
    for cant, prod, precio, tipo in coincidencias:
        item = {
            "cantidad": float(cant), 
            "producto": prod.strip(), 
            "precio_unit": float(precio), 
            "subtotal": float(cant)*float(precio), 
            "tipo": tipo.strip().upper()
        }
        st.session_state.cart.append(item)
        items_nuevos.append(item)
    return items_nuevos

def calcular_negocio():
    bruto = sum(i['subtotal'] for i in st.session_state.cart)
    desc = 3; color = "#546e7a"; nivel = "INICIAL"
    
    # 1. Regla Gancho
    if any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart):
        desc = 15; nivel = "🔥 MAYORISTA"; color = "#d32f2f"
    # 2. Regla Volumen
    elif bruto > 3000000: desc = 15; nivel = "👑 PARTNER"; color = "#6200ea"
    elif bruto > 1500000: desc = 10; nivel = "🏗️ OBRA"; color = "#f57c00"
    
    return bruto, bruto*(1-(desc/100)), desc, color, nivel

def generar_link_wa(total):
    txt = "Hola Martín, confirmar pedido:\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL: ${total:,.0f} + IVA\n(Pago: {CONDICION_PAGO})"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 4. UI: HEADER FIJO + TABS
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
pct_barra = min(total_final / 3000000 * 100, 100) if total_final < 3000000 else 100

st.markdown(f"""
    <style>
    .block-container {{ padding-top: 130px !important; padding-bottom: 90px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    
    /* PESTAÑAS ESTILO APP */
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 80px; left: 0; width: 100%; background: white; z-index: 9999;
        display: flex; justify-content: space-around; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 10px; font-weight: bold; }}
    
    /* HEADER FIJO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 10000;
        border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{ background: #232f3e; color: white; padding: 6px 15px; display: flex; justify-content: space-between; font-size: 0.7rem; }}
    .cart-summary {{ padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; }}
    .price-tag {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
    .badge {{ background: {color_barra}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; }}
    .warning-text {{ color: #ffeb3b; font-weight: bold; font-size: 0.65rem; animation: pulse-yellow 2s infinite; }}
    @keyframes pulse-yellow {{ 0% {{ opacity: 0.8; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.8; }} }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip"><span>PEDRO BRAVIN S.A.</span><span class="warning-text">⚠️ PRECIOS ESTIMADOS IA</span></div>
        <div class="cart-summary">
            <div><span class="badge">{nombre_nivel} {desc_actual}% OFF</span></div>
            <div class="price-tag">${total_final:,.0f} <span style="font-size:0.7rem; color:#666;">+IVA</span></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 5. CEREBRO IA (REGLAS BLINDADAS)
# ==========================================
try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: st.error("Falta API KEY")

sys_prompt = f"""
ROL: Miguel, vendedor Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

📜 REGLAS DE NEGOCIO INMUTABLES (DO NOT TOUCH):
1. **LARGOS:** 12m (Perfiles/Hierro Const), 6.40m (Caños Epoxi/Galv), 6m (Resto).
2. **UNIDADES:** Clavos/Alambre=KG, Mallas/Planchuelas=UNIDAD, Alambre Agro=ROLLO.
3. **CHAPAS:** Acanalada=COD4, T101=COD6, Sin corte=METRO.
4. **LOGÍSTICA:**
   - ZONA BENEFICIO ({CIUDADES_GRATIS}): ¡ENVÍO GRATIS!
   - RESTO: Estima (KM*2*0.85 USD). Aclara "Estimado".
   - RETIROS: "Retiro en Planta".
5. **DISCLAIMER:** Precio estimado IA. Martín confirma.

SALIDA: Breve. FORMATO: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. APLICA REGLAS. Genera [ADD...]. SOLO CONFIRMA.", img]).text

# ==========================================
# 6. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])

with tab1:
    # --- ZONA DE INPUTS SUPERIORES ---
    c_mic, c_cam = st.columns([1, 1])
    
    with c_mic:
        if MIC_AVAILABLE:
            # EL BOTÓN QUE SIMULA GEMINI: GRANDE Y CLARO
            audio_text = speech_to_text(
                language='es', 
                start_prompt="🎙️ TOCÁ PARA HABLAR", 
                stop_prompt="⏹️ LISTO (ENVIAR)", 
                just_once=True, 
                key='mic_input',
                use_container_width=True # Ocupa todo el ancho disponible
            )
        else:
            st.warning("⚠️ Sin Micrófono")
            audio_text = None
            
    with c_cam:
        with st.expander("📷 **FOTO**", expanded=False):
            up_file = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
            if up_file and st.button("⚡ ENVIAR", type="primary", use_container_width=True):
                with st.spinner("👀 Mirando..."):
                    txt = procesar_vision(Image.open(up_file))
                    if parsear_ordenes_bot(txt):
                        st.session_state.messages.append({"role": "assistant", "content": txt})
                        log_interaction("FOTO", total_final)
                        st.rerun()

    # --- HISTORIAL CHAT ---
    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    # --- LÓGICA DE ENVÍO ---
    prompt = audio_text if audio_text else st.chat_input("Escribí acá...")

    if prompt:
        if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        if random.random() > 0.7: st.toast(random.choice(FRASES_FOMO), icon='🔥')

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Calculando..."):
                try:
                    resp = st.session_state.chat_session.send_message(prompt).text
                    news = parsear_ordenes_bot(resp)
                    
                    display = re.sub(r'\[ADD:.*?\]', '', resp)
                    st.markdown(display)
                    
                    if news:
                        st.caption("✅ Agregado al pedido")
                        st.dataframe(pd.DataFrame(news)[['cantidad','producto','precio_unit']], hide_index=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    log_interaction(prompt, total_final)
                    
                    if news: time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    if not st.session_state.cart:
        st.info("Carrito vacío. Volvé a 'COTIZAR' para agregar cosas.")
    else:
        for i, item in enumerate(st.session_state.cart):
            st.markdown(f"""
            <div style="background:white; border:1px solid #ddd; border-radius:10px; padding:10px; margin-bottom:8px;">
                <div style="font-weight:bold;">{item['cantidad']}x {item['producto']}</div>
                <div style="display:flex; justify-content:space-between; color:#555;">
                    <span>Unit: ${item['precio_unit']:,.0f}</span>
                    <span style="font-weight:bold; color:#0f2c59; font-size:1.1rem;">${item['subtotal']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"🗑️ Quitar {i+1}", key=f"d{i}"): st.session_state.cart.pop(i); st.rerun()

        st.divider()
        st.metric("TOTAL FINAL (+IVA)", f"${total_final:,.0f}")
        st.markdown(f"""<a href="{generar_link_wa(total_final)}" target="_blank" style="display:block; width:100%; background-color:#25D366; color:white; text-align:center; padding:15px; border-radius:50px; text-decoration:none; font-weight:bold; font-size:1.2rem; box-shadow: 0 4px 15px rgba(37,211,102,0.4);">✅ CONFIRMAR WHATSAPP</a>""", unsafe_allow_html=True)
        st.write("")
        if st.button("🗑️ VACIAR TODO", type="primary"): st.session_state.cart = []; st.rerun()

if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
