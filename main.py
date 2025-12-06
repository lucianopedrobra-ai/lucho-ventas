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
# 1. CONFIGURACIÓN INNEGOCIABLE
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A. | Cotizador Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TUS VARIABLES DE NEGOCIO ---
DOLAR_BNA = 1060.00
COSTO_FLETE_KM_USD = 0.85 

# --- INFRAESTRUCTURA GOOGLE ---
URL_FORM_GOOGLE = ""  # 🔴 TU LINK DE GOOGLE FORMS AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- SHEETS (RECUPERADO) ---
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

FRASES_FOMO = [
    "🔥 Chapas: Quedan pocas unidades del lote.",
    "⚠️ Hierro: Alta rotación hoy.",
    "👀 3 Constructores están cotizando ahora.",
    "📉 Dólar estable: Buen momento para acopiar.",
    "🚚 Logística: Armado de reparto en proceso."
]

# ==========================================
# 2. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.** Cotizo directo de fábrica. Escribí tu pedido o subí una foto de tu lista."}]
# Variables calculadas globales para sincronizar barra y carrito
if "monto_total_global" not in st.session_state: st.session_state.monto_total_global = 0.0
if "nivel_actual_global" not in st.session_state: st.session_state.nivel_actual_global = 3

# ==========================================
# 3. FUNCIONES DE LÓGICA & BACKEND
# ==========================================

@st.cache_data(ttl=600)
def load_data():
    try:
        # Recuperamos la conexión real a tu CSV
        df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
        return df.to_csv(index=False)
    except Exception as e:
        return "Error DB: " + str(e)

csv_context = load_data()

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {
                ID_CAMPO_CLIENTE: str(cliente), 
                ID_CAMPO_MONTO: str(monto), 
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except: pass

def log_interaction(user_text, monto_real_carrito):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "BAJA"
    if monto_real_carrito > 1500000: opportunity = "🔥 ALTA"
    elif monto_real_carrito > 500000: opportunity = "MEDIA"
    
    st.session_state.log_data.append({
        "Fecha": timestamp, 
        "Usuario": user_text[:50], 
        "Oportunidad": opportunity, 
        "Monto": monto_real_carrito
    })
    
    thread = threading.Thread(
        target=enviar_a_google_form_background, 
        args=(user_text, monto_real_carrito, opportunity)
    )
    thread.daemon = True
    thread.start()

def parsear_ordenes_bot(texto_respuesta):
    # Detecta: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
    patron = r'\[ADD:(\d+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto_respuesta)
    items_agregados = []
    
    for cant, prod, precio, tipo in coincidencias:
        item = {
            "cantidad": int(cant),
            "producto": prod.strip(),
            "precio_unit": float(precio),
            "subtotal": int(cant) * float(precio),
            "tipo": tipo.strip().upper()
        }
        st.session_state.cart.append(item)
        items_agregados.append(item)
    return items_agregados

def calcular_negocio():
    """Función maestra de matemáticas. Sincroniza todo."""
    total_bruto = sum(item['subtotal'] for item in st.session_state.cart)
    
    # Lógica de Descuentos
    descuento = 3
    color = "#90a4ae" # Gris inicial
    texto_nivel = "INICIAL"
    
    # 1. Detectar productos gancho
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO'] for x in st.session_state.cart)
    
    # 2. Reglas de Escala
    if tiene_gancho:
        descuento = 15
        texto_nivel = "COMPETITIVO 🔥"
        color = "#d50000" # Rojo
    elif total_bruto > 3000000:
        descuento = 15
        texto_nivel = "PARTNER"
        color = "#6200ea" # Violeta
    elif total_bruto > 1500000:
        descuento = 10
        texto_nivel = "OBRA"
        color = "#ffa726" # Naranja
        
    total_neto = total_bruto * (1 - (descuento/100))
    
    # Actualizamos variables globales para la UI
    st.session_state.monto_total_global = total_neto
    st.session_state.nivel_actual_global = descuento
    
    return total_bruto, total_neto, descuento, color, texto_nivel

def generar_link_whatsapp(total):
    texto = "Hola Martín, confirmo pedido:\n"
    for item in st.session_state.cart:
        texto += f"▪ {item['cantidad']}x {item['producto']}\n"
    texto += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(texto)}"

# ==========================================
# 4. BARRA SUPERIOR (SINCRONIZADA)
# ==========================================
# Ejecutamos cálculo antes de mostrar nada
subtotal, total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
porcentaje_barra = min(total_final / 3000000 * 100, 100) if total_final < 3000000 else 100

st.markdown(f"""
    <style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 160px !important; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 99999;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}
    .top-strip {{
        background: #0f2c59; color: white; padding: 8px 15px;
        display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;
    }}
    .game-zone {{ padding: 10px 20px; background: #fafafa; border-bottom: 3px solid {color_barra}; }}
    .level-info {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
    .current-badge {{ 
        background: {color_barra}; color: white; padding: 4px 10px; border-radius: 12px; 
        font-weight: bold; font-size: 0.8rem;
    }}
    .custom-progress-bg {{ width: 100%; height: 10px; background: #e0e0e0; border-radius: 10px; }}
    .custom-progress-fill {{
        height: 100%; width: {porcentaje_barra}%; 
        background: {color_barra}; border-radius: 10px; transition: width 0.5s;
    }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>⚡ PEDRO BRAVIN S.A.</span>
            <span>PRECIOS WEB ESTIMADOS</span>
        </div>
        <div class="game-zone">
            <div class="level-info">
                <span class="current-badge">{nombre_nivel} | {desc_actual}% OFF</span>
                <span style="color:#333; font-weight:bold;">Total: ${total_final:,.0f}</span>
            </div>
            <div class="custom-progress-bg">
                <div class="custom-progress-fill"></div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR (CARRITO DE COMPRAS)
# ==========================================
with st.sidebar:
    st.header("🛒 TU ACOPIO")
    if not st.session_state.cart:
        st.info("Carro vacío. Pedile materiales a Miguel.")
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
        st.caption(f"Subtotal lista: ${subtotal:,.0f}")
        
        if desc_actual > 0:
            ahorro = subtotal - total_final
            st.success(f"🎉 Descuento {desc_actual}%: -${ahorro:,.0f}")
            
        st.metric("TOTAL FINAL (+IVA)", f"${total_final:,.0f}")
        
        link_wa = generar_link_whatsapp(total_final)
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="
                display:block; width:100%; background-color:#25D366; color:white; 
                text-align:center; padding:15px; border-radius:10px; 
                text-decoration:none; font-weight:bold; font-size:1.1rem;
                box-shadow: 0 4px 10px rgba(37,211,102,0.3);">
                ✅ CONFIRMAR CON MARTÍN
            </a>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Borrar todo"):
            st.session_state.cart = []
            st.rerun()

# ==========================================
# 6. CEREBRO IA (CONFIGURACIÓN)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("⚠️ FALTA API KEY")

sys_prompt = f"""
ROL: Eres Miguel, vendedor experto de Pedro Bravin S.A.
BASE DE DATOS REAL: {csv_context}
ZONA DE ENVÍO GRATIS: {CIUDADES_GRATIS}

OBJETIVO:
1. Leer lo que pide el cliente (texto o foto).
2. Buscar en la BASE DE DATOS el producto más cercano.
3. Generar COMANDOS OCULTOS para llenar el carrito.

COMANDO OBLIGATORIO PARA AGREGAR PRODUCTOS:
[ADD:CANTIDAD:NOMBRE_EXACTO_DB:PRECIO_NUMERICO:TIPO]
(El TIPO debe ser: CHAPA, PERFIL, HIERRO o VARIOS)

REGLAS DE VENTAS:
- NO sumes totales en el texto. Dilo: "Te lo cargo al carrito y ahí ves el descuento final".
- Fletes: Si es cerca de {CIUDADES_GRATIS}, di "Flete Bonificado". Si es lejos, di "Te calculo un costo logístico estimado".
- Sé breve y usa Bullets.

VISIÓN (SI RECIBES IMAGEN):
- Extrae todos los items de la lista manuscrita y genera los comandos [ADD...] masivamente.
"""

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
    st.session_state.chat_session = model.start_chat(history=[])

def analizar_imagen_vision(imagen):
    prompt_vision = "Analiza la imagen. Identifica productos y cantidades. Mapealos a mi DB y genera los comandos [ADD:...] para cada uno."
    response = st.session_state.chat_session.send_message([prompt_vision, imagen])
    return response.text

# ==========================================
# 7. INTERFAZ CHAT CENTRAL
# ==========================================

# Historial
for msg in st.session_state.messages:
    if msg["role"] != "system":
        # Limpiamos los tags técnicos para que no se vean feos
        content_clean = re.sub(r'\[ADD:.*?\]', '', msg["content"])
        if content_clean.strip():
            avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
            st.chat_message(msg["role"], avatar=avatar).markdown(content_clean)

# Uploader de Fotos
with st.expander("📸 Subir foto de lista de materiales"):
    uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"])
    if uploaded_file and st.button("Procesar Lista"):
        image = Image.open(uploaded_file)
        st.image(image, width=150)
        with st.spinner("Analizando lista..."):
            full_text = analizar_imagen_vision(image)
            items = parsear_ordenes_bot(full_text)
            
            clean_text = re.sub(r'\[ADD:.*?\]', '', full_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            
            # Logueamos la acción con el total actualizado
            log_interaction("SUBIDA DE FOTO", st.session_state.monto_total_global)
            st.rerun()

# Input Texto
if prompt := st.chat_input("Ej: 20 chapas C25..."):
    if prompt == "#admin-miguel":
        st.session_state.admin_mode = not st.session_state.admin_mode
        st.rerun()

    if random.random() > 0.8:
        st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    with st.chat_message("assistant", avatar="👷‍♂️"):
        with st.spinner("Consultando stock..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                full_text = response.text
                
                # Procesar lógica
                items = parsear_ordenes_bot(full_text)
                
                # Visualización limpia
                display_text = re.sub(r'\[ADD:.*?\]', '', full_text)
                st.markdown(display_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                # Logueamos con el NUEVO total del carrito
                # Forzamos recálculo rápido para el log
                total_para_log = sum(i['subtotal'] for i in st.session_state.cart) 
                log_interaction(prompt, total_para_log)
                
                if items:
                    st.rerun() # Refresca para actualizar Sidebar y Barra Superior
                    
            except Exception as e:
                st.error(f"Error: {e}")

# Admin Panel
if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN LOGS"):
        st.dataframe(pd.DataFrame(st.session_state.log_data))
