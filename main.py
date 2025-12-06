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
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A.",
    page_icon="💣", # Icono de bomba para urgencia
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VARIABLES ---
DOLAR_BNA = 1060.00
COSTO_FLETE_USD = 0.85 
CONDICION_PAGO = "Contado/Transferencia"
SHEET_ID = "2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?gid=2029869540&single=true&output=csv"
URL_FORM_GOOGLE = "" # 🔴 PEGAR TU LINK AQUI
ID_CAMPO_CLIENTE = "entry.xxxxxx"
ID_CAMPO_MONTO = "entry.xxxxxx"
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx"

# TIEMPO LIMITE EN MINUTOS PARA EL 3% EXTRA
MINUTOS_OFERTA = 10 

CIUDADES_GRATIS = [
    "EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", 
    "CAÑADA ROSQUIN", "SAN VICENTE", "SAN MARTIN DE LAS ESCOBAS", "ANGELICA", 
    "SUSANA", "RAFAELA", "SUNCHALES", "PRESIDENTE ROCA", "SA PEREIRA", 
    "CLUCELLAS", "MARIA JUANA", "SASTRE", "SAN JORGE", "LAS PETACAS", 
    "ZENON PEREYRA", "CARLOS PELLEGRINI", "LANDETA", "MARIA SUSANA", 
    "PIAMONTE", "VILA", "SAN FRANCISCO"
]

TOASTS_EXITO = ["🛒 Agregado", "🔥 ¡Apurate!", "✅ Stock Reservado", "⏳ El tiempo corre"]

# ==========================================
# 2. ESTADO (INCLUYE TIMER)
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None

# --- LÓGICA DEL TIMER ---
if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Hola, soy Miguel.**\nCotizo aceros directo de fábrica. ¡Tenés 10 minutos de precios congelados!"}]

# ==========================================
# 3. BACKEND
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
    op = "ALTA" if monto > 1500000 else "MEDIA" if monto > 500000 else "BAJA"
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

def calcular_negocio():
    # 1. CHEQUEAR TIMER
    now = datetime.datetime.now()
    tiempo_restante = st.session_state.expiry_time - now
    segundos_restantes = int(tiempo_restante.total_seconds())
    
    oferta_activa = segundos_restantes > 0
    
    # Formato visual del reloj MM:SS
    if oferta_activa:
        mins, secs = divmod(segundos_restantes, 60)
        reloj_str = f"{mins:02d}:{secs:02d}"
        color_reloj = "#2e7d32" if mins > 2 else "#d32f2f" # Verde si hay tiempo, Rojo si falta poco
    else:
        reloj_str = "00:00"
        color_reloj = "#b0bec5" # Gris muerto

    bruto = sum(i['subtotal'] for i in st.session_state.cart)
    desc = 0 # Base 0 si se venció
    color = "#546e7a"; nivel = "PRECIO LISTA (EXPIRÓ)"; siguiente_meta = 1500000
    
    # 2. CALCULAR DESCUENTOS SOLO SI OFERTA ACTIVA
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO', 'CAÑO'] for x in st.session_state.cart)
    
    if oferta_activa:
        if bruto > 5000000:
            desc = 18; nivel = "👑 PARTNER MAX (18%)"; color = "#6200ea"; siguiente_meta = 0
        elif bruto > 3000000:
            desc = 15; nivel = "🏗️ CONSTRUCTOR (15%)"; color = "#d32f2f"; siguiente_meta = 5000000
        elif bruto > 1500000:
            if tiene_gancho: 
                desc = 15; nivel = "🔥 MAYORISTA (15%)"; color = "#d32f2f"; siguiente_meta = 5000000
            else:
                desc = 10; nivel = "🏢 OBRA (10%)"; color = "#f57c00"; siguiente_meta = 3000000
        else:
            # BASE CON EL 3% EXTRA
            if tiene_gancho:
                desc = 15; nivel = "🔥 MAYORISTA (15%)"; color = "#d32f2f"; siguiente_meta = 5000000
            else:
                desc = 3; nivel = "⚡ 3% EXTRA CONTADO"; color = "#2e7d32"; siguiente_meta = 1500000
    else:
        # Si expiró, se pierden los beneficios base, salvo los muy grandes que se mantienen por volumen puro
        if bruto > 5000000: desc = 15; nivel = "PARTNER (SIN BONUS)"; color = "#6200ea"
        else: desc = 0; nivel = "⚠️ OFERTA CADUCADA"; color = "#455a64"

    neto = bruto * (1 - (desc/100))
    return bruto, neto, desc, color, nivel, siguiente_meta, reloj_str, oferta_activa, color_reloj

def generar_link_wa(total):
    txt = "Hola Martín, confirmar pedido URGENTE:\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
    txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"

# ==========================================
# 4. UI: HEADER CON TIMER "TEMU STYLE"
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel, prox_meta, reloj, oferta_viva, color_timer = calcular_negocio()
porcentaje_barra = 100
if prox_meta > 0: porcentaje_barra = min((subtotal / prox_meta) * 100, 100)

st.markdown(f"""
    <style>
    .block-container {{ padding-top: 175px !important; padding-bottom: 60px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    
    .stTabs [data-baseweb="tab-list"] {{
        position: fixed; top: 95px; left: 0; width: 100%; background: white; z-index: 9999;
        display: flex; justify-content: space-around; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        padding-bottom: 5px;
    }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 10px; font-weight: bold; font-size: 0.9rem; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; width: 100%; background: white; z-index: 10000;
        border-bottom: 4px solid {color_barra};
        height: 95px;
    }}
    
    .top-strip {{ background: #111; color: #fff; padding: 5px 15px; display: flex; justify-content: space-between; font-size: 0.75rem; align-items: center; }}
    .cart-summary {{ padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; }}
    .price-tag {{ font-size: 1.5rem; font-weight: 900; color: #333; }}
    
    .badge {{ 
        background: {color_barra}; color: white; padding: 4px 12px; 
        border-radius: 4px; font-size: 0.75rem; font-weight: 900; text-transform: uppercase; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    
    /* RELOJ DE LA MUERTE */
    .timer-box {{
        color: {color_timer}; font-weight: 900; font-size: 0.8rem;
        background: #fff; padding: 2px 8px; border-radius: 4px; margin-left: 5px;
        animation: { 'blink 1s infinite' if not oferta_viva or reloj.startswith('00') else 'none' };
    }}
    
    @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
    
    .progress-container {{ width: 100%; height: 6px; background: #eee; position: absolute; bottom: 0; }}
    .progress-bar {{ height: 100%; width: {porcentaje_barra}%; background: {color_barra}; transition: width 0.8s ease-out; }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <span>🔥 PEDRO BRAVIN S.A.</span>
            <span>⏱️ EXPIRA EN: <span class="timer-box">{reloj}</span></span>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{nombre_nivel}</span>
                <div style="font-size:0.65rem; color:#666; margin-top:3px;">
                    {f"Ahorro extra aplicado: {desc_actual}%" if oferta_viva else "DESCUENTO PERDIDO"}
                </div>
            </div>
            <div class="price-tag">${total_final:,.0f} <span style="font-size:0.7rem; color:#666; font-weight:400;">+IVA</span></div>
        </div>
        <div class="progress-container"><div class="progress-bar"></div></div>
    </div>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# ==========================================
# 5. CEREBRO IA
# ==========================================
try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: st.error("Falta API KEY")

sys_prompt = f"""
ROL: Miguel, vendedor experto de Pedro Bravin S.A.
DB: {csv_context}
ZONA GRATIS: {CIUDADES_GRATIS}

📜 REGLAS INMUTABLES:
1. **LARGOS:** 12m (Perfiles/Hierro), 6.40m (Caños Epoxi/Galv), 6m (Resto).
2. **UNIDADES:** KG (Clavos), UNIDAD (Mallas), ROLLO (Agro).
3. **CHAPAS:** Acanalada=COD4, T101=COD6, Sin corte=METRO.
4. **LOGÍSTICA:** Gratis en Zona. Resto Estimado. Retiro en Planta.

🧨 **ESTRATEGIA URGENCIA (TIMER ACTIVO):**
- Dile al cliente que **APROVECHE EL 3% EXTRA ANTES DE QUE EL RELOJ LLEGUE A CERO.**
- Si el cliente duda, usa el tiempo: "Quedan pocos minutos para mantener este precio".

🕵️‍♂️ PROTOCOLO AMBIGÜEDAD:
- Si falta variante (Negro/Galv) -> PREGUNTAR.

SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO:TIPO]
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt).start_chat(history=[])

def procesar_vision(img):
    return st.session_state.chat_session.send_message(["Analiza lista. Usa urgencia del timer. Genera comandos [ADD...] y confirma.", img]).text

# ==========================================
# 6. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])

with tab1:
    # SI EXPIRÓ, MOSTRAR BOTÓN DE RESCATE
    if not oferta_viva:
        st.error("⚠️ ¡SE TE ACABÓ EL TIEMPO! PERDISTE EL DESCUENTO.")
        if st.button("🔄 SOLICITAR PRÓRROGA (REACTIVAR 3%)", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.toast("✅ ¡Salvado! Tiempo reiniciado.", icon="😅")
            st.rerun()

    with st.expander("📷 **Subir Foto de Lista**", expanded=False):
        img_val = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
        if img_val is not None:
            file_id = f"{img_val.name}_{img_val.size}"
            if st.session_state.last_processed_file != file_id:
                with st.spinner("👀 Analizando..."):
                    full_text = procesar_vision(Image.open(img_val))
                    news = parsear_ordenes_bot(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    st.session_state.last_processed_file = file_id
                    if news: st.toast("🔥 Productos Cargados!", icon='🛒')
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
            with st.spinner("Cotizando..."):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    full_text = response.text
                    news = parsear_ordenes_bot(full_text)
                    display = re.sub(r'\[ADD:.*?\]', '', full_text)
                    st.markdown(display)
                    
                    if news:
                        st.toast(random.choice(TOASTS_EXITO), icon='🛒')
                        st.markdown(f"""
                        <div style="background:#e8f5e9; padding:10px; border-radius:10px; border:1px solid #25D366; margin-top:5px;">
                            <strong>✅ {len(news)} items agregados.</strong><br>
                            <span style="font-size:0.85rem">💰 Total: ${total_final:,.0f} | ⏳ Quedan {reloj} min</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if desc_actual >= 15 and len(st.session_state.cart) > 1: st.balloons()

                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    log_interaction(prompt, total_final)
                    if news: time.sleep(1.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- PESTAÑA CARRITO ---
with tab2:
    if not st.session_state.cart:
        st.info("Carrito vacío. ¡Aprovechá el 3% extra antes de que termine el tiempo!")
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
            col_res1.markdown(f"**Beneficio {nombre_nivel}:**")
            col_res2.markdown(f"**-${subtotal * (desc_actual/100):,.0f}**")
        elif not oferta_viva:
            st.warning("⚠️ DESCUENTO EXPIRADO. SOLICITÁ PRÓRROGA EN LA PESTAÑA 'COTIZAR'.")
            
        st.markdown(f"""
        <div style="background:{color_barra}; color:white; padding:20px; border-radius:15px; text-align:center; margin-top:15px; box-shadow: 0 4px 15px {color_barra}66; border: 2px solid #fff;">
            <div style="font-size:0.8rem; opacity:0.9;">TOTAL FINAL CONTADO (+IVA)</div>
            <div style="font-size:2.2rem; font-weight:900;">${total_final:,.0f}</div>
            <div style="font-size:0.8rem; margin-top:5px; background:rgba(0,0,0,0.2); padding:4px 10px; border-radius:10px; display:inline-block;">
                { '⚡ 3% EXTRA APLICADO' if oferta_viva else '❌ PRECIO LISTA SIN DESCUENTO' }
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
