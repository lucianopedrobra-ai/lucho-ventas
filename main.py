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

# 🎯 METAS DE VENTA (BASE POR VOLUMEN)
META_MAXIMA = 2500000   # Base 15%
META_MEDIA  = 1500000   # Base 12%
META_BASE   = 800000    # Base 10%

# ==========================================
# 2. MOTOR INVISIBLE (DATOS + LÓGICA)
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
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

MINUTOS_OFERTA = 10 

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

TOASTS_EXITO = [
    "✨ ¡Excelente elección!", 
    "🔥 ¡Te congelé este precio!", 
    "💎 ¡Producto reservado!", 
    "🚀 ¡Sumamos puntos para el descuento!"
]

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
    st.session_state.messages = [{"role": "assistant", "content": "👋 **¡Hola!** Soy Miguel. Tengo la lista de precios abierta y el dólar actualizado. \n\nPasame tu pedido ahora y **vemos qué atención especial te puedo hacer** en el final. 😉"}]

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
        try: 
            requests.post(URL_FORM_GOOGLE, data={
                ID_CAMPO_CLIENTE: str(cliente), 
                ID_CAMPO_MONTO: str(monto), 
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }, timeout=1)
        except: pass

def log_interaction(user_text, monto):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    op = "ALTA" if monto > META_MEDIA else "MEDIA" if monto > META_BASE else "BAJA"
    st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Monto": monto})
    threading.Thread(target=enviar_a_google_form_background, args=(user_text, monto, op)).start()

def parsear_ordenes_bot(texto):
    items_nuevos = []
    for cant, prod, precio, tipo in re.findall(r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]', texto):
        item = {
            "cantidad": float(cant), 
            "producto": prod.strip(), 
            "precio_unit": float(precio), 
            "subtotal": float(cant)*float(precio), 
            "tipo": tipo.strip().upper()
        }
        st.session_state.cart.append(item)
        items_nuevos.append(item)
    return items_nuevos

# --- NUEVA LÓGICA DE NEGOCIO (BASE + BOOSTERS) ---
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
    desc_base = 0
    desc_extra = 0
    nivel_texto = "PRECIO LISTA"
    color = "#546e7a"
    meta = META_BASE
    
    # 1. DETECCIÓN DE TIPOS EN CARRITO
    tipos_en_carrito = [x['tipo'] for x in st.session_state.cart]
    
    # Lógica de categorías
    tiene_chapa = any("CHAPA" in t for t in tipos_en_carrito)
    tiene_perfil = any("PERFIL" in t for t in tipos_en_carrito)
    tiene_acero = any(t in ["HIERRO", "MALLA", "CLAVOS", "ALAMBRE", "PERFIL", "CHAPA", "TUBO", "CAÑO"] for t in tipos_en_carrito)
    tiene_pintura = any("PINTURA" in t or "ACCESORIO" in t or "ELECTRODO" in t for t in tipos_en_carrito)

    if activa:
        # A. CALCULO BASE POR VOLUMEN
        if bruto > META_MAXIMA:
            desc_base = 15
            nivel_texto = "PARTNER (15%)"
            color = "#6200ea" # Violeta
            meta = 0
        elif bruto > META_MEDIA:
            desc_base = 12
            nivel_texto = "CONSTRUCTOR (12%)"
            color = "#d32f2f" # Rojo
            meta = META_MAXIMA
        elif bruto > META_BASE:
            desc_base = 10
            nivel_texto = "OBRA (10%)"
            color = "#f57c00" # Naranja
            meta = META_MEDIA
        else:
            desc_base = 3
            nivel_texto = "CONTADO (3%)"
            color = "#2e7d32" # Verde
            meta = META_BASE

        # B. BOOSTERS (CROSS-SELLING) - ACUMULABLES HASTA TOPE
        boosters_activos = []
        
        # Booster 1: Kit Techo (Chapa + Perfil)
        if tiene_chapa and tiene_perfil:
            desc_extra += 3
            boosters_activos.append("🏠 KIT TECHO (+3%)")
            
        # Booster 2: Terminación (Acero + Pintura/Consumibles)
        elif tiene_acero and tiene_pintura: # Usamos elif para no regalar todo junto tan fácil, o if para acumular
            desc_extra += 2
            boosters_activos.append("🎨 PACK TERM. (+2%)")
            
        # C. SUMA FINAL Y TOPE (MAX 18%)
        desc_total = min(desc_base + desc_extra, 18)
        
        # D. GENERACIÓN DE ETIQUETA FINAL
        if desc_extra > 0:
            nivel_texto = f"{nivel_texto} + {' '.join(boosters_activos)}"
            # Si hay booster, color especial
            if desc_total >= 15: color = "#6200ea" 
            
    else:
        # Oferta caducada
        if bruto > META_MAXIMA: 
            desc_total = 12 # Castigo por demora, baja del 15/18 al 12
            nivel_texto = "OFERTA EXPIRADA"
            color = "#455a64"
        else: 
            desc_total = 0
            nivel_texto = "PRECIO LISTA"
            color = "#455a64"

    neto = bruto * (1 - (desc_total/100))
    return bruto, neto, desc_total, color, nivel_texto, meta, segundos_restantes, activa, color_reloj, reloj_init

def generar_link_wa(total):
    txt = "Hola Martín, confirmar pedido:\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 5. UI: HEADER
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel, prox_meta, seg_restantes, oferta_viva, color_timer, reloj_python = calcular_negocio()
porcentaje_barra = 100
if prox_meta > 0: porcentaje_barra = min((subtotal / prox_meta) * 100, 100)

display_precio = f"${total_final:,.0f}" if subtotal > 0 else "🛒 COTIZAR"
display_iva = "+IVA" if subtotal > 0 else ""
# Ajuste de Badge para que entren los textos largos de los boosters
display_badge = nombre_nivel[:25] + "..." if len(nombre_nivel) > 25 and subtotal > 0 else (nombre_nivel if subtotal > 0 else "⚡ 3% OFF YA")
subtext_badge = f"Ahorro Total: {desc_actual}%" if (oferta_viva and subtotal > 0) else "TIEMPO LIMITADO"

header_html = f"""
    <style>
    .block-container {{ padding-top: 130px !important; padding-bottom: 150px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    
    [data-testid="stBottomBlock"], [data-testid="stChatInput"] {{
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: white; padding-top: 10px; padding-bottom: 10px;
        z-index: 99999; border-top: 1px solid #eee;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 90px; left: 0; width: 100%; 
        background: white; z-index: 99990;
        display: flex; justify-content: space-around;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
        padding-bottom: 2px; padding-top: 5px;
    }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 8px; font-weight: bold; font-size: 0.8rem; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; 
        background: white; z-index: 100000;
        border-bottom: 4px solid {color_barra}; 
        height: 90px; overflow: hidden;
    }}
    
    .top-strip {{ 
        background: #111; color: #fff; padding: 8px 15px; 
        display: flex; justify-content: space-between; 
        font-size: 0.7rem; align-items: center; height: 30px;
    }}
    
    .cart-summary {{ 
        padding: 5px 15px; display: flex; justify-content: space-between; 
        align-items: center; height: 56px;
    }}
    
    .price-tag {{ font-weight: 900; color: #333; white-space: nowrap; }}
    
    .badge {{ 
        background: {color_barra}; color: white; padding: 3px 8px; 
        border-radius: 4px; font-weight: 900; text-transform: uppercase; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.2); white-space: nowrap;
    }}

    @media only screen and (max-width: 600px) {{
        .price-tag {{ font-size: 1.1rem; }}
        .badge {{ font-size: 0.6rem; padding: 3px 6px; }}
        .cart-summary {{ padding: 5px 10px; }}
    }}

    @media only screen and (min-width: 601px) {{
        .price-tag {{ font-size: 1.5rem; }}
        .badge {{ font-size: 0.75rem; padding: 4px 12px; }}
    }}
    
    .timer-container {{ display: flex; align-items: center; gap: 5px; }}
    .timer-box {{ 
        color: {color_timer}; font-weight: 900; font-size: 0.8rem; 
        background: #fff; padding: 1px 6px; border-radius: 4px; 
        border: 1px solid {color_timer}; min-width: 45px; text-align: center;
    }}
    
    .progress-container {{ width: 100%; height: 4px; background: #eee; position: absolute; bottom: 0; }}
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
            if (--duration < 0) {{
                duration = 0;
                if (window.miIntervalo) clearInterval(window.miIntervalo);
            }}
        }}
        if (duration > 0) {{
            updateTimer();
            window.miIntervalo = setInterval(updateTimer, 1000);
        }}
    }})();
    </script>
"""

st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 6. CEREBRO IA (MODO: EXPERTO + CLASIFICADOR DE PRODUCTOS)
# ==========================================
try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: st.error("Falta API KEY")

sys_prompt = f"""
ROL: Miguel, ejecutivo comercial de Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}
# DATO INTERNO: DOLAR = {DOLAR_BNA}

📏 **CATÁLOGO TÉCNICO Y LARGOS DE VENTA:**
1. **PERFILES/HIERROS/TUBO/IPN/UPN:** Barras enteras (12m o 6m según tipo).
2. **CAÑOS:** Barras de 6.40m.
3. **CHAPA T90:** Hoja cerrada de 13m.
4. **CHAPA COLOR:** Por Metro Lineal.
5. **CHAPA CINCALUM:** Códigos de cortes o base 1 Metro.
6. **PINTURERIA/ACCESORIOS:** Unidad.

🏷️ **IMPORTANTE: CLASIFICACIÓN DE TIPOS PARA DESCUENTOS**
Al generar la salida [ADD:...], en el campo 'TIPO' debes ser preciso para que el sistema active los descuentos combinados:
- Si es Chapa (Techo) -> TIPO: **CHAPA**
- Si es Perfil C/U/I -> TIPO: **PERFIL**
- Si es Pintura, Solvente, Pincel, Disco, Electrodo -> TIPO: **PINTURA**
- Si es Hierro, Malla, Clavos, Alambre, Caño, Tubo -> TIPO: **HIERRO** (O el específico).

💞 **PERSONALIDAD "SEDUCTOR COMERCIAL":**
- **ACTITUD:** "Franelea" al cliente. Hazle notar si activa un combo.
- **CROSS-SELLING:** Si lleva chapa, sugiérele Perfil C para activar el "Descuento Kit Techo". Si lleva hierro, sugiérele antióxido para el "Descuento Terminación".
- **CIERRE:** Induce al botón verde.

SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO_FINAL_PESOS:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. COTIZA, CLASIFICA BIEN LOS TIPOS Y SEDUCE.", img]).text

# ==========================================
# 7. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])

with tab1:
    if not oferta_viva:
        st.error("⚠️ SE ACABÓ EL TIEMPO. PRECIOS ACTUALIZADOS.")
        if st.button("🔄 REACTIVAR BENEFICIO (PRÓRROGA)", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.toast("✅ ¡Tiempo reiniciado!", icon="😅")
            st.rerun()

    with st.expander("📷 **Subir Foto de Lista**", expanded=False):
        img_val = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
        if img_val is not None:
            file_id = f"{img_val.name}_{img_val.size}"
            if st.session_state.last_processed_file != file_id:
                with st.spinner("👀 Analizando combos..."):
                    full_text = procesar_vision(Image.open(img_val))
                    news = parsear_ordenes_bot(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    st.session_state.last_processed_file = file_id
                    if news: 
                        st.toast("🔥 Productos Cargados", icon='✅')
                        st.balloons()
                    log_interaction("FOTO AUTO", total_final)
                    st.rerun()

    for m in st.session_state.messages:
        if m["role"] != "system":
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"]).strip()
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

    if prompt := st.chat_input("Escribí tu pedido acá..."):
        if prompt == "#admin-miguel": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Buscando descuentos..."):
                try:
                    prompt_con_presion = f"{prompt}. (NOTA INTERNA: Cotiza exacto. Clasifica bien el TIPO para los descuentos. Seduce con el ahorro)."
                    
                    response = st.session_state.chat_session.send_message(prompt_con_presion)
                    full_text = response.text
                    news = parsear_ordenes_bot(full_text)
                    display = re.sub(r'\[ADD:.*?\]', '', full_text)
                    st.markdown(display)
                    
                    if news:
                        st.toast(random.choice(TOASTS_EXITO), icon='🎉')
                        
                        # LOGICA DE GLOBOS Y ALERTAS SEGUN DESCUENTOS OBTENIDOS
                        if desc_actual >= 15 and st.session_state.discount_tier_reached < 3:
                            st.session_state.discount_tier_reached = 3
                            st.balloons()
                        elif desc_actual >= 12 and st.session_state.discount_tier_reached < 2:
                            st.session_state.discount_tier_reached = 2
                            st.snow()

                        st.markdown(f"""
                        <div style="background:#e8f5e9; padding:10px; border-radius:10px; border:1px solid #25D366; margin-top:5px; animation: pulse-green 2s infinite;">
                            <strong>✅ {len(news)} items reservados.</strong><br>
                            <span style="font-size:0.85rem">💰 Total: ${total_final:,.0f}</span><br>
                            <span style="font-size:0.8rem; color:#d32f2f;">⏳ Confirmá antes de que cambie el dólar ({reloj_python})</span>
                        </div>
                        <style>@keyframes pulse-green {{ 0% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(37, 211, 102, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }} }}</style>
                        """, unsafe_allow_html=True)

                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    log_interaction(prompt, total_final)
                    if news: time.sleep(1.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    if not st.session_state.cart:
        st.info("Tu carrito está esperando ofertas...")
    else:
        st.markdown(f"### 📋 Confirmar Pedido ({len(st.session_state.cart)} items)")
        
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                with c1:
                    st.markdown(f"**{item['producto']}**")
                    st.caption(f"C/U: ${item['precio_unit']:,.0f}")
                with c2:
                    nueva_cant = st.number_input("Cant", min_value=0.0, value=float(item['cantidad']), step=1.0, key=f"qty_{i}", label_visibility="collapsed")
                    if nueva_cant != item['cantidad']:
                        if nueva_cant == 0: st.session_state.cart.pop(i)
                        else:
                            st.session_state.cart[i]['cantidad'] = nueva_cant
                            st.session_state.cart[i]['subtotal'] = nueva_cant * item['precio_unit']
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                st.markdown("---")

        col_res1, col_res2 = st.columns(2)
        col_res1.write("Subtotal Lista:")
        col_res2.write(f"${subtotal:,.0f}")
        
        if oferta_viva and desc_actual > 0:
            col_res1.markdown(f"**Beneficio:**")
            col_res2.markdown(f"**-${subtotal * (desc_actual/100):,.0f} ({desc_actual}%)**")
            st.caption(f"Aplicado: {nombre_nivel}")
        elif not oferta_viva:
            st.warning("⚠️ DESCUENTO EXPIRADO.")
            
        st.markdown(f"""
        <div style="background:{color_barra}; color:white; padding:20px; border-radius:15px; text-align:center; margin-top:15px; box-shadow: 0 4px 15px {color_barra}66; border: 2px solid #fff;">
            <div style="font-size:0.8rem; opacity:0.9;">TOTAL FINAL CONTADO (+IVA)</div>
            <div style="font-size:2.2rem; font-weight:900;">${total_final:,.0f}</div>
            <div style="font-size:0.8rem; margin-top:5px; background:rgba(0,0,0,0.2); padding:4px 10px; border-radius:10px; display:inline-block;">
                { '⚡ DESCUENTO APLICADO' if oferta_viva else '❌ PRECIO LISTA' }
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <a href="{generar_link_wa(total_final)}" target="_blank" style="
            display:block; width:100%; background-color:#25D366; color:white; margin-top:15px;
            text-align:center; padding:18px; border-radius:50px; text-decoration:none; 
            font-weight:bold; font-size:1.2rem; box-shadow: 0 4px 15px rgba(37,211,102,0.5);
            animation: pulse-green 2s infinite;">
            🚀 ENVIAR PEDIDO AHORA
        </a>
        <style>@keyframes pulse-green {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); }} }}</style>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("🗑️ VACIAR CARRITO", type="secondary", use_container_width=True): st.session_state.cart = []; st.rerun()

if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
