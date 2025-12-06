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
    page_title="Pedro Bravin S.A. | Stock Vivo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00
MONTO_OBJETIVO_MAYORISTA = 300000  

# --- INFRAESTRUCTURA DE DATOS ---
URL_FORM_GOOGLE = ""  # 🔴 TU LINK DE GOOGLE FORMS
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- LISTA DE LOGÍSTICA ---
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE,
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- GATILLOS PSICOLÓGICOS ---
FRASES_FOMO = [
    "🔥 Alguien en Rafaela acaba de pedir 20 Chapas T101.",
    "⚠️ Stock Bajo: Quedan pocas unidades de este lote.",
    "👀 5 personas están viendo precios de Perfiles ahora.",
    "📉 El dólar está estable AHORA. Aprovechá antes del cierre.",
    "🚚 Camión saliendo para Zona Oeste esta tarde. ¡Sumate!"
]

# ==========================================
# 2. MOTOR DE BACKEND
# ==========================================

if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "monto_acumulado" not in st.session_state: st.session_state.monto_acumulado = 0.0
# Inicializar mensajes si no existen
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "⚡ **Sistema En Vivo.**\n\nEl stock está volando. ¿Qué necesitás cotizar YA?"}]

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {ID_CAMPO_CLIENTE: str(cliente), ID_CAMPO_MONTO: str(monto), ID_CAMPO_OPORTUNIDAD: str(oportunidad)}
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except: pass

def log_interaction(user_text, bot_response, monto_detectado):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "NORMAL"
    if monto_detectado > 300000: opportunity = "🔥 ALTA (MAYORISTA)"
    elif monto_detectado > 0: opportunity = "MEDIA (COTIZANDO)"

    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto": monto_detectado})
    
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True
    thread.start()

def extraer_monto(texto):
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = [int(p.replace('.', '')) for p in patrones if p.replace('.', '').isdigit()]
    return max(montos) if montos else 0

# ==========================================
# 3. INTERFAZ "TEMU STYLE"
# ==========================================

# Cálculo Barra
porcentaje = min(st.session_state.monto_acumulado / MONTO_OBJETIVO_MAYORISTA, 1.0) * 100
falta = max(MONTO_OBJETIVO_MAYORISTA - st.session_state.monto_acumulado, 0)
mensaje_barra = "🎉 ¡DESCUENTO MAYORISTA ACTIVADO!" if falta == 0 else f"Faltan ${falta:,.0f} para 15% OFF"
color_barra = "#00e676" if falta == 0 else "#ff9100" 

st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 160px !important; padding-bottom: 120px !important; }}
    
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
    
    .progress-wrapper {{ padding: 10px 20px; background: #fff8e1; border-bottom: 1px solid #ffe0b2; }}
    .progress-title {{ 
        display: flex; justify-content: space-between; font-weight: 800; 
        color: #e65100; font-size: 0.9rem; margin-bottom: 5px; text-transform: uppercase;
    }}
    .custom-progress-bg {{
        width: 100%; height: 12px; background: #e0e0e0; border-radius: 10px; overflow: hidden;
    }}
    .custom-progress-fill {{
        height: 100%; width: {porcentaje}%; 
        background: linear-gradient(90deg, #ff9800, #f57c00, {color_barra}); 
        transition: width 0.5s ease-in-out;
    }}
    
    .wa-float {{
        position: fixed; bottom: 90px; right: 20px;
        background: #25D366; color: white; width: 60px; height: 60px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 30px; box-shadow: 0 4px 15px rgba(37, 211, 102, 0.4);
        z-index: 9999; transition: transform 0.2s;
    }}
    .wa-float:hover {{ transform: scale(1.1) rotate(10deg); }}
    
    .closing-card {{
        background: linear-gradient(135deg, #d50000 0%, #c62828 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 900; font-size: 1.2rem; margin-top: 15px;
        box-shadow: 0 8px 25px rgba(213, 0, 0, 0.4);
        border: 2px solid #ff8a80; animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(213, 0, 0, 0.7); transform: scale(1); }}
        70% {{ box-shadow: 0 0 0 10px rgba(213, 0, 0, 0); transform: scale(1.02); }}
        100% {{ box-shadow: 0 0 0 0 rgba(213, 0, 0, 0); transform: scale(1); }}
    }}
    
    .stChatMessage {{ border-radius: 15px !important; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>⚡ PEDRO BRAVIN S.A. | LIVE</span>
            <span class="legal-text">⚠️ Precios est. (Web Parcial)</span>
        </div>
        <div class="progress-wrapper">
            <div class="progress-title">
                <span><i class="fa-solid fa-trophy"></i> Meta Mayorista</span>
                <span>{mensaje_barra}</span>
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
# 4. CEREBRO IA
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Sistema en Mantenimiento (API Key).")
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
ROL: Eres Miguel, el Mejor Vendedor de Pedro Bravin S.A.
BASE DE DATOS: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}
META: ${MONTO_OBJETIVO_MAYORISTA}

MISIÓN: CERRAR LA VENTA.
1. **PRECIO:** Siempre "+ IVA".
2. **ESCASEZ:** Usa frases como "Quedan pocos metros", "Precio congela hoy".
3. **LOGÍSTICA:** Si ZONA GRATIS -> "¡Flete BONIFICADO!".
4. **GAMIFICACIÓN:** Calcula cuánto falta para ${MONTO_OBJETIVO_MAYORISTA} y dilo.

FORMATO RESPUESTA FINAL:
[TEXTO_WHATSAPP]:
Hola Martín, quiero CONGELAR PRECIO Y STOCK.
📦 Pedido: [Items]
📍 Zona: [Ciudad]
💰 Total: $[Monto] + IVA
🏆 Nivel Mayorista: [{'✅ DESBLOQUEADO' if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA else '❌ Faltan items'}]
¡Pasame el CBU!
"""

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
    except: pass

# ==========================================
# 5. RENDERIZADO HISTORIAL (PRIMERO)
# ==========================================
# 🔥 CORRECCIÓN CLAVE: Renderizar mensajes ANTES de procesar input nuevo
# Esto asegura que el chat se vea siempre, incluso al recargar.
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# ==========================================
# 6. INPUT Y PROCESAMIENTO
# ==========================================
if prompt := st.chat_input("Ej: 20 Chapas C25 para El Trébol..."):
    # Admin Backdoor
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

    # 1. Globito FOMO (Solo si no es admin)
    if random.random() > 0.5:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    # 2. Agregar mensaje usuario a estado visual (inmediato)
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Dibujarlo manualmente para feedback instantáneo antes del rerun
    st.chat_message("user").markdown(prompt)
    
    # 3. Procesamiento IA
    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Verificando stock..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Análisis de Respuesta
                nuevo_monto = extraer_monto(full_text)
                if nuevo_monto > 0: st.session_state.monto_acumulado = nuevo_monto
                
                log_interaction(prompt, full_text, nuevo_monto)

                if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA:
                    st.balloons()
                    st.toast("🎉 ¡PRECIO MAYORISTA DESBLOQUEADO!", icon="💰")

                if "[TEXTO_WHATSAPP]:" in full_text:
                    display, wa_msg = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(display)
                    st.session_state.messages.append({"role": "assistant", "content": display})
                    
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_msg.strip())}"
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="closing-card">
                        🔥 ¡CONGELAR PRECIO AHORA! <br>
                        <span style="font-size:0.9rem; font-weight:400; opacity:0.9;">Antes que aumente o se agote</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})

                # Rerun para que la barra del header se actualice
                time.sleep(0.5) 
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# ==========================================
# 7. PANEL ADMIN
# ==========================================
if st.session_state.admin_mode:
    with st.expander("🔐 PANEL ADMIN"):
        st.write(st.session_state.log_data)
        if st.session_state.log_data:
            df = pd.DataFrame(st.session_state.log_data)
            st.download_button("Descargar CSV", df.to_csv(), "leads.csv")
