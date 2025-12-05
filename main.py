import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import datetime
import requests
import threading
import time

# --- 1. CONFIGURACIÓN DE ANALÍTICAS ---
URL_FORM_GOOGLE = ""  
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

    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

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
            <span class="brand-name">Miguel | Pedro Bravin S.A.</span>
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

# --- 5. CARGA DE DATOS OPTIMIZADA ---
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

# --- 6. METRICAS BACKGROUND ---
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

# --- 7. CEREBRO DE VENTAS (MIGUEL CONCISO) ---
# AQUÍ ESTÁ EL CAMBIO PRINCIPAL PARA EVITAR TEXTOS LARGOS
sys_prompt = f"""
ROL: Eres Miguel, Asesor de Pedro Bravin S.A.
ESTILO: **EXTREMADAMENTE CONCISO Y BREVE**. (Estilo WhatsApp rápido).
OBJETIVO: Cotizar y cerrar venta. NO dar explicaciones largas.

BASE DE DATOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR: ${DOLAR_BNA_REF}
- ZONA GRATIS: {CIUDADES_GRATIS}

🚨 **REGLAS DE ORO (VELOCIDAD):**
1.  **NO SALUDES LARGO:** Ve directo al grano.
2.  **PRECIOS:** Siempre "$X + IVA".
3.  **VENTA CRUZADA CORTA (OBLIGATORIA):**
    * Si pide chapas -> "¿Agrego tornillos?". (NO expliques para qué sirven).
    * Si pide perfiles -> "¿Sumo electrodos?".
    * **SI ESTÁ EN LISTA:** Da precio y ofrece sumar.
    * **SI NO ESTÁ:** "Te agrego los complementarios a cotizar en el pedido".
4.  **DESCUENTOS (BREVE):**
    * $200k-$300k: "Falta poco para el 15% OFF. ¿Sumamos algo?".
    * >300k: "¡15% OFF Mayorista aplicado!".
5.  **CIERRE:** "Acopio 6 meses gratis. ¿Te paso el link?".

FORMATO SALIDA FINAL (WHATSAPP):
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual.
📍 Destino: [Localidad]
📋 Pedido Web:
- [Item] x [Cant]
⚠️ A Cotizar Manual (IA Sugiere):
- [Complementarios Faltantes]
💰 Inversión: $[Monto] + IVA
🎁 Beneficios: [Acopio / 15% OFF]
Link pago por favor.
"""

# --- 8. CHAT IA ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola. Soy Miguel.**\n\n¿Qué materiales necesitas cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        generation_config = {"temperature": 0.2, "max_output_tokens": 4096} # Menos tokens = Más rápido
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
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            
            with st.spinner("Miguel analizando precios..."):
                try:
                    response_stream = chat.send_message(prompt, stream=True)
                except Exception:
                    st.error("Error de red.")
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
                    st.toast('🎉 ¡Tarifa Mayorista (15% OFF)!', icon='💰')
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="final-action-card">
                    🚀 FINALIZAR PEDIDO CON MARTÍN<br>
                    <span style="font-size:0.8rem; font-weight:400;">Enviar cotización por WhatsApp</span>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Error: {e}")

# --- 10. ADMIN ---
if st.session_state.admin_mode:
    st.markdown("---")
    st.warning("🔐 ADMIN MIGUEL")
    if st.session_state.log_data:
        df_log = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df_log, use_container_width=True)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "metricas.csv", "text/csv")
    else:
        st.info("Sin datos.")
    if st.button("🔴 Cerrar"):
        st.session_state.admin_mode = False
        st.rerun()
