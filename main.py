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
# 1. CONFIGURACIÓN INNEGOCIABLE
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A. | Cotizador",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00

# --- INFRAESTRUCTURA DE DATOS ---
URL_FORM_GOOGLE = ""  # 🔴 TU LINK DE GOOGLE FORMS
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE,
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

FRASES_FOMO = [
    "🔥 Chapas: Quedan pocas unidades del lote.",
    "⚠️ Hierro: Alta rotación hoy.",
    "👀 3 Constructores están cotizando ahora.",
    "📉 Dólar estable: Buen momento para acopiar.",
    "🚚 Logística: Armado de reparto en proceso."
]

# ==========================================
# 2. MOTOR DE BACKEND & ESTADO
# ==========================================

# Inicialización de Estados
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "monto_acumulado" not in st.session_state: st.session_state.monto_acumulado = 0.0
# Nuevo: Estado para forzar el nivel visual de la barra si es producto competitivo
if "nivel_forzado" not in st.session_state: st.session_state.nivel_forzado = 0 
# Nuevo: Estado para que el botón de compra no desaparezca
if "link_compra_activo" not in st.session_state: st.session_state.link_compra_activo = None

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "🏗️ **Hola.** Cotizo directo de fábrica.\n¿Qué materiales necesitás?"}]

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {ID_CAMPO_CLIENTE: str(cliente), ID_CAMPO_MONTO: str(monto), ID_CAMPO_OPORTUNIDAD: str(oportunidad)}
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except: pass

def log_interaction(user_text, bot_response, monto_detectado):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "BAJA"
    if monto_detectado > 1500000: opportunity = "🔥 ALTA"
    elif monto_detectado > 500000: opportunity = "MEDIA"
    
    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto": monto_detectado})
    
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True
    thread.start()

def extraer_datos_respuesta(texto):
    """Extrae precio y etiqueta de nivel forzado"""
    # Extraer Monto
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = [int(p.replace('.', '')) for p in patrones if p.replace('.', '').isdigit()]
    monto_max = max(montos) if montos else 0
    
    # Extraer Nivel Forzado (Tag oculto [LEVEL:15])
    nivel_tag = re.search(r'\[LEVEL:(\d+)\]', texto)
    nivel_detectado = int(nivel_tag.group(1)) if nivel_tag else 0
    
    return monto_max, nivel_detectado

# ==========================================
# 3. LÓGICA DE LA BARRA (SINCRONIZADA)
# ==========================================

# Definimos niveles base
NIVELES = [
    {"techo": 500000, "desc": 5, "nombre": "INICIAL", "color": "#78909c"}, 
    {"techo": 1500000, "desc": 10, "nombre": "OBRA", "color": "#ffa726"}, 
    {"techo": 3000000, "desc": 15, "nombre": "CONSTRUCTOR", "color": "#d50000"}, 
    {"techo": float('inf'), "desc": 18, "nombre": "PARTNER", "color": "#6200ea"} 
]

# 1. Determinamos el % de descuento real a mostrar
descuento_visual = 5 # Base
color_barra = "#78909c"
texto_meta = "Iniciando..."
porcentaje_barra = 0

# Si Miguel detectó producto competitivo, manda el nivel forzado
if st.session_state.nivel_forzado > 0:
    descuento_visual = st.session_state.nivel_forzado
    # Asignar color según el forzado
    if descuento_visual >= 18: color_barra = "#6200ea"
    elif descuento_visual >= 15: color_barra = "#d50000"
    elif descuento_visual >= 10: color_barra = "#ffa726"
    porcentaje_barra = 100 # Barra llena porque es un beneficio especial
    texto_meta = "🔥 ¡BENEFICIO COMPETITIVO ACTIVADO!"

else:
    # Si no hay forzado, usa la lógica de montos acumulados
    monto = st.session_state.monto_acumulado
    for i, nivel in enumerate(NIVELES):
        if monto < nivel["techo"]:
            descuento_visual = nivel["desc"]
            color_barra = nivel["color"]
            # Calcular progreso hacia el siguiente nivel
            base = NIVELES[i-1]["techo"] if i > 0 else 0
            rango = nivel["techo"] - base
            progreso = monto - base
            porcentaje_barra = min(max(progreso / rango, 0), 1) * 100
            falta = nivel["techo"] - monto
            
            # Ver cual es el siguiente salto
            prox_desc = NIVELES[i+1]["desc"] if i < len(NIVELES)-1 else 18
            texto_meta = f"Faltan ${falta:,.0f} para {prox_desc}% OFF"
            break
    
    if monto >= 3000000:
        descuento_visual = 18
        color_barra = "#6200ea"
        porcentaje_barra = 100
        texto_meta = "🏆 SOCIO PARTNER"

# Renderizado CSS de la Barra
st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 165px !important; padding-bottom: 120px !important; }}
    
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
    
    .game-zone {{ padding: 10px 20px; background: #fafafa; border-bottom: 1px solid #eee; }}
    .level-info {{ display: flex; justify-content: space-between; margin-bottom: 5px; align-items: center; }}
    .current-badge {{ 
        background: #37474f; color: white; padding: 4px 10px; border-radius: 12px; 
        font-size: 0.75rem; font-weight: bold; border: 1px solid #cfd8dc;
    }}
    .next-target {{ color: {color_barra}; font-weight: 800; font-size: 0.9rem; }}
    .custom-progress-bg {{ width: 100%; height: 14px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }}
    .custom-progress-fill {{
        height: 100%; width: {porcentaje_barra}%; 
        background: linear-gradient(90deg, {color_barra} 0%, {color_barra} 100%); 
        transition: width 0.6s ease-in-out;
        box-shadow: 0 0 10px {color_barra};
    }}
    
    .wa-float {{
        position: fixed; bottom: 90px; right: 20px;
        background: #25D366; color: white; width: 60px; height: 60px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 30px; box-shadow: 0 4px 15px rgba(37, 211, 102, 0.4);
        z-index: 9999; transition: transform 0.2s;
    }}
    .wa-float:hover {{ transform: scale(1.1); }}
    
    .closing-card {{
        background: linear-gradient(135deg, #d50000 0%, #b71c1c 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 900; font-size: 1.2rem; margin-top: 15px;
        box-shadow: 0 8px 25px rgba(213, 0, 0, 0.3);
        border: 2px solid #ff8a80; animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); }}
    }}
    .stChatMessage {{ border-radius: 15px !important; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>⚡ PEDRO BRAVIN S.A. | LIVE</span>
            <span class="legal-text">⚠️ Precios Web Estimados</span>
        </div>
        <div class="game-zone">
            <div class="level-info">
                <span class="current-badge">TU DESCUENTO: {descuento_visual}%</span>
                <span class="next-target">{texto_meta}</span>
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
# 4. CEREBRO IA (CON STRICT GUARDRAILS)
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
    except: return "Error DB"

csv_context = load_data()

sys_prompt = f"""
ROL: Eres Miguel, un cotizador automático de materiales de construcción.
BASE DE DATOS: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

⛔ GUARDRAILS (REGLAS DE SEGURIDAD):
1. SI EL USUARIO PREGUNTA COSAS PERSONALES, DE PROGRAMACIÓN, CLIMA O POLÍTICA -> RESPONDE: "Soy Miguel, experto en acero. Solo cotizo materiales para tu obra."
2. NO MENCIONES A "MARTÍN" EN EL TEXTO. Martín es solo para el botón final.
3. NO SALUDES CON TEXTOS LARGOS.

💰 REGLAS DE DESCUENTO:
1. **COMPETITIVOS (Chapas Techo, Perfiles, Hierro Const.):**
   - APLICA 15% AUTOMÁTICO.
   - AGREGA AL FINAL DEL TEXTO LA ETIQUETA OCULTA: [LEVEL:15]
2. **RESTO:**
   - < $500k: 5% (Pago Contado). [LEVEL:5]
   - > $1.5M: 10%. [LEVEL:10]
   - > $3M: 15%. [LEVEL:15]

📝 FORMATO DE RESPUESTA (EXTREMADAMENTE BREVE):
- Usa Bullet points.
- Max 30 palabras.
- Estructura:
  ✅ Stock: [SI/NO/BAJO]
  💲 Precio: $[Monto] + IVA
  🚚 Flete: [Bonificado/A cotizar]
  ❓ Cierre: "¿Cerramos?"

FORMATO WHATSAPP FINAL (SOLO SI EL CLIENTE MUESTRA INTENCIÓN DE COMPRA):
[TEXTO_WHATSAPP]:
Hola Martín, CONGELAR STOCK.
📦 Items: [Resumen]
📍 Zona: [Ciudad]
💰 Total: $[Monto] + IVA
💎 Descuento: [X%]
"""

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
    except: pass

# ==========================================
# 5. CHAT Y PROCESAMIENTO
# ==========================================

# 1. Renderizar Historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# 2. Renderizar Botón de Compra PERSISTENTE
if st.session_state.link_compra_activo:
    st.markdown(f"""
    <a href="{st.session_state.link_compra_activo}" target="_blank" class="closing-card">
        🔥 FINALIZAR CON MARTÍN <br>
        <span style="font-size:0.9rem; font-weight:400; opacity:0.9;">Click aquí para congelar precio</span>
    </a>
    """, unsafe_allow_html=True)

# 3. Input Usuario
if prompt := st.chat_input("Ej: 20 Chapas C25 y Perfiles..."):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

    if random.random() > 0.7:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("⚡ Cotizando..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Análisis Inteligente
                nuevo_monto, nivel_detectado = extraer_datos_respuesta(full_text)
                
                # Actualizar estados
                if nuevo_monto > 0: st.session_state.monto_acumulado = nuevo_monto
                if nivel_detectado > 0: st.session_state.nivel_forzado = nivel_detectado
                
                log_interaction(prompt, full_text, nuevo_monto)

                # Procesar Link de WhatsApp y limpiarlo del texto visible
                display_text = full_text
                if "[TEXTO_WHATSAPP]:" in full_text:
                    parts = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    display_text = parts[0].strip()
                    wa_msg = parts[1].strip()
                    
                    # Guardar link en sesión para que sea persistente
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_msg)}"
                    st.session_state.link_compra_activo = wa_url
                    
                    # Feedback visual de éxito
                    st.balloons()
                    st.toast("✅ COTIZACIÓN LISTA PARA MARTÍN", icon="🚀")

                # Limpiar etiquetas internas del texto visible [LEVEL:XX]
                display_text = re.sub(r'\[LEVEL:\d+\]', '', display_text)
                
                st.markdown(display_text)
                st.session_state.messages.append({"role": "assistant", "content": display_text})
                
                time.sleep(0.5)
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# Panel Admin
if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN PANEL"):
        if st.session_state.log_data:
            st.dataframe(pd.DataFrame(st.session_state.log_data))
