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

# ==========================================
# 1. CONFIGURACIÓN TÉCNICA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A. | Cotizador",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00

# --- LA ESCALERA DE VALOR (VISUAL) ---
# Esta es la meta visual general, pero Miguel tendrá reglas especiales para Chapas/Perfiles
NIVELES = [
    # Nivel Base: Mejorado al 5% para que sea atractivo de entrada
    {"techo": 500000,  "desc": 5,  "next_desc": 10, "nombre": "INICIAL", "label_desc": "5% CONTADO", "color": "#78909c"}, 
    {"techo": 1500000, "desc": 10, "next_desc": 15, "nombre": "OBRA", "label_desc": "10% OFF", "color": "#ffa726"}, 
    {"techo": 3000000, "desc": 15, "next_desc": 18, "nombre": "CONSTRUCTOR", "label_desc": "15% OFF", "color": "#d50000"}, 
    {"techo": float('inf'), "desc": 18, "next_desc": 18, "nombre": "PARTNER", "label_desc": "18% MAX", "color": "#6200ea"} 
]

# --- INFRAESTRUCTURA DE DATOS ---
URL_FORM_GOOGLE = ""  # 🔴 PEGAR LINK DE GOOGLE FORMS
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE,
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

FRASES_FOMO = [
    "🔥 Chapas T101: Precio especial por cierre de lote.",
    "⚠️ Hierro Construcción: Stock con alta rotación hoy.",
    "👀 Perfiles C: 3 clientes están consultando stock ahora.",
    "📉 Dólar BNA estable: Aprovechá para congelar precio.",
    "🚚 Logística: Armado de reparto para zona centro."
]

# ==========================================
# 2. MOTOR DE BACKEND
# ==========================================
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "monto_acumulado" not in st.session_state: st.session_state.monto_acumulado = 0.0
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "🏗️ **Bienvenido a Pedro Bravin S.A.**\n\nSoy Miguel. Tengo **tarifas especiales** en Chapas, Perfiles y Hierros.\n¿Qué materiales cotizamos?"}]

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {ID_CAMPO_CLIENTE: str(cliente), ID_CAMPO_MONTO: str(monto), ID_CAMPO_OPORTUNIDAD: str(oportunidad)}
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except: pass

def log_interaction(user_text, bot_response, monto_detectado):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "BAJA"
    if monto_detectado > 1500000: opportunity = "🔥 ALTA (CONSTRUCTOR)"
    elif monto_detectado > 500000: opportunity = "MEDIA (OBRA)"
    
    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto": monto_detectado})
    
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True
    thread.start()

def extraer_monto(texto):
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = [int(p.replace('.', '')) for p in patrones if p.replace('.', '').isdigit()]
    return max(montos) if montos else 0

def obtener_nivel_actual(monto):
    for nivel in NIVELES:
        if monto < nivel["techo"]: return nivel
    return NIVELES[-1]

# ==========================================
# 3. INTERFAZ VISUAL (BARRA DINÁMICA)
# ==========================================
nivel_actual = obtener_nivel_actual(st.session_state.monto_acumulado)
meta = nivel_actual["techo"]
label_descuento = nivel_actual["label_desc"]
siguiente_descuento = nivel_actual["next_desc"]
color_barra = nivel_actual["color"]

base_nivel_anterior = 0
for i, n in enumerate(NIVELES):
    if n == nivel_actual and i > 0:
        base_nivel_anterior = NIVELES[i-1]["techo"]
        break

if meta == float('inf'):
    porcentaje = 100
    texto_meta = "🏆 ¡MEJOR PRECIO DEL MERCADO!"
    falta = 0
else:
    rango = meta - base_nivel_anterior
    progreso_en_rango = st.session_state.monto_acumulado - base_nivel_anterior
    porcentaje = min(max(progreso_en_rango / rango, 0), 1) * 100
    falta = meta - st.session_state.monto_acumulado
    texto_meta = f"Faltan ${falta:,.0f} para {siguiente_descuento}% OFF"

st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 165px !important; padding-bottom: 120px !important; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: white; z-index: 99999;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }}
    .top-strip {{
        background: #0f2c59; color: white; padding: 8px 15px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.8rem;
    }}
    .legal-text {{ color: #ffeb3b; font-weight: 600; font-size: 0.7rem; }}
    
    /* BARRA DE PROGRESO */
    .game-zone {{ padding: 10px 20px; background: #fafafa; border-bottom: 1px solid #eee; }}
    .level-info {{ display: flex; justify-content: space-between; margin-bottom: 5px; align-items: center; }}
    .current-badge {{ 
        background: #37474f; color: white; padding: 4px 10px; border-radius: 12px; 
        font-size: 0.75rem; font-weight: bold; border: 1px solid #cfd8dc;
    }}
    .next-target {{ color: {color_barra}; font-weight: 800; font-size: 0.9rem; }}
    .custom-progress-bg {{ width: 100%; height: 14px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }}
    .custom-progress-fill {{
        height: 100%; width: {porcentaje}%; 
        background: linear-gradient(90deg, {color_barra} 0%, {color_barra} 100%); 
        transition: width 0.6s ease-in-out;
        box-shadow: 0 0 10px {color_barra};
    }}
    
    .wa-float {{
        position: fixed; bottom: 90px; right: 20px;
        background: #25D366; color: white; width: 60px; height: 60px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 30px; box-shadow: 0 4px 15px rgba(37, 211, 102, 0.4);
        z-index: 9999; transition: transform 0.2s;
    }}
    .wa-float:hover {{ transform: scale(1.1); }}
    
    .closing-card {{
        background: linear-gradient(135deg, #d50000 0%, #b71c1c 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 900; font-size: 1.2rem; margin-top: 15px;
        box-shadow: 0 8px 25px rgba(213, 0, 0, 0.3);
        border: 2px solid #ff8a80; animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); }}
    }}
    .stChatMessage {{ border-radius: 15px !important; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>⚡ PEDRO BRAVIN S.A. | LIVE</span>
            <span class="legal-text">⚠️ Precios Web Estimados</span>
        </div>
        <div class="game-zone">
            <div class="level-info">
                <span class="current-badge">TU NIVEL: {label_descuento}</span>
                <span class="next-target">{texto_meta}</span>
            </div>
            <div class="custom-progress-bg">
                <div class="custom-progress-fill"></div>
            </div>
        </div>
    </div>
    
    <a href="https://wa.me/5493401527780" class="wa-float" target="_blank">
        <i class="fa-brands fa-whatsapp"></i>
    </a>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# ==========================================
# 4. CEREBRO IA (CON UPGRADE COMPETITIVO)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Error API Key.")
    st.stop()

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except: return "Error DB"

csv_context = load_data()

sys_prompt = f"""
ROL: Eres Miguel, el Asesor Estrella de Pedro Bravin S.A.
BASE DE DATOS: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

🔥 **PROTOCOLOS DE DESCUENTO:**

1.  **PRODUCTOS ESTRELLA (COMPETITIVOS):**
    * Si piden **CHAPAS DE TECHO**, **PERFILES C** o **HIERRO DE CONSTRUCCIÓN**:
    * ⚡ **UPGRADE AUTOMÁTICO:** Sé MUY agresivo. Ignora los niveles bajos.
    * Ofrece descuentos fuertes (10% al 15%) desde el inicio para ganar la venta.
    * *Argumento:* "En chapas y perfiles tengo el mejor precio de la zona garantizado".

2.  **PRODUCTOS ESTÁNDAR (ESCALA GENERAL):**
    * **$0 - $500k:** Ofrece **5% OFF (Pago Contado)**.
    * **$500k - $1.5M:** 10% OFF.
    * **$1.5M - $3M:** 15% OFF.
    * **+$3M:** 18% OFF (Partner).

3.  **TÁCTICA DE CIERRE:**
    * **Precio:** Siempre di "$ Precio + IVA".
    * **Escasez:** "Queda poco stock de este lote".
    * **Logística:** Si es zona gratis, grítalo: "¡Flete BONIFICADO!".

FORMATO SALIDA WHATSAPP:
[TEXTO_WHATSAPP]:
Hola Martín, CONGELAR STOCK.
📦 Pedido: [Items]
📍 Localidad: [Ciudad]
💰 Total Aprox: $[Monto] + IVA
💎 Descuento Aplicado: [{label_descuento} o 'ESPECIAL COMPETITIVO']
Link de pago por favor.
"""

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
    except: pass

# ==========================================
# 5. CHAT Y PROCESAMIENTO
# ==========================================

# Renderizado Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Input Usuario
if prompt := st.chat_input("Ej: 20 Chapas C25 y Perfiles C..."):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

    if random.random() > 0.6:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Analizando descuentos especiales..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                nuevo_monto = extraer_monto(full_text)
                if nuevo_monto > 0: st.session_state.monto_acumulado = nuevo_monto
                
                log_interaction(prompt, full_text, nuevo_monto)

                if st.session_state.monto_acumulado > 1000000:
                    st.balloons() # Solo festeja ventas grandes
                    st.toast("🚀 ¡PRECIO MAYORISTA DETECTADO!", icon="💰")

                if "[TEXTO_WHATSAPP]:" in full_text:
                    display, wa_msg = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(display)
                    st.session_state.messages.append({"role": "assistant", "content": display})
                    
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_msg.strip())}"
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="closing-card">
                        🔥 ASEGURAR PRECIO Y STOCK <br>
                        <span style="font-size:0.9rem; font-weight:400; opacity:0.9;">Antes del cambio de lista</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                time.sleep(0.5)
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# Panel Admin
if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN PANEL"):
        if st.session_state.log_data:
            st.dataframe(pd.DataFrame(st.session_state.log_data))
