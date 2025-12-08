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
import os
from PIL import Image
from bs4 import BeautifulSoup
import streamlit.components.v1 as components 

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎯 METAS DE VENTA (GAMIFICACIÓN)
META_MAXIMA = 2500000
META_MEDIA  = 1500000
META_BASE   = 800000

# ==========================================
# 2. MOTOR INVISIBLE
# ==========================================
@st.cache_data(ttl=3600)
def obtener_dolar_bna():
    url = "https://www.bna.com.ar/Personas"
    backup = 1060.00
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            target = soup.find(string=re.compile("Dolar U.S.A"))
            if target:
                row = target.find_parent('tr')
                cols = row.find_all('td')
                if len(cols) >= 3:
                    return float(cols[2].get_text().replace(',', '.'))
        return backup
    except: return backup

DOLAR_BNA = obtener_dolar_bna() 
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"
URL_FORM_GOOGLE = "" 

# ⏱️ TIEMPO CORTO (3 MINUTOS) -> PRESIÓN TEMU
MINUTOS_OFERTA = 3

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

TOASTS_EXITO = ["🔥 ¡PRECIO CONGELADO!", "💰 ¡AHORRO ACTIVADO!", "📦 ¡STOCK RESERVADO!", "🚀 ¡VAMOS!"]

# ==========================================
# 3. ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None
if "discount_tier_reached" not in st.session_state: st.session_state.discount_tier_reached = 0

if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)

if "messages" not in st.session_state:
    # SALUDO INICIAL
    saludo = """
🦁 **Soy Miguel.** Dólar actualizado. Stock disponible.

👇 **PASAME TU PEDIDO YA** (Escribí o tocá **➕** para subir foto).
*¡El precio se congela por 3 minutos!* ⏳
    """
    st.session_state.messages = [{"role": "assistant", "content": saludo}]

# ==========================================
# 4. BACKEND
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try: return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

csv_context = load_data()

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE:
        try: requests.post(URL_FORM_GOOGLE, data={'entry.xxxxxx': str(cliente), 'entry.xxxxxx': str(monto), 'entry.xxxxxx': str(oportunidad)}, timeout=1)
        except: pass

def log_interaction(user_text, monto):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Monto": monto})

def parsear_ordenes_bot(texto):
    items_nuevos = []
    for cant, prod, precio, tipo in re.findall(r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]', texto):
        item = {"cantidad": float(cant), "producto": prod.strip(), "precio_unit": float(precio), "subtotal": float(cant)*float(precio), "tipo": tipo.strip().upper()}
        st.session_state.cart.append(item)
        items_nuevos.append(item)
    return items_nuevos

def calcular_negocio():
    now = datetime.datetime.now()
    tiempo_restante = st.session_state.expiry_time - now
    segundos_restantes = int(tiempo_restante.total_seconds())
    activa = segundos_restantes > 0
    
    if activa:
        m, s = divmod(segundos_restantes, 60)
        reloj_init = f"{m:02d}:{s:02d}"
        color_reloj = "#2e7d32" if m > 1 else "#d32f2f" # Rojo si falta poco
    else:
        reloj_init = "00:00"
        color_reloj = "#b0bec5"

    bruto = sum(i['subtotal'] for i in st.session_state.cart)
    desc_base = 0; desc_extra = 0; nivel_texto = "LISTA"; color = "#546e7a"; meta = META_BASE
    
    tipos = [x['tipo'] for x in st.session_state.cart]
    tiene_chapa = any("CHAPA" in t for t in tipos)
    tiene_perfil = any("PERFIL" in t for t in tipos)
    tiene_acero = any(t in ["HIERRO", "MALLA", "CLAVOS", "ALAMBRE", "PERFIL", "CHAPA", "TUBO", "CAÑO"] for t in tipos)
    tiene_pintura = any("PINTURA" in t or "ACCESORIO" in t or "ELECTRODO" in t for t in tipos)

    if activa:
        if bruto > META_MAXIMA: desc_base = 15; nivel_texto = "PARTNER MAX"; color = "#6200ea"; meta = 0
        elif bruto > META_MEDIA: desc_base = 12; nivel_texto = "CONSTRUCTOR"; color = "#d32f2f"; meta = META_MAXIMA
        elif bruto > META_BASE: desc_base = 10; nivel_texto = "OBRA"; color = "#f57c00"; meta = META_MEDIA
        else: desc_base = 3; nivel_texto = "CONTADO"; color = "#2e7d32"; meta = META_BASE

        boosters = []
        if tiene_chapa and tiene_perfil: desc_extra += 3; boosters.append("KIT TECHO")
        elif tiene_acero and tiene_pintura: desc_extra += 2; boosters.append("PACK TERM.")
            
        desc_total = min(desc_base + desc_extra, 18)
        if desc_extra > 0: 
            nivel_texto = f"{nivel_texto} + {' '.join(boosters)}"
            if desc_total >= 15: color = "#6200ea" 
    else:
        desc_total = 0; nivel_texto = "EXPIRADO"; color = "#455a64"

    neto = bruto * (1 - (desc_total/100))
    ahorro_total = bruto - neto
    return bruto, neto, desc_total, color, nivel_texto, meta, segundos_restantes, activa, color_reloj, reloj_init, ahorro_total

def generar_link_wa(total):
    txt = "HOLA, CONFIRMO PEDIDO YA (Precios Congelados):\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 5. UI: HEADER AGRESIVO
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel, prox_meta, seg_restantes, oferta_viva, color_timer, reloj_python, dinero_ahorrado = calcular_negocio()
porcentaje_barra = 100
if prox_meta > 0: porcentaje_barra = min((subtotal / prox_meta) * 100, 100)

display_precio = f"${total_final:,.0f}" if subtotal > 0 else "COTIZAR"
display_iva = "+IVA" if subtotal > 0 else ""
display_badge = nombre_nivel[:25] + "..." if len(nombre_nivel) > 25 and subtotal > 0 else (nombre_nivel if subtotal > 0 else "⚡ 3% OFF")

if dinero_ahorrado > 0:
    subtext_badge = f"🔥 AHORRAS: ${dinero_ahorrado:,.0f}"
else:
    subtext_badge = "TIEMPO LIMITADO"

header_html = f"""
    <style>
    /* LIMPIEZA */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    
    /* LAYOUT OPTIMIZADO PARA MÓVIL */
    .block-container {{ padding-top: 130px !important; padding-bottom: 100px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    
    /* INPUT CHAT SLIM */
    [data-testid="stBottomBlock"], [data-testid="stChatInput"] {{ 
        position: fixed; bottom: 0; left: 0; width: 100%; 
        background: white; padding: 5px 10px !important; 
        z-index: 99999; border-top: 1px solid #eee; 
    }}
    .stChatInputContainer textarea {{ min-height: 38px !important; height: 38px !important; padding: 8px !important; }}

    /* HEADER */
    .fixed-header {{ position: fixed; top: 0; left: 0; width: 100%; background: #fff; z-index: 99990; border-bottom: 4px solid {color_barra}; height: 95px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
    
    /* ANIMACIONES */
    @keyframes heartbeat {{ 0% {{ transform: scale(1); }} 15% {{ transform: scale(1.05); }} 30% {{ transform: scale(1); }} 45% {{ transform: scale(1.05); }} 60% {{ transform: scale(1); }} }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    
    .price-tag {{ font-weight: 900; color: #111; font-size: 1.4rem; animation: heartbeat 2s infinite; }}
    .badge {{ background: {color_barra}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 900; font-size: 0.75rem; text-transform: uppercase; }}
    
    /* BARRA PROGRESO */
    .progress-container {{ width: 100%; height: 6px; background: #eee; position: absolute; bottom: 0; }}
    .progress-bar {{ 
        height: 100%; width: {porcentaje_barra}%; background: {color_barra}; transition: width 0.5s ease-out; 
        background-image: linear-gradient(45deg,rgba(255,255,255,.3) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.3) 50%,rgba(255,255,255,.3) 75%,transparent 75%,transparent);
        background-size: 1rem 1rem; animation: progress-stripes 0.5s linear infinite;
    }}
    @keyframes progress-stripes {{ from {{ background-position: 1rem 0; }} to {{ background-position: 0 0; }} }}

    .top-strip {{ background: #000; color: #fff; padding: 4px 10px; display: flex; justify-content: space-between; font-size: 0.7rem; align-items: center; font-weight: bold; letter-spacing: 0.5px; }}
    .cart-summary {{ padding: 5px 15px; display: flex; justify-content: space-between; align-items: center; height: 60px; }}
    .timer-box {{ color: {color_timer}; background: #fff; padding: 1px 6px; border-radius: 3px; font-weight: 900; }}
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {{ position: fixed; top: 95px; left: 0; width: 100%; background: #ffffff; z-index: 99980; padding-top: 2px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 6px; font-weight: bold; font-size: 0.75rem; }}
    
    /* BOTÓN FLOTANTE ESTILO WHATSAPP (EL +) */
    div[data-testid="stPopover"] {{
        position: fixed; bottom: 65px; left: 10px; z-index: 200000;
        width: auto;
    }}
    div[data-testid="stPopover"] button {{
        border-radius: 50%; width: 45px; height: 45px;
        background-color: #25D366; color: white; border: 2px solid white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        display: flex; align-items: center; justify-content: center; font-size: 20px;
        animation: pulse-green-btn 2s infinite;
    }}
    @keyframes pulse-green-btn {{ 0% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(37, 211, 102, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }} }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <div>⏱️ EXPIRA: <span id="countdown_display" class="timer-box">{reloj_python}</span></div>
            <div style="color:#FFD700;">🦁 PEDRO BRAVIN S.A.</div>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{display_badge}</span>
                <div style="font-size:0.7rem; color:{color_barra}; font-weight:800; margin-top:2px; animation: heartbeat 1.5s infinite;">{subtext_badge}</div>
            </div>
            <div class="price-tag">{display_precio}<span style="font-size:0.8rem; font-weight:400; color:#666;">{display_iva}</span></div>
        </div>
        <div class="progress-container"><div class="progress-bar"></div></div>
    </div>
    <script>
    (function() {{
        if (window.miIntervalo) clearInterval(window.miIntervalo); var duration = {seg_restantes}; var display = document.getElementById("countdown_display");
        function updateTimer() {{
            var m = parseInt(duration / 60, 10); var s = parseInt(duration % 60, 10); m = m < 10 ? "0" + m : m; s = s < 10 ? "0" + s : s;
            if (display) display.textContent = m + ":" + s;
            if (--duration < 0) {{ duration = 0; if (window.miIntervalo) clearInterval(window.miIntervalo); }}
        }}
        if (duration > 0) {{ updateTimer(); window.miIntervalo = setInterval(updateTimer, 1000); }}
    }})();
    </script>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 6. CEREBRO IA (REGLAS + LOGÍSTICA COMPLETA)
# ==========================================
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try: api_key = st.secrets["GOOGLE_API_KEY"]
        except: pass
    if api_key: genai.configure(api_key=api_key)
except: pass

sys_prompt = f"""
ROL: Miguel, vendedor experto de Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}
DOLAR: {DOLAR_BNA}

📏 **CATÁLOGO TÉCNICO (ESTRICTO):**
- **12m:** Perfil C, IPN, UPN, ADN.
- **6.40m:** Caños (Mecánico, Epoxi, Galvanizado, Schedule).
- **6m:** Tubos Estructurales, Hierros, Ángulos, Planchuelas.
- **CHAPA T90:** Única medida 13m.
- **CHAPA COLOR:** Por metro.
- **CINCALUM:** Por metro (Ref Cod 4/6).

🚚 **LOGÍSTICA Y ENVÍOS:**
1. **ZONA GRATIS:** Si la ciudad está en {CIUDADES_GRATIS} -> ENVÍO $0.
2. **OTRAS ZONAS:** El flete se cobra.
   - Cálculo: `KM_TOTAL (IDA+VUELTA) * 0.85 USD * {DOLAR_BNA} * 1.21 (IVA)`.
3. **ACOPIO:** "Comprá hoy, retirá en hasta **6 MESES** sin cargo".

⛔ **PROTOCOLO SNIPER:**
1. **BREVEDAD:** Max 15 palabras. Directo.
2. **CONFIRMACIÓN:** SOLO agrega `[ADD:...]` si el cliente dice "SÍ/CARGALO".
   - *Ejemplo:* Si piden precio, dalo y remata: "**¿Te separo el stock?**".
3. **UPSELL MATEMÁTICO:** "Te faltan $X para el próximo descuento. ¿Sumamos pintura?".
4. **ANTI-AMBIGÜEDAD:** Si falta medida, PREGUNTA.

SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO_FINAL_PESOS:TIPO]
"""

if "chat_session" not in st.session_state and "api_key" in locals() and api_key:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_input(contenido, es_imagen=False):
    if "chat_session" in st.session_state:
        msg = contenido
        prefix = ""
        if es_imagen: msg = ["COTIZA ESTO RÁPIDO. DETECTA OPORTUNIDADES DE COMBO.", contenido]
        prompt = f"{prefix}{msg}. (NOTA: Sé breve. Cotiza precios. NO AGREGUES sin confirmación)." if not es_imagen else msg
        return st.session_state.chat_session.send_message(prompt).text
    return "Error: Chat off."

# ==========================================
# 7. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])
spacer = '<div style="height: 20px;"></div>'

# --- 💡 BOTÓN FLOTANTE "FINALIZAR" (SI HAY CARRITO) ---
if len(st.session_state.cart) > 0 and oferta_viva:
    st.markdown(f"""
    <div style="position:fixed; bottom:75px; right:10px; left:10px; z-index:200000; display:flex; justify-content:center;">
        <a href="{generar_link_wa(total_final)}" target="_blank" style="
            background: linear-gradient(90deg, #ff0000, #ff4d4d); color: white; 
            padding: 12px 30px; border-radius: 50px; width: 100%; text-align:center;
            font-weight: 900; text-decoration: none; box-shadow: 0 5px 20px rgba(255,0,0,0.6);
            border: 2px solid #fff; font-size: 1rem; animation: pulse-red 1.5s infinite;">
            🔥 PAGAR AHORA: ${total_final:,.0f} ➔
        </a>
    </div>
    <style>@keyframes pulse-red {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.05); }} 100% {{ transform: scale(1); }} }}</style>
    """, unsafe_allow_html=True)

with tab1:
    st.markdown(spacer, unsafe_allow_html=True)
    if not oferta_viva:
        st.error("⚠️ PRECIOS EXPIRADOS")
        if st.button("🔄 RECARGAR PRECIOS", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.rerun()

    # POP-UP AGRESIVO DE OPORTUNIDAD
    if 0 < prox_meta - subtotal < 150000 and oferta_viva:
        st.toast(f"🚨 ¡FALTAN ${prox_meta - subtotal:,.0f} PARA DESCUENTO! SUMÁ ALGO CHICO.", icon="🔥")

    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    with st.container():
        c1, c2 = st.columns([1.5, 8.5])
        with c1:
            # BOTÓN + CON ESTILO WHATSAPP
            with st.popover("➕", use_container_width=False):
                st.caption("Subir Foto")
                img = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
                if img:
                    fid = f"{img.name}_{img.size}"
                    if st.session_state.last_processed_file != fid:
                        with st.spinner("⚡ Procesando..."):
                            txt = procesar_input(Image.open(img), True)
                            news = parsear_ordenes_bot(txt)
                            st.session_state.messages.append({"role": "assistant", "content": txt})
                            st.session_state.last_processed_file = fid
                            if news: st.balloons()
                            st.rerun()

    if p := st.chat_input("Escribí acá..."):
        if p == "#admin": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        st.session_state.messages.append({"role": "user", "content": p})
        st.chat_message("user").markdown(p)
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Calculando..."):
                try:
                    if "chat_session" in st.session_state:
                        res = st.session_state.chat_session.send_message(f"{p}. (CORTITO Y AL PIE).").text
                        news = parsear_ordenes_bot(res)
                        display = re.sub(r'\[ADD:.*?\]', '', res)
                        st.markdown(display)
                        
                        if news: 
                            st.toast(random.choice(TOASTS_EXITO), icon='🔥')
                            if desc_actual >= 12: st.balloons()
                        
                        st.session_state.messages.append({"role": "assistant", "content": res})
                        if news: time.sleep(1); st.rerun()
                except: st.error("Error.")

with tab2:
    st.markdown(spacer, unsafe_allow_html=True)
    if not st.session_state.cart:
        st.info("Carrito vacío. Agregá items para ver el precio final.")
    else:
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                c1.markdown(f"**{item['producto']}**\n<span style='color:grey;font-size:0.8em'>${item['precio_unit']:,.0f} unit</span>", unsafe_allow_html=True)
                item['cantidad'] = c2.number_input("Cant", 0.0, value=float(item['cantidad']), key=f"q_{i}", label_visibility="collapsed")
                item['subtotal'] = item['cantidad'] * item['precio_unit']
                if c3.button("🗑️", key=f"d_{i}"): st.session_state.cart.pop(i); st.rerun()
                if item['cantidad'] == 0: st.session_state.cart.pop(i); st.rerun()
                st.markdown("---")
        
        # BOTÓN DE PAGO GIGANTE EN PESTAÑA CARRITO (Backup)
        st.markdown(f"""
        <a href="{generar_link_wa(total_final)}" target="_blank" style="
            display:block; width:100%; background: linear-gradient(45deg, #25D366, #128C7E); 
            color:white; margin-top:20px; text-align:center; padding:20px; border-radius:12px; 
            text-decoration:none; font-weight:900; font-size:1.5rem; text-transform:uppercase;
            box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4); border: 2px solid #fff;
            animation: pulse-green 1.5s infinite;">
            🚀 CONFIRMAR PEDIDO <br><span style="font-size:0.8rem; opacity:0.8">CONGELAR PRECIO AHORA</span>
        </a>
        <style>@keyframes pulse-green {{ 0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }} 70% {{ transform: scale(1.02); box-shadow: 0 0 0 15px rgba(37, 211, 102, 0); }} 100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }} }}</style>
        """, unsafe_allow_html=True)
        
        if st.button("Vaciar Carrito", use_container_width=True): st.session_state.cart = []; st.rerun()

# --- SCRIPT AUTO-SCROLL (ARREGLADO) ---
components.html("""
    <script>
        function scrollDown() {
            var body = window.parent.document.querySelector(".stAppDeployButton").parentElement;
            if(!body) body = window.parent.document.querySelector(".main");
            if(body) body.scrollTop = body.scrollHeight;
        }
        setInterval(scrollDown, 1000);
    </script>
""", height=0)

if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
