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

# INTENTO DE IMPORTAR MICROFONO (Si falla, la app sigue funcionando)
try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

# ==========================================
# 1. CONFIGURACIÓN E INFRAESTRUCTURA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded" # Expandido para ver el botón eliminar
)

# --- VARIABLES DE NEGOCIO (ANCHOR POINTS) ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"

# --- CONEXIÓN REAL GOOGLE SHEETS ---
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"

# --- LOGS GOOGLE FORMS ---
URL_FORM_GOOGLE = "" # 🔴 PEGAR TU LINK AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# --- ZONA DE BENEFICIO LOGÍSTICO ---
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
# 2. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\nCotizo aceros directo de fábrica. Hablame, escribí o subí foto."}]

# ==========================================
# 3. BACKEND (LÓGICA PYTHON PURA)
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
    # Detecta comandos ocultos: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
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
    return items_agregados # Retorna la lista de lo nuevo

def calcular_negocio():
    bruto = sum(item['subtotal'] for item in st.session_state.cart)
    descuento = 3
    color = "#546e7a" # Gris azulado profesional
    texto_nivel = "INICIAL"
    
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart)
    
    if tiene_gancho:
        descuento = 15; texto_nivel = "🔥 MAYORISTA"; color = "#d32f2f" # Rojo
    elif bruto > 3000000:
        descuento = 15; texto_nivel = "👑 PARTNER"; color = "#6200ea" # Violeta
    elif bruto > 1500000:
        descuento = 10; texto_nivel = "🏗️ OBRA"; color = "#f57c00" # Naranja
        
    neto = bruto * (1 - (descuento/100))
    return bruto, neto, descuento, color, texto_nivel

def generar_link_whatsapp(total):
    texto = "Hola Martín, quiero CONGELAR este pedido:\n"
    for item in st.session_state.cart:
        texto += f"▪ {item['cantidad']}x {item['producto']}\n"
    texto += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    texto += f"\n(Condición: {CONDICION_PAGO})"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(texto)}"

# ==========================================
# 4. UI: ESTILO MÓVIL (HEADER + FAB)
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel = calcular_negocio()
porcentaje_barra = min(total_final / 3000000 * 100, 100) if total_final < 3000000 else 100
link_wa_float = generar_link_whatsapp(total_final)

st.markdown(f"""
    <style>
    /* Ajustes Generales Móvil */
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{ padding-top: 130px !important; padding-bottom: 90px !important; }}
    
    /* HEADER FIJO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: white; z-index: 99999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-bottom: 3px solid {color_barra};
    }}
    .top-strip {{
        background: #232f3e; color: white; padding: 6px 15px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.7rem; letter-spacing: 0.5px;
    }}
    .cart-summary {{
        padding: 8px 15px; display: flex; justify-content: space-between; align-items: center;
    }}
    .price-tag {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
    .badge {{ 
        background: {color_barra}; color: white; padding: 3px 8px; 
        border-radius: 10px; font-size: 0.7rem; font-weight: bold; 
    }}
    
    /* BOTÓN WHATSAPP FLOTANTE */
    .float-wa {{
        position: fixed; width: 55px; height: 55px;
        bottom: 80px; right: 20px;
        background-color: #25d366; color: #FFF;
        border-radius: 50px; text-align: center; font-size: 28px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
        z-index: 10000; display: flex; align-items: center; justify-content: center;
        text-decoration: none; transition: transform 0.2s;
    }}
    .float-wa:hover {{ transform: scale(1.1); }}
    
    /* BARRA PROGRESO */
    .progress-line {{ width: 100%; height: 4px; background: #eee; }}
    .progress-fill {{ height: 100%; width: {porcentaje_barra}%; background: {color_barra}; transition: width 0.5s; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>PEDRO BRAVIN S.A.</span>
            <span>COTIZADOR OFICIAL</span>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{nombre_nivel} {desc_actual}% OFF</span>
            </div>
            <div class="price-tag">${total_final:,.0f} <span style="font-size:0.7rem; font-weight:400; color:#666;">+IVA</span></div>
        </div>
        <div class="progress-line"><div class="progress-fill"></div></div>
    </div>
    
    <a href="{link_wa_float}" class="float-wa" target="_blank">
        <i class="fa-brands fa-whatsapp"></i>
    </a>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR (CARRITO CON BOTON ELIMINAR)
# ==========================================
with st.sidebar:
    st.header(f"🛒 CARRITO ({len(st.session_state.cart)})")
    if not st.session_state.cart:
        st.info("Tu acopio está vacío.")
    else:
        # AQUI ESTA LA FUNCION DE ELIMINAR MANUALMENTE
        for i, item in enumerate(st.session_state.cart):
            st.markdown(f"""
            <div style="background:#f0f2f6; padding:10px; border-radius:8px; margin-bottom:5px;">
                <div style="font-weight:bold;">{item['cantidad']}x {item['producto']}</div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#666;">${item['subtotal']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # El botón de eliminar nativo de Streamlit
            if st.button("🗑️ Eliminar item", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
                
        st.divider()
        st.metric("TOTAL A PAGAR (+IVA)", f"${total_final:,.0f}")
        st.caption(f"✅ Descuento: {desc_actual}%")
        if st.button("🗑️ VACIAR TODO EL PEDIDO"):
            st.session_state.cart = []; st.rerun()

# ==========================================
# 6. CEREBRO IA (REGLAS DE NEGOCIO INMUTABLES)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("⚠️ FALTA API KEY")

# 🔒 SECCIÓN BLINDADA: NO MODIFICAR SIN AUTORIZACIÓN 🔒
sys_prompt = f"""
ROL: Miguel, vendedor técnico Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

📜 REGLAS DE NEGOCIO INMUTABLES (DO NOT TOUCH):
1. **LARGOS COMERCIALES:**
   - **12.00 METROS:** Perfiles C, Hierro Construcción (ADN/Nervado), Lisos AL 220, UPN/IPN (>=80).
   - **6.40 METROS:** Caños y Tubos redondos (Epoxi, Galvanizado, Schedule, Mecánico).
   - **6.00 METROS:** Tubos Estructurales (Cuad/Rect), Ángulos, Planchuelas, Hierros T, UPN/IPN (<80).
2. **UNIDADES DE VENTA:**
   - Clavos / Alambres Atar = **KG**.
   - Planchuelas Galv / Mallas = **UNIDAD**.
   - Alambres Agro = **ROLLO MAYOR**.
   - Aislante = m2 (menor) o Rollo (mayor).
3. **CHAPAS (CÓDIGOS):**
   - Sin cortes especificados = Cotizar por **METRO LINEAL**.
   - "Acanalada" = Buscar **COD 4** (o CODIGO 4).
   - "Trapezoidal/T101" = Buscar **COD 6** (o CODIGO 6).
4. **LOGÍSTICA (CRÍTICO):**
   - **ZONA BENEFICIO ({CIUDADES_GRATIS}):** ¡OFRECE ENVÍO GRATIS! Es tu gancho de venta principal.
   - **RESTO DEL PAÍS:** Calcula estimado: (KM * 2 * {COSTO_FLETE_USD} * {DOLAR_BNA}). Resultado + IVA. 
     *Aclara:* "Costo estimado. Martín coordina el envío final."
   - **RETIROS:** Di solo "Retiro en Planta (A coordinar)". No des direcciones exactas.
5. **COMERCIAL:**
   - Pago: {CONDICION_PAGO}.
   - Acopio: 6 Meses (Aclarar "conversable").

INSTRUCCIONES DE SALIDA:
- Sé breve.
- CROSS-SELL: Si llevan chapa, ofrece tornillos/aislante.
- Si piden metros de algo que viene en barras, calcula las barras y aclara: "Te calculé X barras de Y metros".
- FORMATO COMANDO: [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. APLICA REGLAS INMUTABLES (Largos 6/6.40/12m y Códigos). Genera [ADD...]. SOLO CONFIRMA.", img]).text

# ==========================================
# 7. INTERFAZ PRINCIPAL (CHAT + UPLOAD + MIC)
# ==========================================

# 1. CONTROLES SUPERIORES (FOTO + MIC)
c1, c2 = st.columns([1, 1])

with c1:
    with st.expander("📷 **SUBIR FOTO**", expanded=False):
        uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_file:
            if st.button("⚡ PROCESAR", type="primary"):
                with st.spinner("Analizando..."):
                    image = Image.open(uploaded_file)
                    full_text = procesar_vision(image)
                    if parsear_ordenes_bot(full_text):
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        log_interaction("FOTO SUBIDA", total_final)
                        st.rerun()
with c2:
    # 🎤 BOTÓN DE MICRÓFONO
    if MIC_AVAILABLE:
        st.write("🎤 **HABLAR**")
        audio_text = speech_to_text(language='es', start_prompt="🔴 GRABAR", stop_prompt="⏹️ LISTO", just_once=True, key='mic')
    else:
        st.warning("Instalar: pip install streamlit-mic-recorder")
        audio_text = None

# Historial de Chat
for msg in st.session_state.messages:
    if msg["role"] != "system":
        content_clean = re.sub(r'\[ADD:.*?\]', '', msg["content"])
        if content_clean.strip():
            avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
            st.chat_message(msg["role"], avatar=avatar).markdown(content_clean)

# LÓGICA DE INPUT (TEXTO O AUDIO)
prompt = None
if audio_text:
    prompt = audio_text # Si vino del mic
elif user_input := st.chat_input("Escribí tu pedido..."):
    prompt = user_input # Si vino del teclado

if prompt:
    if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
    if random.random() > 0.7: st.toast(random.choice(FRASES_FOMO), icon='🔥')

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    with st.chat_message("assistant", avatar="👷‍♂️"):
        with st.spinner("Cotizando..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                full_text = response.text
                
                # Procesamos y obtenemos los items nuevos
                items_nuevos = parsear_ordenes_bot(full_text)
                
                display_text = re.sub(r'\[ADD:.*?\]', '', full_text)
                st.markdown(display_text)
                
                # --- AQUÍ ESTÁ EL DETALLE QUE PEDISTE (TICKET EN EL CHAT) ---
                if items_nuevos:
                    st.markdown("---")
                    st.markdown("📝 **DETALLE DE LO AGREGADO:**")
                    # Creamos un DF bonito para mostrar solo lo nuevo
                    df_ticket = pd.DataFrame(items_nuevos)
                    st.dataframe(
                        df_ticket[['cantidad', 'producto', 'precio_unit']], 
                        hide_index=True,
                        column_config={
                            "precio_unit": st.column_config.NumberColumn("Precio Unit.", format="$%d")
                        }
                    )
                    st.markdown("---")
                # -------------------------------------------------------------
                
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
                # Logueo
                total_nuevo = sum(i['subtotal'] for i in st.session_state.cart) * (1 - (desc_actual/100))
                log_interaction(prompt, total_nuevo)
                
                # Recargamos para actualizar Carrito y Header
                if items_nuevos:
                    time.sleep(1) # Le damos un segundito para que lea
                    st.rerun() 
            except Exception as e: st.error(f"Error: {e}")

if st.session_state.admin_mode:
    with st.expander("🔐 ADMIN"): st.dataframe(pd.DataFrame(st.session_state.log_data))
