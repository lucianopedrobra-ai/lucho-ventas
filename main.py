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
st.set_page_config(
    page_title="Asesor Comercial | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Analíticas y Variables ---
URL_FORM_GOOGLE = ""  
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# ==========================================
# 2. INTERFAZ VISUAL (SOLUCIÓN MÓVIL)
# ==========================================
st.markdown("""
    <style>
    /* 1. LIMPIEZA Y BASE */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] { 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
        background-color: #ffffff;
    }

    /* 2. HEADER */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%; height: 60px;
        background-color: #ffffff; border-bottom: 1px solid #e0e0e0;
        z-index: 999999; display: flex; justify-content: space-between; align-items: center;
        padding: 0 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .brand-text { color: #0f2c59; font-weight: 800; font-size: 16px; line-height: 1.2; }
    .brand-sub { font-size: 10px; color: #888; font-weight: 400; display: block; }
    .wa-btn {
        background-color: #25D366; color: white !important; text-decoration: none; 
        padding: 8px 15px; border-radius: 20px; font-weight: 600; font-size: 13px; 
        display: flex; align-items: center; gap: 5px; white-space: nowrap;
    }

    /* 3. LAYOUT */
    .block-container {
        padding-top: 80px !important;    
        padding-bottom: 150px !important; 
        max-width: 100%;
    }

    /* 4. CHAT */
    .stChatMessage { background-color: transparent; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f0f4f8; border-radius: 10px; padding: 10px; }

    /* 5. INPUT FIX */
    .stChatInputContainer { padding-bottom: 10px; }
    div[data-testid="stChatInput"] { background-color: white !important; border-top: 1px solid #ddd; padding-top: 10px; }
    textarea[data-testid="stChatInputTextArea"] {
        background-color: #ffffff !important; color: #000000 !important;
        caret-color: #000000 !important; border: 1px solid #cccccc !important;
    }
    textarea[data-testid="stChatInputTextArea"]::placeholder { color: #666666 !important; }

    /* 6. CTA */
    .cta-box {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white; padding: 15px; border-radius: 12px; text-align: center;
        margin-top: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        text-decoration: none; display: block;
    }

    @media (max-width: 600px) {
        .brand-text { font-size: 14px; }
        .wa-btn span { display: none; } 
        .wa-btn::after { content: "WhatsApp"; }
        .block-container { padding-bottom: 160px !important; }
    }
    </style>

    <div class="fixed-header">
        <div class="brand-wrapper">
            <div class="brand-text">MIGUEL | PEDRO BRAVIN S.A.</div>
            <span class="brand-sub">⚠️ Precios y Stock Estimados</span>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-btn">
            <span>Hablar con Martín</span>
        </a>
    </div>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    """, unsafe_allow_html=True)

# ==========================================
# 3. SISTEMA TÉCNICO & MOTOR DE BÚSQUEDA
# ==========================================

# --- Autenticación ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de API Key.")
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
        # Pre-procesamiento para búsqueda rápida (creamos una columna "todo")
        df['SEARCH_INDEX'] = df.astype(str).agg(' '.join, axis=1).str.lower()
        return df 
    except Exception:
        return None

raw_data = load_data()

# --- NUEVO: MOTOR DE BÚSQUEDA HÍBRIDO ---
def buscar_productos_inteligente(consulta, df, limite=40):
    """
    Busca palabras clave en el DataFrame y devuelve solo las filas relevantes.
    Esto permite manejar 20.000 articulos sin marear a la IA.
    """
    if df is None or df.empty:
        return ""
    
    # Limpieza básica de la consulta
    palabras = consulta.lower().split()
    palabras_clave = [p for p in palabras if len(p) > 2] # Ignoramos "de", "la", "el"
    
    if not palabras_clave:
        return "" # Si no hay palabras clave (ej: "hola"), no devolvemos datos
    
    # Filtramos filas que contengan ALGUNA de las palabras clave
    # (Podríamos ser más estrictos pidiendo TODAS, pero empezamos flexible)
    mask = df['SEARCH_INDEX'].apply(lambda x: any(palabra in x for palabra in palabras_clave))
    
    resultados = df[mask].head(limite) # Limitamos a 40 para velocidad
    
    if resultados.empty:
        return ""
    
    # Eliminamos la columna de índice para no ensuciar el contexto
    resultados_limpios = resultados.drop(columns=['SEARCH_INDEX'], errors='ignore')
    return resultados_limpios.to_csv(index=False)

# --- Analíticas ---
if "log_data" not in st.session_state:
    st.session_state.log_data = []
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(cliente),
                ID_CAMPO_MONTO: str(monto),
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }, timeout=3)
        except: pass

def log_interaction(user_text, bot_response):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "NORMAL"
    monto_estimado = 0
    if "$" in bot_response:
        try:
            precios = [int(s.replace('.','')) for s in re.findall(r'\$([\d\.]+)', bot_response) if s.replace('.','').isdigit()]
            if precios:
                monto_estimado = max(precios)
                if monto_estimado > 300000: opportunity = "🔥 ALTA (MAYORISTA)"
        except: pass
    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto Max": monto_estimado})
    threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_estimado, opportunity), daemon=True).start()

# ==========================================
# 4. CEREBRO DE VENTAS (MODIFICADO PARA BÚSQUEDA)
# ==========================================
# Nota: Ya NO incluimos el csv_context completo aquí.
sys_prompt_base = f"""
ROL: Eres Miguel, Asesor Técnico y Experto en Cierre de Pedro Bravin S.A.
TONO: Profesional, resolutivo y comercialmente agresivo (pero amable).
OBJETIVO: Cotizar rápido usando el CONTEXTO ADJUNTO y CERRAR el deal.

DATOS FIJOS: DÓLAR BNA ${DOLAR_BNA_REF} | ZONA GRATIS: {CIUDADES_GRATIS}

📜 **PROTOCOLOS DE ACTUACIÓN:**
1.  **USO DE DATOS:** Recibirás fragmentos de la base de datos según lo que pida el usuario. Si la información está en el fragmento, cotiza exacto. Si no está, di que lo consultas con Martín.
2.  **PRECIOS:** Todo es NETO. Responde siempre "$ [Precio] + IVA".
3.  **LOGÍSTICA:** Zona gratis -> "¡Logística Bonificada!". Lejos -> "Calculo envío desde nodo cercano".
4.  **DESCUENTOS:** > $300.000 -> "¡15% OFF MAYORISTA Activado!".
5.  **CIERRE:** Ofrece "Acopio 6 meses gratis" y pide cerrar.

FORMATO SALIDA FINAL (PARA EL BOTÓN):
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual (Miguel).
📍 Destino: [Localidad]
📋 Pedido Web:
- [Item] x [Cant]
💰 Inversión Aprox: $[Monto] + IVA
Solicito link de pago.
"""

# ==========================================
# 5. MOTOR DE CHAT
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\n\nExperto en materiales de Pedro Bravin S.A.\n\n**¿Qué estás buscando cotizar hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt_base)
        st.session_state.chat_session = model.start_chat(history=[])
    except:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt_base)
            st.session_state.chat_session = model.start_chat(history=[])
        except: st.error("Error conexión.")

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
            with st.spinner("Miguel está buscando en depósito..."):
                
                # --- PASO CRÍTICO: BÚSQUEDA HÍBRIDA ---
                # 1. Buscamos en el CSV los productos que coinciden con el prompt
                contexto_relevante = buscar_productos_inteligente(prompt, raw_data)
                
                # 2. Armamos el mensaje enriquecido para la IA
                if contexto_relevante:
                    mensaje_para_ia = f"""
                    INFORMACIÓN DE STOCK ENCONTRADA (Fragmento de Base de Datos):
                    {contexto_relevante}
                    
                    PREGUNTA DEL CLIENTE:
                    {prompt}
                    """
                else:
                    mensaje_para_ia = f"""
                    NO SE ENCONTRARON PRODUCTOS EXACTOS EN LA BASE DE DATOS PARA ESTA CONSULTA.
                    Actúa como asesor general o pide más detalles del producto.
                    
                    PREGUNTA DEL CLIENTE:
                    {prompt}
                    """
                
                # 3. Enviamos a Gemini
                try:
                    response_stream = chat.send_message(mensaje_para_ia, stream=True)
                except:
                    st.error("Reintentando conexión...")
                    time.sleep(1)
                    response_stream = chat.send_message(mensaje_para_ia, stream=True)

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
                    st.toast('🎉 ¡Tarifa Mayorista Activada!', icon='💰')
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="cta-box">
                    <div style="font-weight:800; font-size: 1.1rem;">🚀 FINALIZAR PEDIDO</div>
                    <div style="font-size:0.8rem; opacity: 0.9;">Enviar cotización a Martín</div>
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
    st.warning("🔐 ADMIN PANEL")
    if st.session_state.log_data:
        df_log = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df_log, use_container_width=True)
    if st.button("🔴 Cerrar"):
        st.session_state.admin_mode = False
        st.rerun()
