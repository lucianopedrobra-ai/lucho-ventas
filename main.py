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
# 2. INTERFAZ VISUAL (UX DE ALTA GAMA)
# ==========================================
st.set_page_config(
    page_title="Asesor Comercial | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* Limpieza de interfaz */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }

    /* Header Flotante con Identidad */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ffffff; border-bottom: 1px solid #e0e0e0;
        padding: 10px 20px; z-index: 99999;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .header-branding { display: flex; flex-direction: column; }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 0.95rem; text-transform: uppercase; }
    .brand-disclaimer { color: #666; font-size: 0.75rem; }
    
    /* Botón WhatsApp en Header */
    .wa-pill-btn {
        background-color: #25D366; color: white !important;
        text-decoration: none; padding: 8px 16px; border-radius: 50px;
        font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2); transition: transform 0.2s;
    }
    .wa-pill-btn:hover { transform: scale(1.05); background-color: #1ebc57; }

    /* Padding principal para evitar que el contenido se oculte bajo el header */
    .block-container { padding-top: 85px !important; padding-bottom: 40px !important; }

    /* Estilos de Chat */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

    /* TARJETA DE CIERRE DE VENTA (CTA GIGANTE) */
    .final-action-card {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 700; font-size: 1.1rem; margin-top: 20px;
        box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        transition: transform 0.2s;
        border: 2px solid white;
    }
    .final-action-card:hover { transform: translateY(-3px); box-shadow: 0 15px 25px rgba(37, 211, 102, 0.4); }
    
    /* Spinner de carga personalizado */
    .stSpinner > div { border-top-color: #0f2c59 !important; }
    
    /* !!! CORRECCIÓN CRÍTICA FINAL PARA MÓVILES !!! */
    /* Este fix asegura que el historial de chat nunca sea tapado por el input fijo */
    @media (max-width: 800px) {
        .stApp {
            /* Forzamos un margen inferior extra grande, más seguro que 120px */
            padding-bottom: 140px !important; 
        }
        .stChatInput {
            height: 70px; /* Altura constante para el input */
        }
    }
    </style>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <div class="fixed-header">
        <div class="header-branding">
            <span class="brand-name">Miguel | Pedro Bravin S.A.</span>
            <span class="brand-disclaimer">⚠️ Precios y Stock estimados (Web Parcial)</span>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-pill-btn">
            <i class="fa-brands fa-whatsapp" style="font-size: 1.2rem;"></i>
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

# --- Carga de Datos Optimizada (Sanitización) ---
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

# --- Hilo de Métricas en Background ---
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
# 4. CEREBRO DE VENTAS (MIGUEL DEFINITIVO)
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

📜 **PROTOCOLOS DE ACTUACIÓN (TU CÓDIGO DE CONDUCTA):**

1.  **PRECIOS E IMPUESTOS:**
    * Todo precio del CSV es NETO.
    * **SIEMPRE** responde: "$ [Precio] + IVA".

2.  **LOGÍSTICA INTELIGENTE (El Argumento de Ahorro):**
    * Si es zona gratis -> "¡Logística Bonificada a tu zona!".
    * Si es lejos -> "Calculo envío desde nuestro nodo más cercano para que ahorres en flete".

3.  **VENTA CRUZADA (CROSS-SELLING HÍBRIDO):**
    * *Detecta la necesidad:* (Chapas -> Tornillos/Aislante) | (Perfiles -> Discos/Electrodos).
    * **CASO A (Está en lista):** "Tengo los tornillos en stock a $X. ¿Los sumo al pedido?".
    * **CASO B (No está en lista):** "Agrego los complementarios a la nota de pedido para que Martín los cotice a medida".

4.  **ESTRATEGIA DE DESCUENTOS (CIERRE):**
    * **$200.000 - $299.999:** "Estás muy cerca del descuento MAYORISTA (15% OFF). ¿Agregamos algo más?".
    * **Mayor a $300.000:** "¡Felicitaciones! **15% OFF MAYORISTA Activado**".

5.  **EL GANCHO FINAL:**
    * Ofrece siempre: **"Acopio 6 meses gratis"**.
    * Cierra con pregunta: "¿Te paso el link para congelar el precio?".

FORMATO SALIDA FINAL (PARA EL BOTÓN DE WHATSAPP):
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual (Miguel).
📍 Destino: [Localidad]
📋 Pedido Web:
- [Item] x [Cant]
⚠️ A Cotizar Manual (Sugerido IA):
- [Items complementarios sin precio en web]
💰 Inversión Aprox: $[Monto] + IVA
🎁 Beneficios: [Acopio / 15% OFF]
Solicito link de pago.
"""

# ==========================================
# 5. MOTOR DE CHAT & RENDERIZADO
# ==========================================

# Inicialización
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\n\nExperto en materiales de Pedro Bravin S.A.\n\n**¿Qué estás buscando cotizar hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        # GEMINI 2.5 PRO (NO SE TOCA, MÁXIMA POTENCIA)
        generation_config = {"temperature": 0.2, "max_output_tokens": 4096}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            # Fallback
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión. Recarga la página.")

# Renderizado de Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Input de Usuario
if prompt := st.chat_input("Ej: Necesito 20 chapas T101 para San Jorge..."):
    
    # --- PUERTA TRASERA ADMIN ---
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = True
        st.rerun()
    # ----------------------------

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            
            # 1. FEEDBACK VISUAL
            with st.spinner("Miguel está calculando costos y logística..."):
                try:
                    response_stream = chat.send_message(prompt, stream=True)
                except Exception:
                    st.error("Error de conexión. Intenta de nuevo.")
                    st.stop()

            # 2. STREAMING DE TEXTO
            response_placeholder = st.empty()
            full_response = ""
            
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
            # 3. PROCESAMIENTO POSTERIOR
            log_interaction(prompt, full_response)
            
            # 4. BOTÓN WHATSAPP INTELIGENTE
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
                <a href="{wa_url}" target="_blank" class="final-action-card">
                    🚀 FINALIZAR PEDIDO CON MARTÍN<br>
                    <span style="font-size:0.8rem; font-weight:400;">Enviar cotización detallada por WhatsApp</span>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Error inesperado: {e}")

# ==========================================
# 6. PANEL ADMIN OCULTO
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
        st.info("Sin datos en esta sesión.")
    if st.button("🔴 Cerrar Panel"):
        st.session_state.admin_mode = False
        st.rerun()
