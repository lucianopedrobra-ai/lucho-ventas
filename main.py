import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import datetime
import requests 

# --- 1. CONFIGURACIÓN DE ANALÍTICAS (GOOGLE FORMS) ---
# IMPORTANTE: Pon aquí el link de tu Google Form para que Google te mande el resumen por email.
URL_FORM_GOOGLE = ""  # Pega el link de acción del Form aquí
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- 2. VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 3. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Asesor Técnico | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }

    /* HEADER FLOTANTE */
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
    
    .wa-pill-btn {
        background-color: #25D366; color: white !important;
        text-decoration: none; padding: 8px 16px; border-radius: 50px;
        font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2); transition: transform 0.2s;
    }
    .wa-pill-btn:hover { transform: scale(1.05); background-color: #1ebc57; }

    .block-container { padding-top: 85px !important; padding-bottom: 40px !important; }

    /* CHAT ESTILO WHATSAPP */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

    /* TARJETA DE CIERRE DE VENTA */
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
    
    .stSpinner > div { border-top-color: #0f2c59 !important; }
    </style>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <div class="fixed-header">
        <div class="header-branding">
            <span class="brand-name">Lucho | Pedro Bravin S.A.</span>
            <span class="brand-disclaimer">⚠️ Precios y Stock estimados (Web Parcial)</span>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-pill-btn">
            <i class="fa-brands fa-whatsapp" style="font-size: 1.2rem;"></i>
            <span>Hablar con Martín</span>
        </a>
    </div>
    """, unsafe_allow_html=True)

# --- 4. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Sistema en mantenimiento.")
    st.stop()

# --- 5. CARGA DE DATOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.fillna("")
        return df 
    except Exception:
        return None

raw_data = load_data()

if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR CRÍTICO: Base de datos no accesible."

# --- 6. LOGS Y METRICAS ---
if "log_data" not in st.session_state:
    st.session_state.log_data = []

if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

def enviar_a_google_form(cliente, monto, oportunidad):
    """Envía los datos a Google Forms"""
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {
                ID_CAMPO_CLIENTE: str(cliente),
                ID_CAMPO_MONTO: str(monto),
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
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

    st.session_state.log_data.append({
        "Fecha": timestamp,
        "Usuario": user_text[:50],
        "Oportunidad": opportunity,
        "Monto Max": monto_estimado
    })
    
    enviar_a_google_form(user_text, monto_estimado, opportunity)

# --- 7. CEREBRO DE VENTAS ---
sys_prompt = f"""
ROL: Eres Lucho, **Asesor Técnico Virtual** y **Experto en Cierre** de **Pedro Bravin S.A.** (El Trébol, Santa Fe).
OBJETIVO: Cotizar EXCLUSIVAMENTE lo que hay en lista, calcular logística precisa y **CERRAR VENTAS**.

BASE DE DATOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR BNA: ${DOLAR_BNA_REF}
- ZONA GRATIS: {CIUDADES_GRATIS}

🚨 **REGLA IMPOSITIVA:** Precios CSV son NETOS. Siempre sumar "+ IVA".

🧠 **ESTRATEGIA COMERCIAL:**
1.  **LOGÍSTICA:** GRATIS si está en zona. Si no, cobrar flete desde nodo cercano y venderlo como "Ahorro".
2.  **GAMIFICACIÓN:**
    * $200k-$299k -> "Estás cerca del MAYORISTA (15% OFF). ¿Agregamos algo?".
    * >$300k -> "¡Tarifa MAYORISTA activada (15% OFF)!".
3.  **CIERRE:** Ofrece siempre **"Acopio 6 meses gratis"**. Termina con pregunta de cierre.

📝 **FORMATO SALIDA:**
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual.
📍 Destino: [Localidad]
📋 Pedido Web:
- [Items]
💰 Inversión Est: $[Monto] + IVA
🎁 Beneficios: [Acopio / 15% OFF]
Solicito link.
"""

# --- 8. SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Bienvenido a Pedro Bravin S.A.**\n\nSoy Lucho, tu asesor técnico.\n\n**¿Qué materiales necesitas cotizar hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión.")

# --- 9. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 20 chapas para San Jorge..."):
    # --- PUERTA TRASERA (SOLO PARA VOS) ---
    if prompt == "#admin-lucho":
        st.session_state.admin_mode = True
        st.rerun()
    # --------------------------------------

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Analizando stock y calculando descuentos..."):
            response = chat.send_message(prompt)
            full_text = response.text
            
            log_interaction(prompt, full_text)
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_text:
                dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                
                if "15%" in dialogue or "MAYORISTA" in dialogue:
                    st.balloons()
                    st.toast('🎉 ¡Tarifa Mayorista (15% OFF) Activada!', icon='💰')
                
                st.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="final-action-card">
                    🚀 FINALIZAR PEDIDO CON MARTÍN<br>
                    <span style="font-size:0.8rem; font-weight:400;">Enviar cotización por WhatsApp</span>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception as e:
        st.error(f"Error: {e}")

# --- 10. PANEL OCULTO (SOLO VISIBLE CON CLAVE) ---
if st.session_state.admin_mode:
    st.markdown("---")
    st.warning("🔓 MODO ADMINISTRADOR ACTIVADO")
    st.write("### 📊 Métricas de Sesión Actual")
    
    if st.session_state.log_data:
        df_log = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df_log)
        
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "metricas.csv", "text/csv")
    else:
        st.info("Sin datos.")
        
    if st.button("🔴 Cerrar Admin"):
        st.session_state.admin_mode = False
        st.rerun()
