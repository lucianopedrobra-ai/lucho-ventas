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
from PIL import Image

# ==========================================
# 1. CONFIGURACIÓN E INFRAESTRUCTURA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A. | App",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed" # Colapsado en móvil para ganar espacio
)

# --- VARIABLES DE NEGOCIO (INTOCABLES) ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 

# --- CONEXIÓN REAL GOOGLE SHEETS ---
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

# --- LOGS GOOGLE FORMS ---
URL_FORM_GOOGLE = "" # 🔴 PEGAR TU LINK AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

FRASES_FOMO = [
    "🔥 Stock bajo en este ítem.",
    "⚡ 2 clientes están llevando esto.",
    "🚚 Salida de camión programada.",
    "📉 Precio congelado por 1 hora.",
    "💎 Oferta exclusiva web."
]

# ==========================================
# 2. GESTIÓN DE ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **¡Hola! Soy Miguel.**\nCotizo al instante. Escribí tu pedido o subí una foto de tu lista."}]

# ==========================================
# 3. FUNCIONES BACKEND
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except Exception as e: return "Error DB: " + str(e)

csv_context = load_data()

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(cliente), 
                ID_CAMPO_MONTO: str(monto), 
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }, timeout=2)
        except: pass

def log_interaction(user_text, monto_real_carrito):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "BAJA"
    if monto_real_carrito > 1500000: opportunity = "🔥 ALTA"
    elif monto_real_carrito > 500000: opportunity = "MEDIA"
    
    st.session_state.log_data.append({
        "Fecha": timestamp, "Usuario": user_text[:50], 
        "Oportunidad": opportunity, "Monto": monto_real_carrito
    })
    thread = threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto_real_carrito, opportunity))
    thread.daemon = True
    thread.start()

def parsear_ordenes_bot(texto_respuesta):
    patron = r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto_respuesta)
    items_agregados = []
    
    for cant, prod, precio, tipo in coincidencias:
        item = {
            "cantidad": float(cant), 
            "producto": prod.strip(),
            "precio_unit": float(precio), 
            "subtotal": float(cant) * float(precio),
            "tipo": tipo.strip().upper()
        }
        st.session_state.cart.append(item)
        items_agregados.append(item)
    return items_agregados

def calcular_negocio():
    total_bruto = sum(item['subtotal'] for item in st.session_state.cart)
    descuento = 3
    color = "#546e7a" # Gris azulado profesional
    texto_nivel = "INICIAL"
    
    # Lógica de Descuentos (Temu Style)
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart)
    
    if tiene_gancho:
        descuento = 15; texto_nivel = "🔥 MAYORISTA"; color = "#d32f2f" # Rojo Temu
    elif total_bruto > 3000000:
        descuento = 15; texto_nivel = "👑 PARTNER"; color = "#6200ea" # Violeta
    elif total_bruto > 1500000:
        descuento = 10; texto_nivel = "🏗️ OBRA"; color = "#f57c00" # Naranja ML
        
    total_neto = total_bruto * (1 - (descuento/100))
    return total_bruto, total_neto, descuento, color, texto_nivel

def generar_link_whatsapp(total):
    texto = "Hola Martín, quiero CONGELAR este pedido:\n"
    for item in st.session_state.cart:
        texto += f"▪ {item['cantidad']}x {item['producto']}\n"
    texto += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    texto += "\n(Acopio 6 meses a conversar)"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(texto)}"

# ==========================================
# 4. UI: ESTILO MÓVIL (TEMU + ML)
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
porcentaje_barra = min(total_final / 3000000 * 100, 100) if total_final < 3000000 else 100
link_wa_float = generar_link_whatsapp(total_final)

st.markdown(f"""
    <style>
    /* Ajustes Generales Móvil */
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 140px !important; padding-bottom: 100px !important; }}
    
    /* HEADER FIJO (Estilo ML/App) */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: white; z-index: 99999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{
        background: #232f3e; color: white; padding: 8px 15px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.75rem; letter-spacing: 0.5px;
    }}
    .cart-summary {{
        padding: 10px 15px; display: flex; justify-content: space-between; align-items: center;
    }}
    .price-tag {{ font-size: 1.2rem; font-weight: 800; color: #333; }}
    .badge {{ 
        background: {color_barra}; color: white; padding: 4px 10px; 
        border-radius: 20px; font-size: 0.75rem; font-weight: bold; 
    }}
    
    /* BOTÓN WHATSAPP FLOTANTE (FAB) */
    .float-wa {{
        position: fixed; width: 60px; height: 60px;
        bottom: 90px; right: 20px;
        background-color: #25d366; color: #FFF;
        border-radius: 50px; text-align: center; font-size: 30px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
        z-index: 10000; display: flex; align-items: center; justify-content: center;
        text-decoration: none; transition: transform 0.2s;
    }}
    .float-wa:hover {{ transform: scale(1.1); }}
    
    /* PROGRESO GAMIFICADO */
    .progress-line {{ width: 100%; height: 4px; background: #eee; }}
    .progress-fill {{ height: 100%; width: {porcentaje_barra}%; background: {color_barra}; transition: width 0.5s; }}
    
    /* AJUSTE CHAT */
    .stChatMessage {{ background-color: #f1f3f4; border-radius: 15px; border: none; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>PEDRO BRAVIN S.A.</span>
            <span>🇦🇷 ENVÍOS A TODO EL PAÍS</span>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{nombre_nivel} {desc_actual}% OFF</span>
                <div style="font-size:0.7rem; color:#666; margin-top:2px;">Precios + IVA</div>
            </div>
            <div class="price-tag">${total_final:,.0f}</div>
        </div>
        <div class="progress-line"><div class="progress-fill"></div></div>
    </div>
    
    <a href="{link_wa_float}" class="float-wa" target="_blank">
        <i class="fa-brands fa-whatsapp"></i>
    </a>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR (DETALLE DEL CARRO)
# ==========================================
with st.sidebar:
    st.header(f"🛒 TU CARRITO ({len(st.session_state.cart)})")
    if not st.session_state.cart:
        st.caption("Tu acopio está vacío.")
    else:
        for i, item in enumerate(st.session_state.cart):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{item['cantidad']}x** {item['producto']}")
                st.caption(f"${item['subtotal']:,.0f}")
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
        st.divider()
        st.metric("TOTAL A PAGAR (+IVA)", f"${total_final:,.0f}")
        st.caption("✅ Descuento aplicado")
        if st.button("🗑️ Vaciar Todo"):
            st.session_state.cart = []; st.rerun()

# ==========================================
# 6. CEREBRO IA (KNOW-HOW + CROSS-SELL)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("⚠️ FALTA API KEY")

sys_prompt = f"""
ROL: Eres Miguel, vendedor experto de Pedro Bravin S.A.
BASE DE DATOS REAL: {csv_context}
ZONA DE ENVÍO GRATIS: {CIUDADES_GRATIS}

🎯 ESTRATEGIA DE VENTA (UP-SELL & CROSS-SELL):
- Tu objetivo es AUMENTAR EL TICKET. No solo tomes pedidos, SUGIERE complementos.
- Si piden CHAPAS -> Ofrece TORNILLOS, AISLANTE o CUMBRERAS.
- Si piden PERFILES -> Ofrece ELECTRODOS o DISCOS DE CORTE.
- Si piden HIERRO -> Ofrece ALAMBRE DE ATAR o CLAVOS.
- Sé sutil pero directo: "¿Te agrego los tornillos para esas chapas? Aprovechá el flete."

🛑 REGLAS TÉCNICAS (KNOW-HOW INTOCABLE):
1. **LARGOS:** Caños/Tubos = 6.40m. Perfiles/Hierros Construcción = 12m. Resto = 6m.
2. **UNIDADES:** Clavos/Alambre = KG. Planchuelas = UNIDAD. Mallas = UNIDAD.
3. **CHAPAS:** Sin corte = por metro. T101 = COD 6. Acanalada = COD 4.
4. **FLETE:** Cerca = Gratis. Lejos = (KM*2*0.85*DOLAR).

FORMATO RESPUESTA:
- Confirma qué agregaste.
- Sugiere el Cross-Sell (si aplica).
- Comando oculto: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
    st.session_state.chat_session = model.start_chat(history=[])

def analizar_imagen_vision(imagen):
    prompt_vision = "Analiza lista. Aplica reglas técnicas (Caños 6.40m, Perfiles 12m). Genera comandos [ADD:...]."
    response = st.session_state.chat_session.send_message([prompt_vision, imagen])
    return response.text

# ==========================================
# 7. INTERFAZ PRINCIPAL (CHAT + UPLOAD)
# ==========================================

# Zona de Carga Rápida (Estilo App)
with st.expander("📷 **¿Tenés una lista? Subí la foto acá**", expanded=False):
    uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if uploaded_file:
        if st.button("Procesar Lista Ahora", type="primary"):
            image = Image.open(uploaded_file)
            with st.spinner("Analizando y cotizando..."):
                full_text = analizar_imagen_vision(image)
                items = parsear_ordenes_bot(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                log_interaction("FOTO SUBIDA", total_final)
                st.rerun()

# Historial
for msg in st.session_state.messages:
    if msg["role"] != "system":
        content_clean = re.sub(r'\[ADD:.*?\]', '', msg["content"])
        if content_clean.strip():
            avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
            st.chat_message(msg["role"], avatar=avatar).markdown(content_clean)

# Input
if prompt := st.chat_input("Escribí tu pedido (Ej: 10 perfiles y chapas)"):
    if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
    if random.random() > 0.7: st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    with st.chat_message("assistant", avatar="👷‍♂️"):
        with st.spinner("Cotizando..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                full_text = response.text
                items = parsear_ordenes_bot(full_text)
                display_text = re.sub(r'\[ADD:.*?\]', '', full_text)
                st.markdown(display_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                # Logueo
                total_nuevo = sum(i['subtotal'] for i in st.session_state.cart) * (1 - (desc_actual/100))
                log_interaction(prompt, total_nuevo)
                if items: st.rerun()
            except Exception as e: st.error(f"Error: {e}")

if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN"): st.dataframe(pd.DataFrame(st.session_state.log_data))
