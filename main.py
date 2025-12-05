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
# 1. CONFIGURACIÓN ESTRATÉGICA (BACKEND)
# ==========================================

# --- Analíticas Silenciosas (Google Forms) ---
URL_FORM_GOOGLE = ""  
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- Variables de Negocio (Reglas de Oro) ---
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# ==========================================
# 2. INTERFAZ VISUAL (OPTIMIZADA MOBILE)
# ==========================================
st.set_page_config(
    page_title="Asesor Comercial | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* 1. RESET GLOBAL */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }

    /* 2. HEADER FLOTANTE (ESTABLE) */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ffffff; 
        border-bottom: 1px solid #e0e0e0;
        padding: 10px 15px; 
        z-index: 1000000; /* Capa máxima */
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .brand-group { display: flex; flex-direction: column; }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 0.9rem; text-transform: uppercase; }
    .brand-sub { color: #666; font-size: 0.7rem; }

    /* Botón WhatsApp */
    .wa-btn {
        background-color: #25D366; color: white !important;
        text-decoration: none; padding: 6px 12px; border-radius: 50px;
        font-weight: 600; font-size: 0.8rem; display: flex; align-items: center; gap: 5px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2);
    }
    
    /* 3. AJUSTE DE CONTENEDOR (CRÍTICO PARA QUE NO SE TAPE NADA) */
    .block-container { 
        padding-top: 80px !important; 
        padding-bottom: 100px !important; /* Espacio para el input */
    }

    /* 4. CHAT Y MENSAJES */
    .stChatMessage { padding: 1rem !important; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

    /* 5. FIX DE INPUT (SOLUCIÓN "NO VEO LO QUE ESCRIBO") */
    /* No forzamos position:fixed al contenedor para no romper el teclado nativo del celular */
    .stChatInput {
        padding-bottom: 15px !important;
        background: transparent !important;
    }
    
    /* Forzamos colores dentro de la caja de texto */
    .stChatInput textarea {
        background-color: #ffffff !important; 
        color: #000000 !important;
        caret-color: #000000 !important; /* Color del cursor */
        border: 1px solid #ccc !important;
    }

    /* 6. RESPONSIVE (CELULARES) */
    @media (max-width: 600px) {
        .brand-name { font-size: 0.75rem; }
        .brand-sub { font-size: 0.6rem; }
        .wa-btn span { display: none; } /* Solo icono en móvil */
        .wa-btn::after { content: "WhatsApp"; font-size: 0.75rem; }
        
        /* Aumentamos padding inferior para seguridad con teclados iOS/Android */
        .block-container { padding-bottom: 140px !important; }
    }

    /* TARJETA FINAL CTA */
    .cta-card {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; text-align: center; padding: 15px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 700; margin-top: 15px;
        box-shadow: 0 8px 15px rgba(37, 211, 102, 0.3);
    }
    </style>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <div class="fixed-header">
        <div class="brand-group">
            <span class="brand-name">Miguel | Pedro Bravin S.A.</span>
            <span class="brand-sub">⚠️ Stock y Precios Estimados</span>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-btn">
            <i class="fa-brands fa-whatsapp"></i>
            <span>Hablar con Martín</span>
        </a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. SISTEMA TÉCNICO
# ==========================================

# --- Autenticación ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de API Key. Sistema en mantenimiento.")
    st.stop()

# --- Carga de Datos ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1) 
        df = df.dropna(how='all', axis=0)
        df = df.fillna("")
        return df 
    except Exception:
        return None

raw_data = load_data()

if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_csv(index=False)
    except Exception:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: Base de datos no accesible."

# --- Hilo de Métricas ---
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

def log_interaction(user_text, bot_response):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "NORMAL"
    monto_estimado = 0
    
    if "$" in bot_response:
        try:
            precios = [int(s.replace('.','')) for s in re.findall(r'\$([\d\.]+)', bot_response) if s.replace('.','').isdigit()]
            if precios:
                monto_estimado = max(precios)
                if monto_estimado > 300000:
                    opportunity = "🔥 ALTA (MAYORISTA)"
        except:
            pass

    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto Max": monto_estimado})
    
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_estimado, opportunity))
    thread.daemon = True 
    thread.start()

# ==========================================
# 4. CEREBRO DE VENTAS
# ==========================================
sys_prompt = f"""
ROL: Eres Miguel, Asesor Técnico y Experto en Cierre de Pedro Bravin S.A.
TONO: Profesional, resolutivo y comercialmente agresivo (pero amable).
OBJETIVO: Cotizar rápido, aplicar lógica logística y CERRAR el deal.

BASE DE DATOS (STOCK REAL):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS: DÓLAR BNA ${DOLAR_BNA_REF} | ZONA GRATIS: {CIUDADES_GRATIS}

📜 **PROTOCOLOS DE ACTUACIÓN:**

1.  **PRECIOS E IMPUESTOS:**
    * Todo precio del CSV es NETO.
    * **SIEMPRE** responde: "$ [Precio] + IVA".

2.  **LOGÍSTICA INTELIGENTE:**
    * Si es zona gratis -> "¡Logística Bonificada a tu zona!".
    * Si es lejos -> "Calculo envío desde nuestro nodo más cercano para que ahorres".

3.  **VENTA CRUZADA:**
    * "Tengo los tornillos/discos en stock. ¿Los sumo al pedido?".

4.  **ESTRATEGIA DE DESCUENTOS:**
    * **> $300.000:** "¡Felicitaciones! **15% OFF MAYORISTA Activado**".

5.  **EL GANCHO FINAL:**
    * Ofrece: **"Acopio 6 meses gratis"**.
    * "¿Te paso el link para congelar el precio?".

FORMATO SALIDA FINAL (PARA EL BOTÓN DE WHATSAPP):
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual (Miguel).
📍 Destino: [Localidad]
📋 Pedido Web:
- [Item] x [Cant]
⚠️ A Cotizar Manual:
- [Items sin precio]
💰 Inversión Aprox: $[Monto] + IVA
🎁 Beneficios: [Acopio / 15% OFF]
Solicito link de pago.
"""

# ==========================================
# 5. MOTOR DE CHAT
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\n\nExperto en materiales de Pedro Bravin S.A.\n\n**¿Qué estás buscando cotizar hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        generation_config = {"temperature": 0.2, "max_output_tokens": 4096}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión.")

for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: Necesito 20 chapas T101 para San Jorge..."):
    
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Miguel está calculando..."):
                try:
                    response_stream = chat.send_message(prompt, stream=True)
                except Exception:
                    st.error("Error de conexión.")
                    st.stop()

            response_placeholder = st.empty()
            full_response = ""
            
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            log_interaction(prompt, full_response)
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_response:
                dialogue, wa_part = full_response.split(WHATSAPP_TAG, 1)
                response_placeholder.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                if "15%" in dialogue or "MAYORISTA" in dialogue:
                    st.balloons()
                    st.toast('🎉 ¡Tarifa Mayorista (15% OFF) Activada!', icon='💰')
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="cta-card">
                    🚀 FINALIZAR PEDIDO CON MARTÍN<br>
                    <span style="font-size:0.8rem; font-weight:400;">Enviar cotización por WhatsApp</span>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Error inesperado: {e}")

# ==========================================
# 6. PANEL ADMIN
# ==========================================
if st.session_state.admin_mode:
    st.markdown("---")
    st.warning("🔐 ADMIN PANEL (MIGUEL)")
    if st.session_state.log_data:
        df_log = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df_log, use_container_width=True)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "metricas_miguel.csv", "text/csv")
    else:
        st.info("Sin datos.")
    if st.button("🔴 Cerrar Panel"):
        st.session_state.admin_mode = False
        st.rerun()
