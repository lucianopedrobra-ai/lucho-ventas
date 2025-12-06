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
# 1. CONFIGURACIÓN DEL NEGOCIO (ESTRATÉGICA)
# ==========================================

# --- Analíticas (RECUPERADO) ---
# Pon aquí tus links reales de Google Forms
URL_FORM_GOOGLE = "" 
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- Variables de Venta ---
DOLAR_BNA_REF = 1060.00
MONTO_OBJETIVO_MAYORISTA = 300000  # Meta para el 15% OFF

# --- Lista Completa de Logística (RECUPERADO) ---
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE,
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- Frases FOMO (Miedo a perderse algo) ---
FRASES_FOMO = [
    "🔥 Un cliente de Rafaela acaba de pedir este material.",
    "⚠️ Stock crítico: Quedan pocas unidades en galpón 2.",
    "👀 3 personas están cotizando esto ahora mismo.",
    "⚡ El precio del dólar podría actualizarse en 1 hora.",
    "🚚 Camión saliendo para zona sur esta tarde."
]

# ==========================================
# 2. FUNCIONES DE FONDO (BACKEND)
# ==========================================

# Hilo de Métricas en Background (RECUPERADO)
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
        except:
            pass 

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
    
    # Enviar al form en un hilo separado para no trabar el chat
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True 
    thread.start()

def extraer_monto(texto):
    """Extrae el precio más alto mencionado en el texto para la barra de progreso"""
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = []
    for p in patrones:
        clean = p.replace('.', '')
        if clean.isdigit():
            montos.append(int(clean))
    if montos:
        return max(montos)
    return 0

# ==========================================
# 3. INTERFAZ VISUAL (ESTILO TEMU)
# ==========================================
st.set_page_config(page_title="Pedro Bravin S.A.", page_icon="🏗️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 130px !important; padding-bottom: 120px !important; }
    
    /* Header Fijo con Barra de Progreso */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%; background: #ffffff;
        border-bottom: 1px solid #e0e0e0; z-index: 99999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .top-bar {
        padding: 10px 20px; display: flex; justify-content: space-between; align-items: center;
        background: #0f2c59; color: white;
    }
    
    .progress-container {
        padding: 10px 20px; background: #fff5e6;
    }
    .progress-label {
        font-size: 0.85rem; font-weight: 700; color: #e65100; margin-bottom: 5px;
        display: flex; justify-content: space-between;
    }
    
    /* Color de la barra de carga (Naranja agresivo) */
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
# 4. SISTEMA TÉCNICO & DATOS
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Error API Key. Revisa secrets.")
    st.stop()

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except: return ""

csv_context = load_data()

# Estado Inicial
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "⚡ **¡Bienvenido!**\n\nSoy Miguel. El stock está volátil hoy. ¿Qué necesitás cotizar?"}]
if "monto_acumulado" not in st.session_state:
    st.session_state.monto_acumulado = 0.0

# ==========================================
# 5. RENDERIZADO CABECERA (LÓGICA TEMU)
# ==========================================
porcentaje = min(st.session_state.monto_acumulado / MONTO_OBJETIVO_MAYORISTA, 1.0)
falta = max(MONTO_OBJETIVO_MAYORISTA - st.session_state.monto_acumulado, 0)

# HTML inyectado
html_header = f"""
<div class="fixed-header">
    <div class="top-bar">
        <span><i class="fa-solid fa-bolt"></i> PEDRO BRAVIN S.A. | VENTA ONLINE</span>
        <span style="font-size: 0.8rem; opacity: 0.9;">Dólar: ${DOLAR_BNA_REF}</span>
    </div>
    <div class="progress-container">
        <div class="progress-label">
            <span>🚀 TARIFA MAYORISTA (15% OFF)</span>
            <span>{'🎉 ¡OBJETIVO LOGRADO!' if falta == 0 else f'Faltan ${falta:,.0f} para activar dcto.'}</span>
        </div>
    </div>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)
st.progress(porcentaje)

# ==========================================
# 6. CEREBRO IA (MIGUEL + REGLAS RECUPERADAS)
# ==========================================
sys_prompt = f"""
ROL: Eres Miguel, Asesor Técnico y Vendedor Agresivo de Pedro Bravin S.A.
BASE DE DATOS: {csv_context}
VARIABLES: DÓLAR BNA ${DOLAR_BNA_REF}
ZONA GRATIS: {CIUDADES_GRATIS}

OBJETIVO: VENDER RÁPIDO. USAR ESCALERA DE VALOR PARA LLEGAR A ${MONTO_OBJETIVO_MAYORISTA}.

📜 REGLAS OBLIGATORIAS:
1. **PRECIO:** Siempre extrae del CSV y di "$ PRECIO + IVA".
2. **LOGÍSTICA:**
   - Si la ciudad está en ZONA GRATIS -> "¡Flete BONIFICADO a tu localidad! (Ahorrás $$$)".
   - Si NO está -> "Calculo el envío más económico desde planta".
3. **UP-SELLING (La Barra):**
   - Siempre calcula mentalmente cuánto falta para ${MONTO_OBJETIVO_MAYORISTA}.
   - Di: "Estás a $X de desbloquear el PRECIO MAYORISTA (-15%). ¿Agregamos discos o tornillos?".
4. **URGENCIA:** Usa frases cortas. "Stock bajo", "Precio por hoy".

FORMATO SALIDA FINAL (PARA WHATSAPP):
[TEXTO_WHATSAPP]:
Hola Martín, quiero CONGELAR PRECIO YA.
📦 Pedido: [Resumen]
📍 Destino: [Ciudad detectada]
💰 Total Aprox: $[Monto] + IVA
🎁 Estado Mayorista: [{'✅ ACTIVADO' if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA else '❌ Falta poco'}]
Enviame link de pago.
"""

try:
    if "chat_session" not in st.session_state or st.session_state.chat_session is None:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
except: pass

# ==========================================
# 7. CHAT Y LÓGICA DE EVENTOS
# ==========================================

# Panel Admin (RECUPERADO)
if prompt := st.chat_input("Ej: 20 chapas, Perfil C, Hierro del 8..."):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

# Mostrar Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Si hay input del usuario (procesamiento)
if prompt and prompt != "#admin-miguel":
    
    # 1. Social Proof (Globito Temu)
    if random.random() > 0.6:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Verificando stock y bonificaciones..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Detectar precio para la barra
                nuevo_monto = extraer_monto(full_text)
                if nuevo_monto > 0:
                    st.session_state.monto_acumulado = nuevo_monto # Opcional: += si quieres sumar items
                
                # Registrar Log (RECUPERADO)
                log_interaction(prompt, full_text, nuevo_monto)

                # Efectos visuales de éxito
                if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA:
                    st.balloons()
                    st.toast("🎉 ¡PRECIO MAYORISTA DESBLOQUEADO!", icon="💰")

                # Renderizar respuesta
                if "[TEXTO_WHATSAPP]:" in full_text:
                    display_text, wa_text = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_text.strip())}"
                    
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="final-action-card">
                        🔥 CONGELAR PRECIO Y STOCK <br>
                        <span style="font-size:0.9rem;">Hablar con Martín ahora</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                # Forzar actualización de barra visual
                time.sleep(0.5)
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# Botón WhatsApp Flotante
st.markdown("""
<a href="https://wa.me/5493401527780" class="wa-float" target="_blank">
    <i class="fa-brands fa-whatsapp"></i>
</a>
""", unsafe_allow_html=True)

# Panel Admin Visual
if st.session_state.admin_mode:
    with st.expander("🔐 PANEL ADMIN (Datos de Sesión)"):
        st.write(st.session_state.log_data)
        if st.button("Descargar Logs CSV"):
            df_logs = pd.DataFrame(st.session_state.log_data)
            st.download_button("Descargar", df_logs.to_csv(), "logs.csv")
