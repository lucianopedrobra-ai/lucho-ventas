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
URL_FORM_GOOGLE = ""  # Pega tu link aquí si lo tienes
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# ==========================================
# 2. INTERFAZ VISUAL (SOLUCIÓN MÓVIL ROBUSTA)
# ==========================================
st.markdown("""
    <style>
    /* RESET GLOBAL */
    header[data-testid="stHeader"] {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* FUENTES Y BASE */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* 1. HEADER FIJO SIMPLIFICADO */
    .fixed-header {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 55px;
        background-color: #ffffff;
        border-bottom: 1px solid #ddd;
        z-index: 99999; /* Por encima de todo */
        display: flex; justify-content: space-between; align-items: center;
        padding: 0 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .brand-box { line-height: 1.1; }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 14px; text-transform: uppercase; }
    .brand-sub { color: #666; font-size: 10px; }

    /* Botón WhatsApp Compacto */
    .wa-btn {
        background-color: #25D366; color: white !important;
        padding: 6px 12px; border-radius: 20px;
        font-weight: 600; font-size: 12px; text-decoration: none;
        display: flex; align-items: center; gap: 5px;
    }

    /* 2. ESPACIADO CRÍTICO PARA MÓVIL (PADDING) */
    /* Esto empuja el chat hacia arriba para que el teclado no tape el último mensaje */
    .block-container {
        padding-top: 70px !important;
        padding-bottom: 140px !important; 
    }

    /* 3. ESTILO DE MENSAJES */
    .stChatMessage { background-color: transparent; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { 
        background-color: #f4f6f9; 
        border-radius: 12px; 
        padding: 10px; 
    }

    /* 4. ARREGLO DEL INPUT (SOLUCIÓN DEFINITIVA) */
    /* Forzamos el contenedor del input para que tenga fondo blanco y borde */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border-top: 1px solid #e0e0e0 !important;
        padding-bottom: 15px !important; /* Espacio para gestos en iPhone */
        padding-top: 10px !important;
    }
    
    /* Forzamos el color del TEXTO a NEGRO (soluciona el texto invisible) */
    textarea[data-testid="stChatInputTextArea"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        caret-color: #000000 !important; /* Cursor negro */
        border: 1px solid #cccccc !important;
        border-radius: 20px !important;
    }
    
    /* Placeholder visible */
    textarea[data-testid="stChatInputTextArea"]::placeholder {
        color: #777777 !important;
        opacity: 1 !important;
    }

    /* 5. TARJETA DE CIERRE (CTA) */
    .cta-container {
        margin-top: 10px;
        text-align: center;
    }
    .cta-button {
        display: block;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important;
        padding: 12px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
        # Creamos una columna oculta con todo el texto en minúsculas para buscar rápido
        df['SEARCH_INDEX'] = df.astype(str).agg(' '.join, axis=1).str.lower()
        return df 
    except Exception:
        return None

raw_data = load_data()

# --- MOTOR DE BÚSQUEDA HÍBRIDO (Conserva datos, ahorra tokens) ---
def buscar_productos_inteligente(consulta, df, limite=50):
    """
    Filtra el DataFrame basándose en palabras clave.
    Garantiza que la IA reciba los datos exactos del CSV sin perder nada.
    """
    if df is None or df.empty: return ""
    
    palabras = consulta.lower().split()
    # Filtramos palabras muy cortas que pueden generar ruido (ej: "de", "el")
    palabras_clave = [p for p in palabras if len(p) > 2]
    
    if not palabras_clave:
        return "" # Si solo escribe "hola", no devolvemos datos (ahorra tokens)
    
    # Lógica: Si la fila contiene CUALQUIERA de las palabras clave.
    # Esto asegura que si escribe "chapa t101", traiga todo lo que diga chapa O t101.
    mask = df['SEARCH_INDEX'].apply(lambda x: any(p in x for p in palabras_clave))
    
    resultados = df[mask].head(limite)
    
    if resultados.empty:
        return ""
    
    # Devolvemos el CSV limpio (sin la columna de índice de búsqueda)
    return resultados.drop(columns=['SEARCH_INDEX'], errors='ignore').to_csv(index=False)

# --- Logging (Analíticas) ---
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False

def log_interaction(user_text, bot_response):
    # Lógica simplificada de logging
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Bot": bot_response[:50]})
        # Aquí iría el envío a Google Forms en background si se activa
    except: pass

# ==========================================
# 4. CEREBRO IA (PROMPT DINÁMICO)
# ==========================================
# El prompt base NO tiene los datos. Los datos se inyectan en cada turno.
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

# Renderizar mensajes
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Input del Usuario
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
                
                # 1. BÚSQUEDA HÍBRIDA (La clave del éxito)
                # Buscamos en Python primero
                stock_encontrado = buscar_productos_inteligente(prompt, raw_data)
                
                # 2. Construcción del Prompt "Just-in-Time"
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
                
                # 3. Envío a Gemini
                response_stream = chat.send_message(mensaje_final, stream=True)
            
            # Renderizado Streaming
            response_placeholder = st.empty()
            full_response = ""
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            log_interaction(prompt, full_response)
            
            # Botón WhatsApp
            if "[TEXTO_WHATSAPP]:" in full_response:
                dialogue, wa_part = full_response.split("[TEXTO_WHATSAPP]:", 1)
                
                # Limpieza visual
                response_placeholder.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                # Generación del Link
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
