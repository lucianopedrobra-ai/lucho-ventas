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
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(
    page_title="🔥 OFERTAS PEDRO BRAVIN",
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎯 METAS DE VENTA
META_MAXIMA = 2500000
META_MEDIA  = 1500000
META_BASE   = 800000

# ==========================================
# 2. MOTOR INVISIBLE Y VARIABLES GLOBALES
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
URL_FORM_GOOGLE = "" # Remplazar con URL real del Formulario de Google

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
# 3. ESTADO Y SESIÓN
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None
if "discount_tier_reached" not in st.session_state: st.session_state.discount_tier_reached = 0

if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)

if "messages" not in st.session_state:
    saludo = """
🦁 **Soy Miguel.** Dólar actualizado. Stock disponible.

👇 **PASAME TU PEDIDO YA** (Escribí o usá el botón **➕** para subir foto).
*¡El precio se congela por 3 minutos!* ⏳
    """
    st.session_state.messages = [{"role": "assistant", "content": saludo}]
    
if "model_name" not in st.session_state: st.session_state.model_name = None
if "chat_session" not in st.session_state: st.session_state.chat_session = None

# ==========================================
# 4. BACKEND Y LÓGICA DE NEGOCIO
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    try: return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

csv_context = load_data()

def parsear_ordenes_bot(texto):
    items_nuevos = []
    # Regex robusto para capturar las órdenes del bot
    # Captura: Cantidad, Producto (incluye espacios), Precio, Tipo (no incluye ])
    for cant, prod, precio, tipo in re.findall(r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]', texto):
        try:
            item = {
                "cantidad": float(cant), 
                "producto": prod.strip(), 
                "precio_unit": float(precio), 
                "subtotal": float(cant)*float(precio), 
                "tipo": tipo.strip().upper()
            }
            st.session_state.cart.append(item)
            items_nuevos.append(item)
        except Exception as e:
            # Simplemente ignora si el bot alucina un formato numérico extraño
            pass 
    return items_nuevos

def calcular_negocio():
    try:
        now = datetime.datetime.now()
        tiempo_restante = st.session_state.expiry_time - now
        segundos_restantes = int(tiempo_restante.total_seconds())
        activa = segundos_restantes > 0
        
        # Lógica del reloj
        if activa:
            m, s = divmod(segundos_restantes, 60)
            reloj_init = f"{m:02d}:{s:02d}"
            color_reloj = "#2e7d32" 
            if m < 2: color_reloj = "#ff9800"
            if m < 1: color_reloj = "#ff0000"
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
            # Lógica de descuentos
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
    except Exception as e:
        # Fallback seguro para evitar errores en cierre
        print(f"Error en calcular_negocio: {e}")
        return 0, 0, 0, "#455a64", "ERROR", 0, 0, False, "#b0bec5", "00:00", 0

def generar_link_wa(total):
    try:
        txt = "HOLA, QUIERO CONGELAR PRECIO YA (Oferta Flash):\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
        txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
        return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"
    except:
        return "https://wa.me/5493401527780"


# ==========================================
# 5. CEREBRO IA (REGLAS + INICIALIZACIÓN)
# ==========================================
MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-2.5-pro'] 

def initialize_gemini():
    """Busca la API Key e inicializa la sesión de chat con el mejor modelo disponible."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try: api_key = st.secrets["GOOGLE_API_KEY"]
        except: pass
        
    if not api_key:
        st.warning("⚠️ **ALERTA:** No se encontró la `GOOGLE_API_KEY`. El bot no funcionará.")
        return False
        
    genai.configure(api_key=api_key)
    
    sys_prompt = f"""
ROL: Miguel, vendedor experto de Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS (PUNTOS LOGÍSTICOS): {CIUDADES_GRATIS}
DOLAR BNA VENTA: {DOLAR_BNA}

📏 **CATÁLOGO TÉCNICO (ESTRICTO):**
- **12m:** Perfil C, IPN, UPN, ADN.
- **6.40m:** Caños (Mecánico, Epoxi, Galvanizado, Schedule). **¡ATENCIÓN! La unidad de venta de estas barras es "METRO", NO "KG".**
- **6m:** Tubos Estructurales, Hierros, Ángulos, Planchuelas.
- **CHAPA T90:** Única medida 13m.
- **CHAPA COLOR / CINCALUM:** Por metro.

🧠 **CEREBRO DE VENTAS (ASOCIACIÓN LÓGICA DE PRODUCTOS):**
- **ANÁLISIS DE PROYECTO:** Si el usuario pide una solución genérica, debes mapearla a los productos del CSV.
- **CASO "CERCAR/ALAMBRAR":** Si el usuario dice "quiero cercar un terreno" o "cerrar un lote", OFRECE AUTOMÁTICAMENTE: Mallas, Tejido Romboidal, Tubos/Caños (postes), Alambre.
- **CASO "TECHO/GALPÓN":** Si pide material para techo, ofrece: Perfil C, Chapas y Aislantes.
- **INTERPRETACIÓN:** Si el usuario no especifica medidas exactas, sugiere las estándar disponibles en el CSV y PREGUNTA para confirmar.

🚚 **LÓGICA DE FLETE (CRÍTICO - CÁLCULO AUTOMÁTICO):**
1. **Analiza la ubicación del cliente.**
2. **CASO 1: ZONA GRATIS.** Si la ciudad está en {CIUDADES_GRATIS} -> ENVÍO $0.
3. **CASO 2: FUERA DE ZONA.** - **Herramienta de Búsqueda (IMPRESCINDIBLE):** Utiliza tu herramienta de búsqueda/geografía para:
     a. Identificar la ciudad de {CIUDADES_GRATIS} más cercana al cliente (Punto Logístico).
     b. **Estimar/Buscar la distancia REAL en KM (solo IDA) entre el Punto Logístico y el cliente.**
   - **Cálculo de Flete (Total):** `(KM_IDA * 2) * {COSTO_FLETE_USD} USD * {DOLAR_BNA} * 1.21 (IVA)`.
   - **RESPUESTA:** Agrega este costo de flete al carrito inmediatamente como un item obligatorio. NUNCA preguntes los KM al cliente.
   - **Formato:** Agrega el costo como un item "[ADD:1:FLETE A [CIUDAD DEL CLIENTE]:PRECIO_CALCULADO:SERVICIO]".

⛔ **PROTOCOLO SNIPER:**
1. **BREVEDAD:** Max 15 palabras. Directo.
2. **CONFIRMACIÓN:** SOLO agrega `[ADD:...]` si el cliente dice "SÍ" o "CARGALO" o si has inferido una necesidad obvia (ej. flete obligatorio y productos cotizados).
3. **UPSELL:** "Te faltan $X para el descuento. ¿Agrego pintura?".

SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO_FINAL_PESOS:TIPO]
"""

    for model_name in MODELS_TO_TRY:
        try:
            st.session_state.chat_session = genai.GenerativeModel(
                model_name, 
                system_instruction=sys_prompt,
                tools='google_search_retrieval' 
            ).start_chat(history=[])
            st.session_state.model_name = model_name
            return True # Éxito
        except Exception as e:
            st.session_state.model_name = None 
            print(f"Error al inicializar {model_name}: {e}")
            continue
            
    st.error("Error: No se pudo inicializar ningún modelo de IA. Revisar logs/API Key.")
    return False

if not st.session_state.chat_session:
    initialize_gemini()


def procesar_input(contenido, es_imagen=False):
    if not st.session_state.chat_session:
        return "Error: Chat off. No se pudo inicializar ningún modelo de IA. Revisar logs."
        
    msg = contenido
    if es_imagen: msg = ["COTIZA ESTO RÁPIDO. DETECTA OPORTUNIDADES Y CONTEXTO DEL PRODUCTO (No confundir unidades).", contenido]
    
    prompt_final = f"{msg}. (NOTA: Sé breve. Cotiza precios. NO AGREGUES sin confirmación)." if not es_imagen else msg

    try:
        # Aquí es donde ocurre la comunicación real con la API
        return st.session_state.chat_session.send_message(prompt_final).text
    except Exception as e:
        # Si falla la comunicación (time-out, etc.), intentamos re-inicializar
        st.session_state.chat_session = None 
        initialize_gemini()
        return f"Hubo un error de conexión con el modelo **{st.session_state.model_name}**, intenta de nuevo. (Detalle: {e})"
            
# ==========================================
# 6. UI: HEADER AGRESIVO Y TEMPORIZADOR
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

# Placeholder para el reloj y el header
header_placeholder = st.empty() 

def render_header(reloj_init, color_timer):
    """Renderiza el HTML del encabezado con el tiempo actual."""
    
    # Se pasa el reloj de Python aquí, el JS lo actualizará cada segundo.
    header_html = f"""
        <style>
        /* LIMPIEZA Y LAYOUT OPTIMIZADO PARA MÓVIL */
        #MainMenu, footer, header {{ visibility: hidden !important; }}
        [data-testid="stToolbar"] {{ display: none !important; }}
        .block-container {{ padding-top: 130px !important; padding-bottom: 120px !important; }}
        .stChatInputContainer textarea {{ min-height: 38px !important; height: 38px !important; padding: 8px !important; }}
        
        /* HEADER */
        .fixed-header {{ position: fixed; top: 0; left: 0; width: 100%; background: #fff; z-index: 99990; border-bottom: 4px solid {color_barra}; height: 95px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.15); }}
        .price-tag {{ font-weight: 900; color: #111; font-size: 1.5rem; animation: heartbeat 2s infinite; }}
        .badge {{ background: linear-gradient(90deg, {color_barra}, #111); color: white; padding: 3px 10px; border-radius: 4px; font-weight: 900; font-size: 0.75rem; text-transform: uppercase; }}
        
        /* BARRA PROGRESO */
        .progress-container {{ width: 100%; height: 8px; background: #eee; position: absolute; bottom: 0; }}
        .progress-bar {{ 
            height: 100%; width: {porcentaje_barra}%; 
            background: linear-gradient(90deg, {color_barra}, #ffeb3b); 
            transition: width 0.5s ease-out; 
            background-size: 200% 200%;
            animation: slideBg 2s linear infinite;
        }}
        .top-strip {{ background: #000; color: #fff; padding: 4px 10px; display: flex; justify-content: space-between; font-size: 0.7rem; align-items: center; font-weight: bold; letter-spacing: 0.5px; }}
        .cart-summary {{ padding: 5px 15px; display: flex; justify-content: space-between; align-items: center; height: 60px; }}
        .timer-box {{ color: {color_timer}; background: #fff; padding: 1px 6px; border-radius: 3px; font-weight: 900; border: 1px solid {color_timer}; }}
        
        /* TABS */
        .stTabs [data-baseweb="tab-list"] {{ position: fixed; top: 95px; left: 0; width: 100%; background: #ffffff; z-index: 99980; padding-top: 2px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 6px; font-weight: bold; font-size: 0.75rem; }}
        
        /* BOTÓN FLOTANTE ESTILO WHATSAPP (EL +) */
        div[data-testid="stPopover"] {{
            position: fixed; bottom: 65px; left: 10px; z-index: 200000; width: auto;
        }}
        div[data-testid="stPopover"] button {{
            border-radius: 50%; width: 45px; height: 45px;
            background-color: #25D366; color: white; border: 2px solid white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            display: flex; align-items: center; justify-content: center; font-size: 20px;
            animation: pulse-green-btn 2s infinite;
        }}
        @keyframes pulse-green-btn {{ 0% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(37, 211, 102, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }} }}
        
        /* ANIMACIONES */
        @keyframes heartbeat {{ 0% {{ transform: scale(1); }} 15% {{ transform: scale(1.05); }} 30% {{ transform: scale(1); }} 45% {{ transform: scale(1.05); }} 60% {{ transform: scale(1); }} }}
        @keyframes slideBg {{ 0% {{ background-position: 0% 50%; }} 100% {{ background-position: 100% 50%; }} }}
        </style>
        
        <div class="fixed-header">
            <div class="top-strip">
                <div style="display:flex; align-items:center; gap:5px;">⏳ EXPIRA: <span id="countdown_display" class="timer-box">{reloj_init}</span></div>
                <div style="color:#FFD700; font-style:italic;">🦁 PEDRO BRAVIN S.A.</div>
            </div>
            <div class="cart-summary">
                <div>
                    <span class="badge">{display_badge}</span>
                    <div style="font-size:0.7rem; color:{color_barra}; font-weight:900; margin-top:3px; animation: heartbeat 1s infinite;">{subtext_badge}</div>
                </div>
                <div class="price-tag">{display_precio}<span style="font-size:0.8rem; font-weight:400; color:#666; margin-left:2px;">{display_iva}</span></div>
            </div>
            <div class="progress-container"><div class="progress-bar"></div></div>
        </div>
        <script>
        // SCRIPT DE CUENTA REGRESIVA SOLO JAVASCRIPT
        (function() {{
            if (window.miIntervalo) clearInterval(window.miIntervalo); 
            var duration = {seg_restantes}; 
            var display = window.parent.document.getElementById("countdown_display");
            
            function updateTimer() {{
                var m = parseInt(duration / 60, 10); 
                var s = parseInt(duration % 60, 10); 
                m = m < 10 ? "0" + m : m; 
                s = s < 10 ? "0" + s : s;
                
                if (display) display.textContent = m + ":" + s;
                
                if (--duration < 0) {{ 
                    duration = 0; 
                    if (window.miIntervalo) clearInterval(window.miIntervalo); 
                    // st.rerun() puede ser llamado desde JS para recargar Python si el timer llega a 0
                }}
            }}
            if (duration > 0) {{ 
                updateTimer(); 
                window.miIntervalo = setInterval(updateTimer, 1000); 
            }}
        }})();
        </script>
    """
    header_placeholder.markdown(header_html, unsafe_allow_html=True)

# Llama a la función de renderizado una vez
render_header(reloj_python, color_timer)

# ==========================================
# 7. INTERFAZ TABS Y CHAT
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])
spacer = '<div style="height: 20px;"></div>'

# --- 💡 BOTÓN FLOTANTE "PAGAR AHORA" (STICKY FOOTER) ---
if len(st.session_state.cart) > 0 and oferta_viva:
    st.markdown(f"""
    <div style="position:fixed; bottom:75px; right:10px; left:10px; z-index:200000; display:flex; justify-content:center;">
        <a href="{generar_link_wa(total_final)}" target="_blank" style="
            background: linear-gradient(90deg, #ff0000, #d50000); color: white; 
            padding: 15px 30px; border-radius: 50px; width: 100%; text-align:center;
            font-weight: 900; text-decoration: none; box-shadow: 0 5px 25px rgba(255,0,0,0.6);
            border: 3px solid #fff; font-size: 1.2rem; animation: shake 4s infinite; text-transform: uppercase;">
            🔥 PAGAR AHORA: ${total_final:,.0f} ➔
        </a>
    </div>
    <style>@keyframes shake {{ 0%, 100% {{transform: translateX(0);}} 10%, 30%, 50%, 70%, 90% {{transform: translateX(-2px);}} 20%, 40%, 60%, 80% {{transform: translateX(2px);}} }}</style>
    """, unsafe_allow_html=True)


with tab1:
    st.markdown(spacer, unsafe_allow_html=True)
    
    # Manejo de oferta expirada
    if not oferta_viva:
        st.error("⚠️ PRECIOS EXPIRADOS")
        if st.button("🔄 RECARGAR PRECIOS", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.rerun()

    # POP-UP DE OPORTUNIDAD
    if 0 < prox_meta - subtotal < 200000 and oferta_viva:
        st.toast(f"🚨 ¡FALTAN ${prox_meta - subtotal:,.0f} PARA DESCUENTO! SUMÁ PINTURA O DISCOS.", icon="🔥")

    # Muestra los mensajes del chat
    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    # Contenedor del botón flotante para imágenes
    with st.container():
        c1, c2 = st.columns([1.5, 8.5])
        with c1:
            with st.popover("➕", use_container_width=False):
                st.caption("Subir Foto")
                img = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
                if img:
                    fid = f"{img.name}_{img.size}"
                    if st.session_state.last_processed_file != fid:
                        with st.spinner("⚡ Procesando con visión contextual..."):
                            # Usar la imagen como contenido
                            txt = procesar_input(Image.open(img), es_imagen=True)
                            
                            news = parsear_ordenes_bot(txt)
                            st.session_state.messages.append({"role": "assistant", "content": txt})
                            st.session_state.last_processed_file = fid
                            
                            if news: 
                                st.balloons()
                                render_header(reloj_python, color_timer) # Refresca el header tras añadir items
                            st.rerun()

    # Input principal del chat
    if p := st.chat_input("Escribí acá..."):
        if p == "#admin": 
            st.session_state.admin_mode = not st.session_state.admin_mode
            st.rerun()
            
        st.session_state.messages.append({"role": "user", "content": p})
        st.chat_message("user").markdown(p)
        
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Calculando logística y stock..."):
                try:
                    # PROCESAMIENTO DEL INPUT - PUNTO CRÍTICO
                    res = procesar_input(f"{p}. (CORTITO Y AL PIE).")
                    
                    # Si la respuesta comienza con "Error:", lo mostramos directamente
                    if res.startswith("Error:"):
                        st.error(res)
                        # No agregamos el error al historial ni re-ejecutamos.
                        
                    else:
                        news = parsear_ordenes_bot(res)
                        display = re.sub(r'\[ADD:.*?\]', '', res)
                        st.markdown(display)
                        
                        if news: 
                            st.toast(random.choice(TOASTS_EXITO), icon='🔥')
                            if desc_actual >= 12: st.balloons()
                            render_header(reloj_python, color_timer) # Refresca el header tras añadir items

                        st.session_state.messages.append({"role": "assistant", "content": res})
                        if news: time.sleep(1); st.rerun()

                except Exception as e:
                    # Muestra el error específico que antes estaba oculto
                    st.error(f"⚠️ ERROR CRÍTICO AL PROCESAR: {e}")
                    print(f"ERROR EN CHAT INPUT: {e}")

# Lógica del carrito (tab2)
with tab2:
    st.markdown(spacer, unsafe_allow_html=True)
    
    if not st.session_state.cart:
        st.info("Carrito vacío. Agregá items para ver el precio final.")
    else:
        st.markdown(f"## 💰 Resumen de Pedido")
        st.markdown(f"**Subtotal (Lista):** ${subtotal:,.0f}")
        st.markdown(f"**Descuento Aplicado:** {desc_actual}%")
        st.markdown(f"**Total Final (sin IVA):** ${total_final:,.0f}")
        st.markdown("---")
        
        indices_to_remove = []
        # Mostrar y permitir modificar items
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                c1.markdown(f"**{item['producto']}**\n<span style='color:grey;font-size:0.8em'>${item['precio_unit']:,.0f} unit</span>", unsafe_allow_html=True)
                
                # Usar key única para evitar problemas con la cantidad
                nueva_cant = c2.number_input("Cant", 0.0, value=float(item['cantidad']), key=f"q_{i}", label_visibility="collapsed", step=0.1)
                
                if nueva_cant != item['cantidad']:
                    if nueva_cant <= 0:
                        indices_to_remove.append(i)
                    else:
                        st.session_state.cart[i]['cantidad'] = nueva_cant
                        st.session_state.cart[i]['subtotal'] = nueva_cant * item['precio_unit']
                        st.rerun()

                if c3.button("🗑️", key=f"d_{i}"): 
                    indices_to_remove.append(i)
                
                st.markdown("---")
        
        if indices_to_remove:
            for index in sorted(indices_to_remove, reverse=True):
                del st.session_state.cart[index]
            render_header(reloj_python, color_timer) # Refresca el header
            st.rerun()
        
        # BOTÓN DE PAGO BACKUP
        st.markdown(f"""
        <a href="{generar_link_wa(total_final)}" target="_blank" style="
            display:block; width:100%; background: #333; 
            color:white; margin-top:20px; text-align:center; padding:15px; border-radius:12px; 
            text-decoration:none; font-weight:bold; opacity:0.8;">
            Link Alternativo de Pago (WhatsApp)
        </a>
        """, unsafe_allow_html=True)
        
        if st.button("Vaciar Carrito", use_container_width=True): st.session_state.cart = []; st.rerun()

# SCRIPT AUTO-SCROLL
components.html("""
    <script>
        // Esta función se ejecuta para hacer scroll
        function scrollDown() {
            var mainContainer = window.parent.document.querySelector(".main");
            if (mainContainer) {
                // Scroll al fondo del contenedor principal de la página
                mainContainer.scrollTop = mainContainer.scrollHeight;
            }
        }
        // Llamar una vez después de la carga inicial
        scrollDown(); 
        // Llamar cada 800ms para seguir los nuevos mensajes
        setInterval(scrollDown, 800);
    </script>
""", height=0)

if st.session_state.admin_mode: 
    st.subheader("🛠️ Modo Administrador")
    st.dataframe(pd.DataFrame(st.session_state.log_data))
    st.write(f"Modelo Usado: **{st.session_state.model_name}**")
