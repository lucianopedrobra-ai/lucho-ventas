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

# INTENTO DE IMPORTAR MICROFONO (Sino, no rompe la app)
try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

# ==========================================
# 1. CONFIGURACIÓN E INFRAESTRUCTURA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES DE NEGOCIO ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"

# --- CONEXIÓN REAL GOOGLE SHEETS ---
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

# --- LOGS GOOGLE FORMS ---
URL_FORM_GOOGLE = "" # 🔴 PEGAR LINK AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- ZONA DE BENEFICIO LOGÍSTICO ---
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
# 2. GESTIÓN DE ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\nCotizo aceros directo de fábrica. Hablame, escribí o subí foto."}]

# ==========================================
# 3. BACKEND (LÓGICA)
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except Exception as e: return "Error DB: " + str(e)

csv_context = load_data()

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(cliente), 
                ID_CAMPO_MONTO: str(monto), 
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }, timeout=2)
        except: pass

def log_interaction(user_text, monto_real_carrito):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "BAJA"
    if monto_real_carrito > 1500000: opportunity = "🔥 ALTA"
    elif monto_real_carrito > 500000: opportunity = "MEDIA"
    
    st.session_state.log_data.append({
        "Fecha": timestamp, "Usuario": user_text[:50], 
        "Oportunidad": opportunity, "Monto": monto_real_carrito
    })
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_real_carrito, opportunity))
    thread.daemon = True
    thread.start()

def parsear_ordenes_bot(texto_respuesta):
    patron = r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto_respuesta)
    items_agregados = []
    
    for cant, prod, precio, tipo in coincidencias:
        item = {
            "cantidad": float(cant), 
            "producto": prod.strip(),
            "precio_unit": float(precio), 
            "subtotal": float(cant) * float(precio),
            "tipo": tipo.strip().upper()
        }
        st.session_state.cart.append(item)
        items_agregados.append(item)
    return items_agregados

def calcular_negocio():
    bruto = sum(item['subtotal'] for item in st.session_state.cart)
    descuento = 3
    color = "#546e7a" 
    texto_nivel = "INICIAL"
    
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart)
    
    if tiene_gancho:
        descuento = 15; texto_nivel = "🔥 MAYORISTA"; color = "#d32f2f" 
    elif bruto > 3000000:
        descuento = 15; texto_nivel = "👑 PARTNER"; color = "#6200ea" 
    elif bruto > 1500000:
        descuento = 10; texto_nivel = "🏗️ OBRA"; color = "#f57c00" 
        
    neto = bruto * (1 - (descuento/100))
    return bruto, neto, descuento, color, texto_nivel

def generar_link_whatsapp(total):
    texto = "Hola Martín, quiero CONGELAR este pedido:\n"
    for item in st.session_state.cart:
        texto += f"▪ {item['cantidad']}x {item['producto']}\n"
    texto += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    texto += f"\n(Condición: {CONDICION_PAGO})"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(texto)}"

# ==========================================
# 4. UI: HEADER FIJO (App Style)
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
porcentaje_barra = min(total_final / 3000000 * 100, 100) if total_final < 3000000 else 100
link_wa_float = generar_link_whatsapp(total_final)

st.markdown(f"""
    <style>
    /* Ocultar elementos nativos */
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 130px !important; padding-bottom: 90px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} /* OCULTAMOS SIDEBAR NATIVA */
    
    /* PESTAÑAS (Tabs) ESTILO APP */
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 80px; left: 0; width: 100%;
        background: white; z-index: 9999;
        display: flex; justify-content: space-around;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }}
    .stTabs [data-baseweb="tab"] {{
        flex: 1; text-align: center; padding: 10px; font-weight: bold;
    }}
    
    /* HEADER FIJO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: white; z-index: 10000;
        border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{
        background: #232f3e; color: white; padding: 6px 15px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.7rem;
    }}
    .cart-summary {{
        padding: 8px 15px; display: flex; justify-content: space-between; align-items: center;
    }}
    .price-tag {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
    .badge {{ 
        background: {color_barra}; color: white; padding: 3px 8px; 
        border-radius: 10px; font-size: 0.7rem; font-weight: bold; 
    }}
    .warning-text {{
        color: #ffeb3b; font-weight: bold; font-size: 0.65rem;
        animation: pulse-yellow 2s infinite;
    }}
    @keyframes pulse-yellow {{
        0% {{ opacity: 0.8; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.8; }}
    }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>PEDRO BRAVIN S.A.</span>
            <span class="warning-text">⚠️ PRECIOS ESTIMADOS IA</span>
        </div>
        <div class="cart-summary">
            <div><span class="badge">{nombre_nivel} {desc_actual}% OFF</span></div>
            <div class="price-tag">${total_final:,.0f} <span style="font-size:0.7rem; color:#666;">+IVA</span></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 5. CEREBRO IA (REGLAS INMUTABLES)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("⚠️ FALTA API KEY")

sys_prompt = f"""
ROL: Miguel, vendedor técnico Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

📜 REGLAS DE NEGOCIO INMUTABLES (DO NOT TOUCH):
1. **LARGOS COMERCIALES:**
   - 12.00 METROS: Perfiles C, Hierro Construcción, Lisos AL 220, UPN/IPN (>=80).
   - 6.40 METROS: Caños (Epoxi, Galv, Sched, Mec).
   - 6.00 METROS: Tubos Estructurales, Ángulos, Planchuelas.
2. **UNIDADES:** Clavos/Alambre=KG. Planchuelas/Mallas=UNIDAD. Alambres Agro=ROLLO.
3. **CHAPAS:** Acanalada=COD4. T101=COD6. Sin corte=Metro.
4. **LOGÍSTICA:**
   - ZONA BENEFICIO ({CIUDADES_GRATIS}): ¡OFRECE ENVÍO GRATIS!
   - RESTO: Calcula estimado (KM * 2 * {COSTO_FLETE_USD} * {DOLAR_BNA}). Resultado + IVA. 
   - RETIROS: "Retiro en Planta (A coordinar)".
5. **DISCLAIMER:** Precio estimado IA. Martín confirma final.

INSTRUCCIONES DE SALIDA:
- Sé breve.
- FORMATO COMANDO: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. APLICA REGLAS. Genera [ADD...]. SOLO CONFIRMA.", img]).text

# ==========================================
# 6. INTERFAZ DE PESTAÑAS (TABS) - MOBILE FRIENDLY
# ==========================================

# Creamos 2 Pestañas grandes
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])

# --- PESTAÑA 1: CHAT Y COTIZACIÓN ---
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.expander("📷 **SUBIR FOTO**", expanded=False):
            uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
            if uploaded_file and st.button("⚡ PROCESAR FOTO", type="primary"):
                with st.spinner("Analizando..."):
                    image = Image.open(uploaded_file)
                    full_text = procesar_vision(image)
                    if parsear_ordenes_bot(full_text):
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        log_interaction("FOTO SUBIDA", total_final)
                        st.rerun()
    with c2:
        if MIC_AVAILABLE:
            st.write("🎤 **HABLAR**")
            audio_text = speech_to_text(language='es', start_prompt="🔴", stop_prompt="⏹️", just_once=True, key='mic')
        else:
            # Si no está instalado, no mostramos error feo, solo un texto pequeño
            st.caption("🎙️ Mic no disponible")
            audio_text = None

    # Chat Historial
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', msg["content"])
            if clean.strip():
                st.chat_message(msg["role"], avatar="👷‍♂️" if msg["role"]=="assistant" else "👤").markdown(clean)

    # Input Usuario
    prompt = audio_text if audio_text else st.chat_input("Escribí tu pedido...")
    
    if prompt:
        if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        if random.random() > 0.7: st.toast(random.choice(FRASES_FOMO), icon='🔥')

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("..."):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    full_text = response.text
                    items_nuevos = parsear_ordenes_bot(full_text)
                    
                    display_text = re.sub(r'\[ADD:.*?\]', '', full_text)
                    st.markdown(display_text)
                    
                    if items_nuevos:
                        st.success(f"✅ Se agregaron {len(items_nuevos)} items al pedido.")
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    total_nuevo = sum(i['subtotal'] for i in st.session_state.cart) * (1 - (desc_actual/100))
                    log_interaction(prompt, total_nuevo)
                    
                    if items_nuevos: time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- PESTAÑA 2: CARRITO DETALLADO ---
with tab2:
    st.markdown("### 📋 Detalle del Acopio")
    if not st.session_state.cart:
        st.info("Tu carrito está vacío. Ve a la pestaña 'COTIZAR' para agregar materiales.")
    else:
        for i, item in enumerate(st.session_state.cart):
            # Tarjeta de producto estilo App
            st.markdown(f"""
            <div style="
                background-color: white; 
                border: 1px solid #e0e0e0; 
                border-radius: 10px; 
                padding: 15px; 
                margin-bottom: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:bold; font-size:1rem; color:#333;">{item['producto']}</div>
                    <div style="background:#eee; padding:2px 8px; border-radius:5px; font-size:0.8rem;">x{item['cantidad']}</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                    <div style="color:#666; font-size:0.9rem;">Unit: ${item['precio_unit']:,.0f}</div>
                    <div style="font-weight:bold; color:#0f2c59; font-size:1.1rem;">${item['subtotal']:,.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón eliminar nativo debajo de la tarjeta
            if st.button(f"🗑️ Quitar {item['producto']}", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()

        st.divider()
        
        # Resumen Final
        c_tot1, c_tot2 = st.columns(2)
        c_tot1.write("Subtotal Lista:")
        c_tot2.write(f"${sum(i['subtotal'] for i in st.session_state.cart):,.0f}")
        
        if desc_actual > 0:
            c_tot1.write(f"Descuento ({desc_actual}%):")
            c_tot2.write(f"-${sum(i['subtotal'] for i in st.session_state.cart) * (desc_actual/100):,.0f}")
            
        st.markdown(f"""
        <div style="background:{color_barra}; color:white; padding:15px; border-radius:10px; text-align:center; margin-top:10px;">
            <div style="font-size:0.9rem;">TOTAL FINAL (+IVA)</div>
            <div style="font-size:1.8rem; font-weight:bold;">${total_final:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        st.markdown(f"""
            <a href="{link_wa_float}" target="_blank" style="
                display:block; width:100%; background-color:#25D366; color:white; 
                text-align:center; padding:15px; border-radius:50px; 
                text-decoration:none; font-weight:bold; font-size:1.2rem;
                box-shadow: 0 4px 15px rgba(37,211,102,0.4);">
                ✅ CONFIRMAR POR WHATSAPP
            </a>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("🗑️ VACIAR TODO EL PEDIDO", type="secondary", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN"): st.dataframe(pd.DataFrame(st.session_state.log_data))
