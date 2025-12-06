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
# 1. CONFIGURACIÓN E INFRAESTRUCTURA
# ==========================================
st.set_page_config(
    page_title="Pedro Bravin S.A. | Cotizador Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded" # Abrimos sidebar para mostrar el carro
)

# --- VARIABLES ---
DOLAR_BNA = 1060.00
COSTO_FLETE_KM_USD = 0.85
CIUDADES_GRATIS = ["EL TREBOL", "LOS CARDOS", "LAS ROSAS", "SAN GENARO", "CENTENO", "CASAS", "CAÑADA ROSQUIN", "RAFAELA", "SAN JORGE", "CARLOS PELLEGRINI", "MARIA JUANA", "SASTRE", "SAN FRANCISCO"]

# --- ESTADO (SESSION STATE) ---
if "cart" not in st.session_state: st.session_state.cart = [] # El corazón del sistema
if "log_data" not in st.session_state: st.session_state.log_data = []
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola. Soy Miguel. Decime qué materiales necesitás y armamos el acopio ya mismo."}]
if "link_compra_activo" not in st.session_state: st.session_state.link_compra_activo = None

# ==========================================
# 2. FUNCIONES DE LÓGICA (PYTHON PURO)
# ==========================================

def calcular_total_cart():
    total = sum(item['subtotal'] for item in st.session_state.cart)
    return total

def aplicar_descuento(monto):
    # Reglas de negocio duras (Python, no IA)
    descuento = 3
    nivel = "INICIAL"
    color = "#90a4ae"
    
    # Detectar si hay productos "Gancho" en el carrito
    tiene_gancho = any(x['tipo'] in ['CHAPA', 'PERFIL', 'HIERRO'] for x in st.session_state.cart)
    
    if tiene_gancho:
        descuento = 15
        nivel = "MAYORISTA 🔥"
        color = "#d50000"
    elif monto > 3000000:
        descuento = 15
        nivel = "OBRA GRANDE"
        color = "#d50000"
    elif monto > 1500000:
        descuento = 10
        nivel = "PROFESIONAL"
        color = "#ffa726"
    
    total_con_descuento = monto * (1 - (descuento/100))
    return total_con_descuento, descuento, nivel, color

def parsear_ordenes_bot(texto_respuesta):
    """
    Busca comandos ocultos en la respuesta del bot para agregar al carro.
    Formato esperado: [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO:TIPO]
    """
    patron = r'\[ADD:(\d+):([^:]+):([\d\.]+):([^\]]+)\]'
    coincidencias = re.findall(patron, texto_respuesta)
    
    items_agregados = []
    for cant, prod, precio, tipo in coincidencias:
        cantidad = int(cant)
        precio_unit = float(precio)
        subtotal = cantidad * precio_unit
        
        # Agregar al estado
        item = {
            "cantidad": cantidad,
            "producto": prod.strip(),
            "precio_unit": precio_unit,
            "subtotal": subtotal,
            "tipo": tipo.strip() # Para saber si es gancho
        }
        st.session_state.cart.append(item)
        items_agregados.append(item)
        
    return items_agregados

def generar_link_whatsapp(total_final):
    # Genera el texto detallado para Martín
    texto = "Hola Martín, quiero confirmar este pedido:\n"
    for item in st.session_state.cart:
        texto += f"- {item['cantidad']}x {item['producto']}\n"
    texto += f"\n💰 TOTAL WEB CERRADO: ${total_final:,.0f} + IVA"
    return f"https://wa.me/5493401527780?text={urllib.parse.quote(texto)}"

# ==========================================
# 3. INTERFAZ: SIDEBAR (CARRITO)
# ==========================================

with st.sidebar:
    st.header("🛒 TU ACOPIO")
    
    if not st.session_state.cart:
        st.info("Tu carro está vacío. Pedile algo a Miguel.")
    else:
        # Mostrar items
        for i, item in enumerate(st.session_state.cart):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{item['cantidad']}x** {item['producto']}")
                st.caption(f"${item['precio_unit']:,.0f} c/u")
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
        
        st.divider()
        
        # Cálculos Matemáticos Reales
        subtotal_bruto = calcular_total_cart()
        total_neto, porc_desc, nombre_nivel, color_nivel = aplicar_descuento(subtotal_bruto)
        ahorro = subtotal_bruto - total_neto
        
        st.write(f"Subtotal: ${subtotal_bruto:,.0f}")
        
        if ahorro > 0:
            st.markdown(f"""
            <div style="background-color:{color_nivel}; padding:10px; border-radius:5px; color:white; text-align:center;">
                <strong>🎉 {nombre_nivel} ({porc_desc}%)</strong><br>
                Ahorrás: ${ahorro:,.0f}
            </div>
            """, unsafe_allow_html=True)
            
        st.metric(label="TOTAL FINAL (+IVA)", value=f"${total_neto:,.0f}")
        
        # Botón de cierre real
        link_wa = generar_link_whatsapp(total_neto)
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="
                display:block; width:100%; background-color:#25D366; color:white; 
                text-align:center; padding:12px; border-radius:8px; 
                text-decoration:none; font-weight:bold; margin-top:10px;">
                ✅ FINALIZAR COMPRA
            </a>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Vaciar Carrito"):
            st.session_state.cart = []
            st.rerun()

# ==========================================
# 4. CEREBRO IA (GOOGLE GEMINI)
# ==========================================
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except: st.error("Falta API KEY")

# Simulamos base de datos (aquí cargarías tu CSV real)
CSV_DATA_SIMULADA = """
PRODUCTO,PRECIO,TIPO,STOCK
CHAPA C25,22000,CHAPA,ALTO
CHAPA C27,18000,CHAPA,MEDIO
PERFIL C 100,35000,PERFIL,ALTO
HIERRO 8MM,8000,HIERRO,BAJO
MALLA SIMA,45000,VARIOS,ALTO
CLAVOS,5000,VARIOS,ALTO
AISLANTE,12000,VARIOS,ALTO
"""

sys_prompt = f"""
ROL: Eres Miguel, vendedor técnico.
OBJETIVO: Identificar qué quiere el usuario y generar COMANDOS para llenar el carrito.
BASE DE DATOS:
{CSV_DATA_SIMULADA}

⚡ REGLAS CRÍTICAS DE RESPUESTA:
1. SI EL USUARIO PIDE UN PRODUCTO, DEBES AGREGARLO AL FINAL DE TU TEXTO EN ESTE FORMATO EXACTO:
   [ADD:CANTIDAD:NOMBRE_EXACTO_DB:PRECIO_NUMERICO:TIPO]
   
   Ejemplo: El usuario pide "10 chapas del 25".
   Tu respuesta: "Excelente, te agrego las chapas C25 que son eternas. [ADD:10:CHAPA C25:22000:CHAPA]"

2. NO CALCULES TOTALES EN EL TEXTO. De eso se encarga el sistema. Tú vende la calidad y la urgencia.
3. SI NO ENCUENTRAS EL PRODUCTO EXACTO, ofrece el más parecido.
4. MANTÉN EL TONO "TEMU": Urgencia, stock limitado, oportunidad.

ZONA DE ENVÍO:
Si preguntan flete, calcula: (KM * 2 * {COSTO_FLETE_KM_USD} * {DOLAR_BNA}).
"""

model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# ==========================================
# 5. CHAT CENTRAL
# ==========================================

st.title("🏭 Pedro Bravin S.A.")

# Historial
for msg in st.session_state.messages:
    # Ocultamos los tags técnicos [ADD:...] del historial visual para que no se vea feo
    content_clean = re.sub(r'\[ADD:.*?\]', '', msg["content"])
    if content_clean.strip():
        st.chat_message(msg["role"]).write(content_clean)

# Input
if prompt := st.chat_input("Ej: Necesito 10 chapas y 5 perfiles"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    with st.spinner("Buscando stock..."):
        response = st.session_state.chat_session.send_message(prompt)
        full_text = response.text
        
        # 1. Parsear comandos y actualizar carro
        items_nuevos = parsear_ordenes_bot(full_text)
        
        # 2. Limpiar texto para mostrar al usuario
        text_display = re.sub(r'\[ADD:.*?\]', '', full_text)
        
        # 3. Guardar y mostrar
        st.session_state.messages.append({"role": "assistant", "content": full_text})
        st.chat_message("assistant").write(text_display)
        
        # 4. Feedback visual si se agregó algo
        if items_nuevos:
            st.toast(f"✅ Se agregaron {len(items_nuevos)} productos al carro", icon="🛒")
            time.sleep(0.5)
            st.rerun() # Recarga para actualizar el Sidebar
