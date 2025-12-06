import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import random
import time

# ==========================================
# 1. CONFIGURACIÓN ESTRATÉGICA
# ==========================================
DOLAR_BNA_REF = 1060.00
MONTO_OBJETIVO_MAYORISTA = 300000  # Meta para el 15% OFF

# Frases de "Presión Social" estilo Temu
FRASES_FOMO = [
    "🔥 Un cliente de Rafaela acaba de pedir este material.",
    "⚠️ Stock crítico: Quedan pocas unidades en galpón 2.",
    "👀 3 personas están cotizando esto ahora mismo.",
    "⚡ El precio del dólar podría actualizarse en 1 hora.",
    "🚚 Camión saliendo para El Trébol esta tarde."
]

st.set_page_config(page_title="Pedro Bravin S.A.", page_icon="🏗️", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. ESTILOS VISUALES (EFECTO TEMU)
# ==========================================
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 130px !important; padding-bottom: 120px !important; }
    
    /* Header Fijo */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%; background: #ffffff;
        border-bottom: 1px solid #e0e0e0; z-index: 99999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    /* Barra Superior Marca */
    .top-bar {
        padding: 10px 20px; display: flex; justify-content: space-between; align-items: center;
        background: #0f2c59; color: white;
    }
    
    /* BARRA DE PROGRESO "TEMU" */
    .progress-container {
        padding: 10px 20px; background: #fff5e6; /* Fondo naranjita suave */
    }
    .progress-label {
        font-size: 0.85rem; font-weight: 700; color: #e65100; margin-bottom: 5px;
        display: flex; justify-content: space-between;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #ff9800, #ff5722) !important; /* Gradiente Naranja Agresivo */
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
    
    /* Tarjeta Cierre */
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
# 3. LÓGICA DE NEGOCIO Y ESTADO
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
    except: return ""

csv_context = load_data()

# Inicialización de Estado
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "⚡ **¡Bienvenido a Pedro Bravin S.A.!**\n\nSoy Miguel. Decime qué necesitás y te busco el mejor precio YA."}]
if "monto_acumulado" not in st.session_state:
    st.session_state.monto_acumulado = 0.0

# Función para extraer precio de la respuesta del bot
def extraer_monto(texto):
    # Busca patrones como $150.000, $ 150.000, $150000
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = []
    for p in patrones:
        clean = p.replace('.', '')
        if clean.isdigit():
            montos.append(int(clean))
    if montos:
        return max(montos) # Asumimos que el monto mayor es el total o el item principal
    return 0

# ==========================================
# 4. RENDERIZADO DEL HEADER (BARRA TEMU)
# ==========================================
porcentaje = min(st.session_state.monto_acumulado / MONTO_OBJETIVO_MAYORISTA, 1.0)
falta = max(MONTO_OBJETIVO_MAYORISTA - st.session_state.monto_acumulado, 0)

html_header = f"""
<div class="fixed-header">
    <div class="top-bar">
        <span><i class="fa-solid fa-bolt"></i> PEDRO BRAVIN S.A.</span>
        <span style="font-size: 0.8rem; opacity: 0.8;">Dólar BNA: ${DOLAR_BNA_REF}</span>
    </div>
    <div class="progress-container">
        <div class="progress-label">
            <span>🚀 TARIFA MAYORISTA (15% OFF)</span>
            <span>{'🎉 ¡ALCANZADO!' if falta == 0 else f'Faltan ${falta:,.0f}'}</span>
        </div>
    </div>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)
# Renderizamos la barra nativa de Streamlit justo debajo del HTML inyectado
# Usamos un container vacío arriba para "empujar" el contenido si fuera necesario, 
# pero como el header es fixed, usamos st.progress aquí.
st.progress(porcentaje)


# ==========================================
# 5. CEREBRO DE VENTAS (MIGUEL)
# ==========================================
sys_prompt = f"""
ROL: Eres Miguel, Cotizador AGRESIVO de Pedro Bravin S.A.
BASE DE DATOS: {csv_context}
OBJETIVO: CERRAR YA. USAR ESCALERA DE VALOR.

INSTRUCCIONES CLAVE:
1. Respuestas CORTAS (Bullets).
2. Extrae precios de la lista y siempre suma "+ IVA".
3. SIEMPRE menciona cuánto falta para llegar a ${MONTO_OBJETIVO_MAYORISTA} si el monto es menor.
   Ej: "Te faltan $50.000 para el descuento mayorista. ¿Sumamos electrodos?".
4. Si pasa los ${MONTO_OBJETIVO_MAYORISTA}, GRITA: "¡DESCUENTO MAYORISTA ACTIVADO!".

FORMATO CIERRE:
[TEXTO_WHATSAPP]:
Hola Martín, quiero CONGELAR STOCK.
💰 Monto Aprox: $[Monto]
🎁 Descuento: [{'SI (15%)' if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA else 'NO'}]
"""

try:
    if "chat_session" not in st.session_state or st.session_state.chat_session is None:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
except: pass

# ==========================================
# 6. INTERFAZ DE CHAT
# ==========================================

# Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Input
if prompt := st.chat_input("Ej: 20 chapas T101, Perfiles C..."):
    # 1. Globito Random (Social Proof) antes de responder
    if random.random() > 0.5:
        msg_fomo = random.choice(FRASES_FOMO)
        st.toast(msg_fomo, icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Calculando descuento..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # ACTUALIZAR BARRA DE PROGRESO
                nuevo_monto = extraer_monto(full_text)
                if nuevo_monto > 0:
                    # Actualizamos el monto. Podrías hacerlo acumulativo sumando, 
                    # pero por simplicidad de chat tomamos el valor del pedido actual.
                    # Si quieres acumulativo: st.session_state.monto_acumulado += nuevo_monto
                    st.session_state.monto_acumulado = nuevo_monto 
                    
                # Si llegamos a la meta, fiesta
                if st.session_state.monto_acumulado >= MONTO_OBJETIVO_MAYORISTA:
                    st.balloons()
                    st.toast("🎉 ¡DESCUENTO MAYORISTA DESBLOQUEADO!", icon="💰")

                # RENDERIZADO RESPUESTA
                if "[TEXTO_WHATSAPP]:" in full_text:
                    display_text, wa_text = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_text.strip())}"
                    
                    # TARJETA FINAL VIBRANTE
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="final-action-card">
                        🚀 ¡RESERVAR PRECIO CON MARTÍN! <br>
                        <span style="font-size:0.9rem;">Antes que se agote el stock</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    
                # Forzar recarga para actualizar la barra superior visualmente
                time.sleep(0.5)
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# Botón Flotante WhatsApp (Siempre visible abajo a la derecha)
st.markdown("""
<a href="https://wa.me/5493401527780" class="wa-float" target="_blank">
    <i class="fa-brands fa-whatsapp"></i>
</a>
""", unsafe_allow_html=True)
