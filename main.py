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

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎯 METAS DE VENTA
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

MINUTOS_OFERTA = 10 
CIUDADES_GRATIS = ["EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", "PIAMONTE", "VILA", "SAN FRANCISCO"]
TOASTS_EXITO = ["✨ ¡Excelente elección!", "🔥 ¡Te congelé este precio!", "💎 ¡Producto reservado!", "🚀 ¡Sumamos puntos!"]

# ==========================================
# 3. ESTADO DE LA SESIÓN
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None
if "discount_tier_reached" not in st.session_state: st.session_state.discount_tier_reached = 0

if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)

if "messages" not in st.session_state:
    saludo_inicial = """
👋 **¡Hola! Soy Miguel, tu asistente experto.**
Estoy conectado al stock en tiempo real y tengo el dólar actualizado.

🚀 **¿CÓMO PODEMOS COTIZAR?**
1. ✍️ **Escribime** la lista de materiales aquí abajo.
2. 📸 **Subí una foto** de tu papel escrito a mano (Tocá el botón **➕ Adjuntar**).

*¡Probá subir una foto, soy muy rápido!* 😉
    """
    st.session_state.messages = [{"role": "assistant", "content": saludo_inicial}]

# ==========================================
# 4. FUNCIONES BACKEND
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
        color_reloj = "#2e7d32" if m > 2 else "#d32f2f"
    else:
        reloj_init = "00:00"
        color_reloj = "#b0bec5"

    bruto = sum(i['subtotal'] for i in st.session_state.cart)
    desc_base = 0; desc_extra = 0; nivel_texto = "PRECIO LISTA"; color = "#546e7a"; meta = META_BASE
    
    tipos_en_carrito = [x['tipo'] for x in st.session_state.cart]
    tiene_chapa = any("CHAPA" in t for t in tipos_en_carrito)
    tiene_perfil = any("PERFIL" in t for t in tipos_en_carrito)
    tiene_acero = any(t in ["HIERRO", "MALLA", "CLAVOS", "ALAMBRE", "PERFIL", "CHAPA", "TUBO", "CAÑO"] for t in tipos_en_carrito)
    tiene_pintura = any("PINTURA" in t or "ACCESORIO" in t or "ELECTRODO" in t for t in tipos_en_carrito)

    if activa:
        if bruto > META_MAXIMA: desc_base = 15; nivel_texto = "PARTNER (15%)"; color = "#6200ea"; meta = 0
        elif bruto > META_MEDIA: desc_base = 12; nivel_texto = "CONSTRUCTOR (12%)"; color = "#d32f2f"; meta = META_MAXIMA
        elif bruto > META_BASE: desc_base = 10; nivel_texto = "OBRA (10%)"; color = "#f57c00"; meta = META_MEDIA
        else: desc_base = 3; nivel_texto = "CONTADO (3%)"; color = "#2e7d32"; meta = META_BASE

        boosters_activos = []
        if tiene_chapa and tiene_perfil: desc_extra += 3; boosters_activos.append("🏠 KIT TECHO")
        elif tiene_acero and tiene_pintura: desc_extra += 2; boosters_activos.append("🎨 PACK TERM.")
            
        desc_total = min(desc_base + desc_extra, 18)
        if desc_extra > 0: nivel_texto = f"{nivel_texto} + {' '.join(boosters_activos)}"; 
        if desc_total >= 15: color = "#6200ea"
    else:
        if bruto > META_MAXIMA: desc_total = 12; nivel_texto = "OFERTA EXPIRADA"; color = "#455a64"
        else: desc_total = 0; nivel_texto = "PRECIO LISTA"; color = "#455a64"

    neto = bruto * (1 - (desc_total/100))
    return bruto, neto, desc_total, color, nivel_texto, meta, segundos_restantes, activa, color_reloj, reloj_init

def generar_link_wa(total):
    txt = "Hola Martín, confirmar pedido:\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 5. UI: HEADER Y ESTILOS (CCS NUCLEAR PARA BORRAR BARRA BLANCA)
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel, prox_meta, seg_restantes, oferta_viva, color_timer, reloj_python = calcular_negocio()
porcentaje_barra = 100
if prox_meta > 0: porcentaje_barra = min((subtotal / prox_meta) * 100, 100)

display_precio = f"${total_final:,.0f}" if subtotal > 0 else "🛒 COTIZAR"
display_iva = "+IVA" if subtotal > 0 else ""
display_badge = nombre_nivel[:25] + "..." if len(nombre_nivel) > 25 and subtotal > 0 else (nombre_nivel if subtotal > 0 else "⚡ 3% OFF YA")
subtext_badge = f"Ahorro Total: {desc_actual}%" if (oferta_viva and subtotal > 0) else "TIEMPO LIMITADO"

header_html = f"""
    <style>
    /* 1. ELIMINAR BARRA BLANCA Y 3 PUNTOS (CRÍTICO) */
    header {{ visibility: hidden !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    #MainMenu {{ visibility: hidden !important; }}
    footer {{ visibility: hidden !important; }}
    
    /* 2. ESPACIO SUPERIOR EXTREMO (Para que la app baje y no la tape el modal web) */
    .block-container {{ 
        padding-top: 140px !important; 
        padding-bottom: 150px !important; 
    }}
    
    [data-testid="stSidebar"] {{ display: none; }} 
    
    /* 3. BARRA CHAT ESTILO WHATSAPP */
    [data-testid="stBottomBlock"], [data-testid="stChatInput"] {{
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: white; padding: 10px;
        z-index: 99999; border-top: 1px solid #eee;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }}

    /* 4. HEADER APP FIJO */
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: #ffffff; z-index: 99990;
        border-bottom: 4px solid {color_barra}; 
        height: 110px; overflow: hidden;
    }}
    
    /* 5. TABS FLOTANTES */
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 110px; left: 0; width: 100%; 
        background: #ffffff; z-index: 99980;
        display: flex; justify-content: space-around;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); 
        padding-bottom: 2px; padding-top: 5px;
    }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 8px; font-weight: bold; font-size: 0.8rem; }}

    .top-strip {{ background: #111; color: #fff; padding: 8px 15px; display: flex; justify-content: space-between; font-size: 0.7rem; align-items: center; height: 35px; }}
    .cart-summary {{ padding: 5px 15px; display: flex; justify-content: space-between; align-items: center; height: 70px; }}
    .price-tag {{ font-weight: 900; color: #333; white-space: nowrap; font-size: 1.4rem; }}
    .badge {{ background: {color_barra}; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 900; text-transform: uppercase; box-shadow: 0 2px 5px rgba(0,0,0,0.2); white-space: nowrap; }}
    
    @media only screen and (max-width: 600px) {{
        .price-tag {{ font-size: 1.2rem; }}
        .badge {{ font-size: 0.65rem; padding: 3px 6px; }}
        .cart-summary {{ padding: 5px 10px; }}
    }}
    
    .timer-container {{ display: flex; align-items: center; gap: 5px; }}
    .timer-box {{ color: {color_timer}; font-weight: 900; font-size: 0.8rem; background: #fff; padding: 1px 6px; border-radius: 4px; border: 1px solid {color_timer}; min-width: 45px; text-align: center; }}
    .progress-container {{ width: 100%; height: 5px; background: #eee; position: absolute; bottom: 0; }}
    .progress-bar {{ height: 100%; width: {porcentaje_barra}%; background: {color_barra}; transition: width 0.8s ease-out; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <div class="timer-container">
                <span>⏱️ EXPIRA:</span>
                <span id="countdown_display" class="timer-box">{reloj_python}</span>
            </div>
            <span style="font-weight:bold;">PEDRO BRAVIN S.A.</span>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{display_badge}</span>
                <div style="font-size:0.6rem; color:#666; margin-top:2px; white-space:nowrap;">
                    {subtext_badge}
                </div>
            </div>
            <div class="price-tag">{display_precio} <span style="font-size:0.7rem; color:#666; font-weight:400;">{display_iva}</span></div>
        </div>
        <div class="progress-container"><div class="progress-bar"></div></div>
    </div>
    
    <script>
    (function() {{
        if (window.miIntervalo) clearInterval(window.miIntervalo);
        var duration = {seg_restantes};
        var display = document.getElementById("countdown_display");
        function updateTimer() {{
            var minutes = parseInt(duration / 60, 10);
            var seconds = parseInt(duration % 60, 10);
            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;
            if (display) {{ display.textContent = minutes + ":" + seconds; }}
            if (--duration < 0) {{ duration = 0; if (window.miIntervalo) clearInterval(window.miIntervalo); }}
        }}
        if (duration > 0) {{ updateTimer(); window.miIntervalo = setInterval(updateTimer, 1000); }}
    }})();
    </script>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 6. CEREBRO IA (REGLAS DE NEGOCIO RESTAURADAS)
# ==========================================
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try: api_key = st.secrets["GOOGLE_API_KEY"]
        except: pass
    if not api_key: st.error("🚨 FALTA API KEY: Configurar en Cloud Run.")
    else: genai.configure(api_key=api_key)
except Exception as e: st.error(f"Error IA: {e}")

sys_prompt = f"""
ROL: Miguel, ejecutivo comercial de Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}
# DATO INTERNO: DOLAR = {DOLAR_BNA}

📏 **CATÁLOGO TÉCNICO Y LARGOS DE VENTA (MEMORIZAR):**
1. **CONSTRUCCIÓN (ADN) / PERFIL C / IPN / UPN:** Barras de **12 METROS**.
2. **TUBOS ESTRUCTURALES / HIERROS / ÁNGULOS:** Barras de **6 METROS**.
3. **CAÑOS (Uso Mecánico, Epoxi, Galvanizado, Schedule):** Barras de **6.40 METROS**.
4. **CHAPA T90:** Única medida **13 METROS** (Hoja cerrada).
5. **CHAPA COLOR:** Venta por Metro Lineal.
6. **CHAPA CINCALUM:** Códigos de cortes específicos o base 1 Metro (Cod 4/6).
7. **PINTURERIA/ACCESORIOS:** Unidad.

🚚 **LOGÍSTICA Y ENVÍOS:**
1. **ZONA GRATIS:** Si la ciudad está en la lista {CIUDADES_GRATIS} -> ¡Envío SIN CARGO!
2. **OTRAS ZONAS:** Costo aproximado = `Distancia_KM * 2 * {COSTO_FLETE_USD} * {DOLAR_BNA}`.
3. **ACOPIO:** ¡Ofrecemos acopio gratuito por **6 MESES**! (Ideal para congelar precio).

⛔ **REGLAS DE ORO:**
1. **NO AGREGAR SIN PERMISO:** Cotiza -> Sugiere combo -> Espera "Sí" -> Agrega.
2. **ANTI-AMBIGÜEDAD:** Si piden "Planchuela" sin medida -> PREGUNTA ancho y espesor.
3. **CLASIFICACIÓN TIPO:** Chapa->CHAPA, Perfil->PERFIL, Pintura->PINTURA, Hierro->HIERRO.

💞 **PERSONALIDAD:**
- Seductor comercial, amable pero técnico.
- Usa el **ACOPIO** y los **DESCUENTOS** como cierre: "Aprovechá a congelar el precio y te lo guardamos 6 meses".

SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO_FINAL_PESOS:TIPO]
"""

if "chat_session" not in st.session_state:
    if "api_key" in locals() and api_key:
        st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_input(contenido, es_imagen=False):
    if "chat_session" in st.session_state:
        msg = contenido
        prefix = ""
        if es_imagen: 
            msg = ["Analiza lista. COTIZA SOLO LO QUE VES.", contenido]
        
        prompt_final = f"{prefix}{msg}. (NOTA INTERNA: Cotiza SOLO lo pedido. Sugiere combos)." if not es_imagen else msg
        return st.session_state.chat_session.send_message(prompt_final).text
    return "Error: Chat no iniciado."

# ==========================================
# 7. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])

spacer_html = '<div style="height: 30px;"></div>'

with tab1:
    st.markdown(spacer_html, unsafe_allow_html=True)
    
    if not oferta_viva:
        st.error("⚠️ SE ACABÓ EL TIEMPO. PRECIOS ACTUALIZADOS.")
        if st.button("🔄 REACTIVAR BENEFICIO", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.rerun()

    # ZERO STATE
    if len(st.session_state.messages) == 1:
        st.info("💡 **TIP:** Tocá el botón **'➕ Adjuntar'** para subir una foto de tu lista.")

    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    # BARRA FLOTANTE
    with st.container():
        col_pop, col_spacer = st.columns([1.5, 8.5])
        with col_pop:
            with st.popover("➕ Adjuntar", use_container_width=True):
                st.caption("Selecciona:")
                img_val = st.file_uploader("📸 Foto de lista", type=["jpg","png","jpeg"])
                if img_val is not None:
                    file_id = f"{img_val.name}_{img_val.size}"
                    if st.session_state.last_processed_file != file_id:
                        with st.spinner("👀 Analizando foto..."):
                            full_text = procesar_input(Image.open(img_val), es_imagen=True)
                            news = parsear_ordenes_bot(full_text)
                            st.session_state.messages.append({"role": "assistant", "content": full_text})
                            st.session_state.last_processed_file = file_id
                            if news: st.balloons()
                            st.rerun()

    # INPUT CHAT
    if prompt := st.chat_input("Escribí, subí foto..."):
        if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Consultando stock..."):
                try:
                    if "chat_session" in st.session_state:
                        prompt_con_presion = f"{prompt}. (NOTA: Cotiza SOLO lo pedido. Sugiere combos)."
                        response = st.session_state.chat_session.send_message(prompt_con_presion)
                        full_text = response.text
                        news = parsear_ordenes_bot(full_text)
                        display = re.sub(r'\[ADD:.*?\]', '', full_text)
                        st.markdown(display)
                        
                        if news: 
                            st.toast(random.choice(TOASTS_EXITO), icon='🎉')
                            if desc_actual >= 12: st.balloons()
                        
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        if news: time.sleep(1.5); st.rerun()
                    else: st.error("Cerebro desconectado.")
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    st.markdown(spacer_html, unsafe_allow_html=True)
    if not st.session_state.cart:
        st.info("Tu carrito está esperando ofertas...")
