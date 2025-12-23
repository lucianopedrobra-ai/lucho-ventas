#app.py
import streamlit as st
import datetime
import random
import time
from PIL import Image
import google.generativeai as genai
import os
import re
import pandas as pd 

# IMPORTAR MÓDULOS PROPIOS
from config import *
from funciones import *
from estilos import cargar_estilos, auto_scroll

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="🔥 OFERTAS PEDRO BRAVIN", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicializar datos externos
DOLAR_BNA = obtener_dolar_bna() 
csv_context = load_data()

# ==========================================
# 2. ESTADO
# ==========================================
if "cart" not in st.session_state: st.session_state.cart = []
if "log_data" not in st.session_state: st.session_state.log_data = []
if "admin_mode" not in st.session_state: st.session_state.admin_mode = False
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None
if "discount_tier_reached" not in st.session_state: st.session_state.discount_tier_reached = 0

if "expiry_time" not in st.session_state:
    st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)

if "messages" not in st.session_state:
    saludo = """
 **Soy Miguel.** Dólar actualizado. Stock disponible.

👇 **PASAME TU PEDIDO YA** (Escribí o usá los botones rápidos).
*¡El precio se congela por 3 minutos!* ⏳
    """
    st.session_state.messages = [{"role": "assistant", "content": saludo}]

# ==========================================
# 3. CEREBRO IA (MODO NEXT-GEN 2.0)
# ==========================================
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    elif "GOOGLE_API_KEY" in os.environ:
        api_key = os.environ.get("GOOGLE_API_KEY")
except: pass

if api_key:
    try: genai.configure(api_key=api_key)
    except: pass

if "chat_session" not in st.session_state:
    if not api_key:
        st.error("🚨 ERROR CRÍTICO: Falta la API KEY en Secrets.")
    else:
        sys_prompt = get_sys_prompt(csv_context, DOLAR_BNA)
        
        # ⚠️ ESTRATEGIA DE CONEXIÓN:
        intentos = [
            "gemini-2.0-flash-exp", # Tu prioridad (Tecnología nueva)
            "gemini-1.5-flash",     # Intermedio
            "gemini-pro"            # Respaldo total (Legacy)
        ]
        
        connected_model = None
        error_log = []
        
        for modelo in intentos:
            try:
                st.session_state.chat_session = genai.GenerativeModel(
                    modelo, system_instruction=sys_prompt
                ).start_chat(history=[])
                connected_model = modelo
                break 
            except Exception as e:
                error_log.append(f"{modelo}: {e}")
                continue 

        if not connected_model:
            st.error(f"⚠️ Todos los modelos fallaron. Log: {error_log}")

# ==========================================
# 4. UI: HEADER Y ESTILOS
# ==========================================
subtotal, total_final, desc_actual, color_barra, nombre_nivel, prox_meta, seg_restantes, oferta_viva, color_timer, reloj_python, dinero_ahorrado = calcular_negocio()
porcentaje_barra = 100
if prox_meta > 0: porcentaje_barra = min((subtotal / prox_meta) * 100, 100)

display_precio = f"${total_final:,.0f}" if subtotal > 0 else "COTIZAR"
display_iva = "+IVA" if subtotal > 0 else ""
display_badge = nombre_nivel[:25] + "..." if len(nombre_nivel) > 25 and subtotal > 0 else (nombre_nivel if subtotal > 0 else "⚡ 3% OFF")
subtext_badge = f"🔥 AHORRAS: ${dinero_ahorrado:,.0f}" if dinero_ahorrado > 0 else "TIEMPO LIMITADO"

cargar_estilos(color_barra, porcentaje_barra, color_timer, reloj_python, display_badge, subtext_badge, display_precio, display_iva, seg_restantes, generar_link_wa, total_final, oferta_viva)

# ==========================================
# 5. INTERFAZ TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 COTIZAR", f"🛒 MI PEDIDO ({len(st.session_state.cart)})"])
spacer = '<div style="height: 20px;"></div>'

with tab1:
    st.markdown(spacer, unsafe_allow_html=True)
    if not oferta_viva:
        st.error("⚠️ PRECIOS EXPIRADOS")
        if st.button("🔄 RECARGAR PRECIOS", type="primary", use_container_width=True):
            st.session_state.expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTOS_OFERTA)
            st.rerun()

    if 0 < prox_meta - subtotal < 200000 and oferta_viva:
        st.toast(f"🚨 ¡FALTAN ${prox_meta - subtotal:,.0f} PARA DESCUENTO! SUMÁ PINTURA O DISCOS.", icon="🔥")

    for m in st.session_state.messages:
        if m["role"] != "system":
            # LIMPIEZA VISUAL POTENTE
            clean = re.sub(r'\[ADD:.*?\]', '', m["content"])
            clean = clean.replace("[TEXTO VISIBLE]", "").replace("SALIDA:", "").strip()
            
            if clean: st.chat_message(m["role"], avatar="👷‍♂️" if m["role"]=="assistant" else "👤").markdown(clean)

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
                            txt = procesar_input(Image.open(img), True)
                            news = parsear_ordenes_bot(txt)
                            st.session_state.messages.append({"role": "assistant", "content": txt})
                            st.session_state.last_processed_file = fid
                            if news: st.balloons()
                            st.rerun()
    
    # --- BOTONES RÁPIDOS ---
    if not st.session_state.cart and oferta_viva:
        st.caption("Atajos rápidos:")
        cb1, cb2, cb3 = st.columns(3)
        if cb1.button("🏗️ Hierros", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Hola, necesito precio de hierros de 6mm, 8mm y 10mm."})
            st.rerun()
        if cb2.button("🏠 Techos", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Cotizame chapa cincalum y perfiles C para un techo de 40m2."})
            st.rerun()
        if cb3.button("💰 Ofertas", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "¿Qué tenés en oferta hoy para llegar al descuento mayorista?"})
            st.rerun()

    if p := st.chat_input("Escribí acá..."):
        if p == "#admin": st.session_state.admin_mode = not st.session_state.admin_mode; st.rerun()
        st.session_state.messages.append({"role": "user", "content": p})
        st.chat_message("user").markdown(p)
        with st.chat_message("assistant", avatar="👷‍♂️"):
            with st.spinner("Calculando logística y stock..."):
                try:
                    res = procesar_input(p)
                    if res.startswith("⚠️ ERROR"):
                        st.error(res)
                    else:
                        news = parsear_ordenes_bot(res)
                        
                        # LIMPIEZA VISUAL EN TIEMPO REAL
                        display = re.sub(r'\[ADD:.*?\]', '', res)
                        display = display.replace("[TEXTO VISIBLE]", "").replace("SALIDA:", "").strip()
                        
                        st.markdown(display)
                        
                        if news: 
                            st.toast(random.choice(TOASTS_EXITO), icon='🔥')
                            if desc_actual >= 12: st.balloons()
                        
                        st.session_state.messages.append({"role": "assistant", "content": res})
                        if news: time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error crítico en UI: {e}")

with tab2:
    st.markdown(spacer, unsafe_allow_html=True)
    if not st.session_state.cart:
        st.info("Carrito vacío. Agregá items para ver el precio final.")
    else:
        indices_to_remove = []
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                c1.markdown(f"**{item['producto']}**\n<span style='color:grey;font-size:0.8em'>${item['precio_unit']:,.0f} unit</span>", unsafe_allow_html=True)
                
                nueva_cant = c2.number_input("Cant", 0.0, value=float(item['cantidad']), key=f"q_{i}", label_visibility="collapsed")
                
                if nueva_cant != item['cantidad']:
                    if nueva_cant == 0:
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
            st.rerun()
        
        st.markdown(f"""<a href="{generar_link_wa(total_final)}" target="_blank" style="display:block; width:100%; background: #333; color:white; margin-top:20px; text-align:center; padding:15px; border-radius:12px; text-decoration:none; font-weight:bold; opacity:0.8;">Link Alternativo de Pago</a>""", unsafe_allow_html=True)
        if st.button("Vaciar Carrito", use_container_width=True): st.session_state.cart = []; st.rerun()

auto_scroll()
if st.session_state.admin_mode: st.dataframe(pd.DataFrame(st.session_state.log_data))
