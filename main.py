import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import datetime
import requests
import threading
import time

# ==========================================
# 1. CONFIGURACIÓN ESTRATÉGICA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Variables de Negocio ---
URL_FORM_GOOGLE = ""
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# ==========================================
# 2. INTERFAZ VISUAL (MÁXIMA VISIBILIDAD)
# ==========================================
st.markdown("""
    <style>
    /* GLOBAL RESET Y FONDO BLANCO FORZADO */
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 1. ANULACIÓN DE FONDO OSCURO EN CONTENEDORES RAÍZ */
    .stApp { background-color: white !important; }
    .stApp > header { visibility: hidden; }
    .main { background-color: white !important; }
    
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* 2. HEADER FIJO */
    .fixed-header {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 55px;
        background-color: #ffffff;
        border-bottom: 1px solid #ddd;
        z-index: 1000000;
        display: flex; justify-content: space-between; align-items: center;
        padding: 0 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .brand-box { line-height: 1.1; }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 14px; text-transform: uppercase; }
    .brand-sub { color: #666; font-size: 10px; }
    .wa-btn {
        background-color: #25D366; color: white !important;
        padding: 6px 12px; border-radius: 20px;
        font-weight: 600; font-size: 12px; text-decoration: none;
        display: flex; align-items: center; gap: 5px;
    }

    /* 3. ESPACIADO CRÍTICO PARA MÓVIL */
    .block-container {
        padding-top: 70px !important;
        padding-bottom: 140px !important; 
    }

    /* 4. ARREGLO DEL INPUT (EL MAYOR REFUERZO DE VISIBILIDAD) */
    
    /* Contenedor principal de la barra de chat (el que Streamlit fija al fondo) */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border-top: 1px solid #e0e0e0 !important;
        padding-bottom: 15px !important;
        padding-top: 10px !important;
        z-index: 9999999; /* Z-index EXTREMO para garantizar que no haya superposición */
    }
    
    /* El área de texto donde se escribe */
    textarea[data-testid="stChatInputTextArea"] {
        background-color: #ffffff !important;
        color: #000000 !important; /* Texto negro forzado */
        caret-color: #000000 !important; /* Cursor negro forzado */
        border: 1px solid #cccccc !important;
        border-radius: 20px !important;
        /* Aseguramos que el contenido del texto esté sobre el fondo */
        z-index: 10000000; 
    }
    
    /* Placeholder visible */
    textarea[data-testid="stChatInputTextArea"]::placeholder {
        color: #777777 !important;
        opacity: 1 !important;
    }

    /* 5. ESTILOS DE MENSAJES */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { 
        background-color: #f4f6f9; 
        border-radius: 12px; 
        padding: 10px; 
    }

    /* 6. CTA */
    .cta-container { margin-top: 10px; text-align: center; }
    .cta-button {
        display: block;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; padding: 12px; border-radius: 10px;
        text-decoration: none; font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>

    <div class="fixed-header">
        <div class="brand-box">
            <div class="brand-name">Miguel | Pedro Bravin S.A.</div>
            <div class="brand-sub">⚠️ Stock y Precios Estimados</div>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-btn">
            <span>Contactar</span>
        </a>
    </div>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND & LÓGICA DE BÚSQUEDA
# ==========================================

# --- API KEY ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Falta configurar la API Key en Secrets.")
    st.stop()

# --- Carga de Datos (Optimizado) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.dropna(how='all', axis=0)
        df = df.fillna("")
        df['SEARCH_INDEX'] = df.astype(str).agg(' '.join, axis=1).str.lower()
        return df 
    except Exception:
        return None

raw_data = load_data()

# --- MOTOR DE BÚSQUEDA HÍBRIDO ---
def buscar_productos_inteligente(consulta, df, limite=50):
    if df is None or df.empty: return ""
    palabras = consulta.lower().split()
    palabras_clave = [p for p in palabras if len(p) > 2]
    if not palabras_clave: return "" 
    mask = df['SEARCH_INDEX'].apply(lambda x: any(p in x for p in palabras_clave))
    resultados = df[mask].head(limite)
    if resultados.empty: return ""
    return resultados.drop(columns=['SEARCH_INDEX'], errors='ignore').to_csv(index=False)

# --- Logging (Analíticas) ---
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False

def log_interaction(user_text, bot_response):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Bot": bot_response[:50]})
    except: pass

# ==========================================
# 4. CEREBRO IA (PROMPT DINÁMICO)
# ==========================================
sys_prompt_base = f"""
ROL: Eres Miguel, Asesor Técnico de Pedro Bravin S.A.
TONO: Profesional, directo y orientado a la venta.
OBJETIVO: Usar el STOCK ADJUNTO para cotizar y cerrar ventas.

REGLAS DE ORO:
1. PRECIOS: Los precios del stock son NETOS. Suma siempre "+ IVA".
2. LOGÍSTICA: Zona gratis: {CIUDADES_GRATIS}. Resto: "Cotizamos envío desde nodo cercano".
3. DESCUENTOS: Si el total > $300.000 -> Ofrece 15% OFF MAYORISTA.
4. NO INVENTES: Si el producto no está en el STOCK ADJUNTO que te paso, di "No lo veo en stock rápido, déjame consultarlo con Martín".

FORMATO WHATSAPP (ÚSALO AL FINAL):
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual.
📍 Destino: [Ciudad]
📋 Interés: [Resumen]
💰 Presupuesto Aprox: $[Monto]
Solicito contacto.
"""

# ==========================================
# 5. CHAT ENGINE
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\n\nExperto en materiales de Pedro Bravin S.A.\n\n**¿Qué estás buscando hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt_base)
        st.session_state.chat_session = model.start_chat(history=[])
    except:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt_base)
            st.session_state.chat_session = model.start_chat(history=[])
        except: st.error("Error de conexión con la IA.")

for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Escribe aquí tu consulta..."):
    
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Buscando precios..."):
                
                stock_encontrado = buscar_productos_inteligente(prompt, raw_data)
                
                if stock_encontrado:
                    mensaje_final = f"""
                    DATOS DE STOCK ENCONTRADOS (Usa esto para responder):
                    {stock_encontrado}
                    PREGUNTA DEL CLIENTE: {prompt}
                    """
                else:
                    mensaje_final = f"""
                    NO ENCONTRÉ COINCIDENCIAS EXACTAS EN EL CSV.
                    Responde al cliente pidiendo más detalles o como asesor general.
                    PREGUNTA: {prompt}
                    """
                
                response_stream = chat.send_message(mensaje_final, stream=True)
            
            response_placeholder = st.empty()
            full_response = ""
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            log_interaction(prompt, full_response)
            
            if "[TEXTO_WHATSAPP]:" in full_response:
                dialogue, wa_part = full_response.split("[TEXTO_WHATSAPP]:", 1)
                
                response_placeholder.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <div class="cta-container">
                    <a href="{wa_url}" target="_blank" class="cta-button">
                        🚀 FINALIZAR PEDIDO EN WHATSAPP
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
                if "15%" in dialogue or "MAYORISTA" in dialogue:
                    st.toast('🎉 ¡Descuento Mayorista Activado!')
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")

# Panel Admin (Opcional)
if st.session_state.admin_mode:
    st.write("---")
    st.write("### Panel Admin")
    st.dataframe(pd.DataFrame(st.session_state.log_data))
    if st.button("Salir"):
        st.session_state.admin_mode = False
        st.rerun()
