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
# 1. CONFIGURACIÓN VISUAL INICIAL
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.", 
    page_icon="🏗️", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. VARIABLES DE NEGOCIO Y BACKEND
# ==========================================

# --- Analíticas Silenciosas (Google Forms) ---
URL_FORM_GOOGLE = "" # Poner URL real aquí
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- Reglas de Venta ---
MONTO_OBJETIVO_MAYORISTA = 300000  # Meta para el 15% OFF
# (El Dólar BNA se mantiene interno si lo necesitas, pero oculto al usuario)
DOLAR_BNA_REF = 1060.00 

# --- Logística (Lista Completa) ---
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE,
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- Frases FOMO (Social Proof) ---
FRASES_FOMO = [
    "🔥 Un cliente de Rafaela acaba de pedir este material.",
    "⚠️ Stock crítico: Quedan pocas unidades en galpón.",
    "👀 3 personas están cotizando esto ahora mismo.",
    "🚚 Camión saliendo para zona sur esta tarde.",
    "⚡ Precios sujetos a modificación sin previo aviso."
]

# ==========================================
# 3. FUNCIONES TÉCNICAS
# ==========================================

# --- Logger a Google Forms ---
if "log_data" not in st.session_state:
    st.session_state.log_data = []
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {
                ID_CAMPO_CLIENTE: str(cliente),
                ID_CAMPO_MONTO: str(monto),
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=3)
        except: pass 

def log_interaction(user_text, bot_response, monto_detectado):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "NORMAL"
    
    if monto_detectado > 300000:
        opportunity = "🔥 ALTA (MAYORISTA)"
    elif monto_detectado > 0:
        opportunity = "MEDIA (COTIZANDO)"

    st.session_state.log_data.append({
        "Fecha": timestamp, 
        "Usuario": user_text[:50], 
        "Oportunidad": opportunity, 
        "Monto": monto_detectado
    })
    
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True 
    thread.start()

# --- Extractor de Precios para la Barra ---
def extraer_monto(texto):
    # Busca precios en el texto generado para actualizar la barra
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = []
    for p in patrones:
        clean = p.replace('.', '')
        if clean.isdigit():
            montos.append(int(clean))
    if montos:
        return max(montos)
    return 0

# --- Carga de Datos ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Error Crítico: API Key no configurada.")
    st.stop()

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except: return ""

csv_context = load_data()

# ==========================================
# 4. INTERFAZ Y ESTILOS (CSS)
# ==========================================
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 135px !important; padding-bottom: 120px !important; }
    
    /* Header Fijo */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%; background: #ffffff;
        border-bottom: 1px solid #e0e0e0; z-index: 99999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    /* Barra Superior Marca + DISCLAIMER */
    .top-bar {
        padding: 10px 20px; display: flex; justify-content: space-between; align-items: center;
        background: #0f2c59; color: white;
    }
    
    /* Estilo del Disclaimer */
    .legal-warning {
        font-size: 0.75rem; 
        color: #fff176; /* Amarillo suave */
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    
    /* Contenedor Barra Progreso */
    .progress-container {
        padding: 10px 20px; background: #fff5e6;
    }
    .progress-label {
        font-size: 0.85rem; font-weight: 700; color: #e65100; margin-bottom: 5px;
        display: flex; justify-content: space-between;
    }
    
    /* Gradiente Naranja Agresivo */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #ff9800, #ff5722) !important;
    }

    /* Botón Flotante WhatsApp */
    .wa-float {
        position: fixed; bottom: 90px; right: 20px;
        background-color: #25D366; color: white;
        padding: 15px; border-radius: 50%;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        z-index: 9999; font-size: 24px;
        transition: transform 0.2s;
    }
    .wa-float:hover { transform: scale(1.1); }
    
    /* Tarjeta Cierre Pulsante */
    .final-action-card {
        background: linear-gradient(135deg, #ff3d00 0%, #dd2c00 100%);
        color: white !important; text-align: center; padding: 15px; 
        border-radius: 8px; text-decoration: none; display: block;
        font-weight: 800; font-size: 1.1rem; margin-top: 10px;
        box-shadow: 0 4px 15px rgba(255, 61, 0, 0.4);
        border: 2px solid #fff; animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    """, unsafe_allow_html=True)

# ==========================================
# 5. RENDERIZADO DEL HEADER (LÓGICA TEMU)
# ==========================================
if "monto_acumulado" not in st.session_state:
    st.session_state.monto_acumulado = 0.0

porcentaje = min(st.session_state.monto_acumulado / MONTO_OBJETIVO_MAYORISTA, 1.0)
falta = max(MONTO_OBJETIVO_MAYORISTA - st.session_state.monto_acumulado, 0)

# HTML con el Disclaimer restaurado
html_header = f"""
<div class="fixed-header">
    <div class="top-bar">
        <span><i class="fa-solid fa-bolt"></i> PEDRO BRAVIN S.A.</span>
        <span class="legal-warning">⚠️ Precios y Stock estimados (Web Parcial)</span>
    </div>
    <div class="progress-container">
        <div class="progress-label">
            <span>🚀 TARIFA MAYORISTA (15% OFF)</span>
            <span>{'🎉 ¡OBJETIVO LOGRADO!' if falta == 0 else f'Faltan ${falta:,.0f}'}</span>
        </div>
    </div>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)
st.progress(porcentaje)

# ==========================================
# 6. CEREBRO IA (MIGUEL - EL CERRADOR)
# ==========================================
sys_prompt = f"""
ROL: Eres Miguel, Asesor Técnico y Vendedor de Pedro Bravin S.A.
BASE DE DATOS: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

OBJETIVO: Responder rápido, conciso y cerrar ventas.

📜 PROTOCOLO DE RESPUESTA:
1. **PRECIOS:** Siempre extrae del CSV y agrega "+ IVA".
2. **DISCLAIMER:** Si el producto no está exacto en CSV, aclara que es "A cotizar por Martín".
3. **LOGÍSTICA:**
   - Si la ciudad está en ZONA GRATIS -> "¡Logística BONIFICADA!".
   - Si no -> "Busco el flete más conveniente desde planta".
4. **EFECTO BARRA DE PROGRESO:**
   - Si el total es < {MONTO_OBJETIVO_MAYORISTA}, dile cuánto falta para el DESCUENTO MAYORISTA.
   - Usa listas (bullets) para que sea fácil de leer.

FORMATO SALIDA BOTÓN WHATSAPP:
[TEXTO_WHATSAPP]:
Hola Martín, quiero CONGELAR PRECIO.
📦 Pedido: [Resumen]
📍 Destino: [Ciudad]
💰 Aprox: $[Monto] + IVA
🎁 Descuento Mayorista: [{'✅ SÍ' if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA else '❌ Aún no'}]
Solicito link de pago.
"""

# Inicialización Chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "⚡ **Sistema Online.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

try:
    if "chat_session" not in st.session_state or st.session_state.chat_session is None:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
except: pass

# ==========================================
# 7. INTERACCIÓN Y RENDERIZADO
# ==========================================

# Panel Admin Backdoor
if prompt := st.chat_input("Escribe tu consulta aquí..."):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

# Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Procesamiento
if prompt and prompt != "#admin-miguel":
    
    # 1. Globito FOMO (Probabilidad 60%)
    if random.random() > 0.4:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Consultando stock en tiempo real..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Actualizar Barra
                nuevo_monto = extraer_monto(full_text)
                if nuevo_monto > 0:
                    st.session_state.monto_acumulado = nuevo_monto 
                
                # Logger
                log_interaction(prompt, full_text, nuevo_monto)

                # Efectos
                if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA:
                    st.balloons()
                    st.toast("🎉 ¡PRECIO MAYORISTA ALCANZADO!", icon="💰")

                # Respuesta + Botón WhatsApp
                if "[TEXTO_WHATSAPP]:" in full_text:
                    display_text, wa_text = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_text.strip())}"
                    
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="final-action-card">
                        🔥 CONGELAR PRECIO AHORA <br>
                        <span style="font-size:0.9rem;">Hablar con Martín antes del aumento</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                # Rerun para que la barra de arriba salte visualmente
                time.sleep(0.5)
                st.rerun()

    except Exception as e:
        st.error(f"Error de conexión: {e}")

# Botón Flotante
st.markdown("""
<a href="https://wa.me/5493401527780" class="wa-float" target="_blank">
    <i class="fa-brands fa-whatsapp"></i>
</a>
""", unsafe_allow_html=True)

# Panel Admin
if st.session_state.admin_mode:
    with st.expander("🔐 PANEL ADMIN - PEDRO BRAVIN S.A."):
        st.write(st.session_state.log_data)
        if st.session_state.log_data:
            df_logs = pd.DataFrame(st.session_state.log_data)
            st.download_button("Descargar CSV", df_logs.to_csv(), "ventas_miguel.csv")
