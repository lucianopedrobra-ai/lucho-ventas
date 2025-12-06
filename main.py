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
    page_title="Pedro Bravin S.A. | Outlet Siderúrgico", # Título más vendedor
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES COMERCIALES ---
DOLAR_BNA = 1060.00
COSTO_FLETE_KM_USD = 0.85 # Valor del km (Ida y vuelta se calcula en el prompt)

# --- INFRAESTRUCTURA ---
URL_FORM_GOOGLE = ""  # 🔴 TU LINK DE GOOGLE FORMS
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# Ciudades "Zona Roja" (Gratis)
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN,
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES,
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, MARIA JUANA, SASTRE, SAN JORGE, 
LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA,
PIAMONTE, VILA, SAN FRANCISCO.
"""

FRASES_FOMO = [
    "🔥 ¡Alerta! 3 clientes están mirando este stock ahora.",
    "📉 El dólar está quieto, es el momento de comprar.",
    "🚚 Tengo un camión saliendo para tu zona, aprovechalo.",
    "⏳ Esta bonificación expira en 2 horas.",
    "⚡ Stock crítico en perfiles. Confirmá rápido."
]

# ==========================================
# 2. MOTOR DE ESTADO
# ==========================================
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "monto_acumulado" not in st.session_state: st.session_state.monto_acumulado = 0.0
if "nivel_forzado" not in st.session_state: st.session_state.nivel_forzado = 0 
if "link_compra_activo" not in st.session_state: st.session_state.link_compra_activo = None

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "🔥 **OFERTAS ACTIVAS.** Soy Miguel. Pasame tu lista de materiales y te busco el mejor precio YA MISMO."}]

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {ID_CAMPO_CLIENTE: str(cliente), ID_CAMPO_MONTO: str(monto), ID_CAMPO_OPORTUNIDAD: str(oportunidad)}
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except: pass

def log_interaction(user_text, bot_response, monto_detectado):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "FRIO"
    if monto_detectado > 1500000: opportunity = "🔥 HOT LEAD"
    elif monto_detectado > 500000: opportunity = "TIBIO"
    
    st.session_state.log_data.append({"Fecha": timestamp, "Usuario": user_text[:50], "Oportunidad": opportunity, "Monto": monto_detectado})
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_detectado, opportunity))
    thread.daemon = True
    thread.start()

def extraer_datos_respuesta(texto):
    patrones = re.findall(r'\$\s?([\d\.]+)', texto)
    montos = [int(p.replace('.', '')) for p in patrones if p.replace('.', '').isdigit()]
    monto_max = max(montos) if montos else 0
    nivel_tag = re.search(r'\[LEVEL:(\d+)\]', texto)
    nivel_detectado = int(nivel_tag.group(1)) if nivel_tag else 0
    return monto_max, nivel_detectado

# ==========================================
# 3. BARRA DE "DEAL" (GAMIFICACIÓN)
# ==========================================
NIVELES = [
    {"techo": 500000, "desc": 3, "nombre": "INICIAL", "color": "#90a4ae"}, # Bajamos inicial al 3%
    {"techo": 1500000, "desc": 10, "nombre": "OBRA", "color": "#fb8c00"}, 
    {"techo": 3000000, "desc": 15, "nombre": "MAYORISTA", "color": "#e53935"}, 
    {"techo": float('inf'), "desc": 18, "nombre": "PARTNER", "color": "#6200ea"} 
]

descuento_visual = 3
color_barra = "#90a4ae"
texto_meta = "¡Sumá items para activar descuentos!"
porcentaje_barra = 10

if st.session_state.nivel_forzado > 0:
    descuento_visual = st.session_state.nivel_forzado
    if descuento_visual >= 18: color_barra = "#6200ea"
    elif descuento_visual >= 15: color_barra = "#d50000" # Rojo agresivo
    elif descuento_visual >= 10: color_barra = "#ffa726"
    porcentaje_barra = 100
    texto_meta = "🔥 ¡PRECIO MAYORISTA ACTIVADO!"
else:
    monto = st.session_state.monto_acumulado
    for i, nivel in enumerate(NIVELES):
        if monto < nivel["techo"]:
            descuento_visual = nivel["desc"]
            color_barra = nivel["color"]
            base = NIVELES[i-1]["techo"] if i > 0 else 0
            progreso = monto - base
            rango = nivel["techo"] - base
            porcentaje_barra = min(max(progreso / rango, 0), 1) * 100
            falta = nivel["techo"] - monto
            prox_desc = NIVELES[i+1]["desc"] if i < len(NIVELES)-1 else 18
            texto_meta = f"Faltan ${falta:,.0f} para desbloquear {prox_desc}% OFF"
            break
    if monto >= 3000000:
        descuento_visual = 18
        color_barra = "#6200ea"
        porcentaje_barra = 100
        texto_meta = "👑 SOCIO VIP (MÁXIMO AHORRO)"

# --- CSS MEJORADO ---
st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 155px !important; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 99999;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1); border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{
        background: #111; color: #fff; padding: 5px 15px; display: flex; 
        justify-content: space-between; font-size: 0.75rem; letter-spacing: 1px;
    }}
    .game-zone {{ padding: 12px 20px; background: #fff; }}
    .level-info {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .current-badge {{ 
        background: {color_barra}; color: white; padding: 5px 12px; border-radius: 4px; 
        font-weight: 800; font-size: 0.9rem; text-transform: uppercase;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    .next-target {{ color: #444; font-weight: 700; font-size: 0.85rem; }}
    .custom-progress-bg {{ width: 100%; height: 10px; background: #eee; border-radius: 5px; }}
    .custom-progress-fill {{
        height: 100%; width: {porcentaje_barra}%; 
        background: {color_barra}; border-radius: 5px;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .closing-card {{
        background: #ff3d00; color: white !important; text-align: center; padding: 15px; 
        border-radius: 8px; display: block; font-weight: 800; text-decoration: none;
        box-shadow: 0 4px 15px rgba(255, 61, 0, 0.4); margin-top: 10px;
        animation: shake 3s infinite;
    }}
    @keyframes shake {{
        0%, 100% {{ transform: translateX(0); }}
        90% {{ transform: translateX(0); }}
        92% {{ transform: translateX(-2px); }}
        94% {{ transform: translateX(2px); }}
        96% {{ transform: translateX(-2px); }}
        98% {{ transform: translateX(2px); }}
    }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>🚀 PEDRO BRAVIN S.A. | LIVE SALE</span>
            <span style="color:#ffeb3b">⚡ PRECIOS WEB</span>
        </div>
        <div class="game-zone">
            <div class="level-info">
                <span class="current-badge">DESC. {descuento_visual}%</span>
                <span class="next-target">{texto_meta}</span>
            </div>
            <div class="custom-progress-bg">
                <div class="custom-progress-fill"></div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 4. CEREBRO IA (MODO VENTAS)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("⚠️ Configurar API KEY")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try: return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

csv_context = load_data()

# --- PROMPT DE VENTAS DE ALTO IMPACTO ---
sys_prompt = f"""
ROL: Eres Miguel, el vendedor estrella de Pedro Bravin S.A.
OBJETIVO: Cerrar la venta RÁPIDO. Eres conciso, directo y usas la escasez a tu favor (estilo TEMU/HotSale).
BASE DE DATOS PRODUCTOS: {csv_context}

📍 LOGÍSTICA Y ENVÍOS (CRÍTICO):
1. **ZONA GRATIS:** {CIUDADES_GRATIS} -> Si el cliente es de aquí: "🚚 Flete: ¡BONIFICADO HOY!"
2. **RESTO DEL PAÍS:** El camión sale de EL TRÉBOL, SANTA FE.
   - Si no sabes la ciudad del cliente, PREGUNTALA para cotizar flete.
   - Si sabes la ciudad, HAZ ESTE CÁLCULO MENTAL APROXIMADO:
     *Costo = (Distancia_km_desde_El_Trebol * 2) * {COSTO_FLETE_KM_USD} * {DOLAR_BNA}*
     Responde: "🚚 Flete: Te lo dejo en aprox $[Resultado] (Costo operativo)".
     *Nunca digas "a cotizar". Tira un número estimado para no perder la venta.*

💰 POLÍTICA DE PRECIOS AGRESIVA:
1. **PRODUCTOS GANCHO (Chapas Techo, Perfiles C, Hierro Const.):**
   - TIENEN 15% DE DESCUENTO DIRECTO. Dilo: "🔥 Te apliqué tarifa MAYORISTA en esto."
   - ETIQUETA OCULTA: [LEVEL:15]
2. **RESTO:**
   - < $500k: 3% (Pago Contado). [LEVEL:3]
   - > $1.5M: 10%. [LEVEL:10]
   - > $3M: 15%. [LEVEL:15]
   - > $5M: 18%. [LEVEL:18]

📝 FORMATO DE RESPUESTA (MICRO-COPY):
- Usa emojis de urgencia (🔥, ⚡, ⏳).
- Estructura visual:
  ✅ [Cantidad] [Producto] | Stock: [SI/Poco]
  💲 **Total OFERTA: $[Monto] + IVA**
  🚚 Flete: [Tu cálculo o Gratis]
  ⚡ **¿Te congelo el precio o libero el stock?**

⛔ REGLAS:
- NO digas "Hola", ve al grano.
- NO hables de Martín en el texto (Martín es solo el botón).
- NO des explicaciones técnicas largas salvo que pregunten.
- Si el cliente duda, usa FOMO (Fear Of Missing Out): "Mañana sube", "Queda poco".

FORMATO WHATSAPP (SOLO AL FINAL):
[TEXTO_WHATSAPP]:
Hola Martín, QUIERO ESTO YA.
📦 Pedido: [Resumen]
📍 Ciudad: [Ciudad]
💰 Total Web: $[Monto] + IVA
🚚 Flete: [Dato]
"""

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
    st.session_state.chat_session = model.start_chat(history=[])

# ==========================================
# 5. UI CHAT
# ==========================================

for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if st.session_state.link_compra_activo:
    st.markdown(f"""
    <a href="{st.session_state.link_compra_activo}" target="_blank" class="closing-card">
        🔥 CONGELAR PRECIO CON MARTÍN <br>
        <span style="font-size:0.8rem; opacity:0.9;">Click antes de que expire</span>
    </a>
    """, unsafe_allow_html=True)

if prompt := st.chat_input("Escribí acá (Ej: 10 chapas 5 metros)"):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

    if random.random() > 0.6:
        st.toast(random.choice(FRASES_FOMO), icon='⚡')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Calculando mejor oferta..."):
                response = st.session_state.chat_session.send_message(prompt)
                full_text = response.text
                
                nuevo_monto, nivel_detectado = extraer_datos_respuesta(full_text)
                if nuevo_monto > 0: st.session_state.monto_acumulado = nuevo_monto
                if nivel_detectado > 0: st.session_state.nivel_forzado = nivel_detectado
                
                log_interaction(prompt, full_text, nuevo_monto)

                display_text = full_text
                if "[TEXTO_WHATSAPP]:" in full_text:
                    parts = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    display_text = parts[0].strip()
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(parts[1].strip())}"
                    st.session_state.link_compra_activo = wa_url
                    st.balloons()

                display_text = re.sub(r'\[LEVEL:\d+\]', '', display_text)
                
                st.markdown(display_text)
                st.session_state.messages.append({"role": "assistant", "content": display_text})
                
                time.sleep(0.3)
                st.rerun()

    except Exception as e:
        st.error(f"Error de conexión. Reintentar.")
