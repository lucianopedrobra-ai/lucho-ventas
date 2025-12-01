import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🏗️", layout="centered")

# 1. AUTENTICACIÓN
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("🚨 Error: Falta la API Key en los Secrets.")
    st.stop()

# 2. CARGA DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except:
        return "Error leyendo lista."

csv_context = load_data()

# 3. EL CEREBRO (PROMPT V72)
sys_prompt = f"""
ROL: Lucho, Ejecutivo Comercial Senior.
BASE DE DATOS: {csv_context}

REGLAS:
1. IVA: Precios son NETOS. MULTIPLICA SIEMPRE POR 1.21.
2. SEGURIDAD: Valida CANTIDAD antes de cotizar.
3. DATOS: Pide Nombre y Localidad antes del precio.
4. LÍMITE: Solo reservas pedidos.

PROTOCOLOS:
- TUBOS: 6.40m (Conducción) / 6.00m (Estructura).
- CHAPAS: Techo/Lisa. Aislante consultivo. Acopio.
- TEJIDOS: Kit Completo. Eco -> Acindar.
- REJA: Macizo vs Estructural. Diagrama ASCII.
- CONSTRUCCIÓN: Hierro ADN vs Liso. Upsell.

MATRIZ COMERCIAL:
- ENVÍO GRATIS: Zona El Trébol, San Jorge, Sastre, etc.
- DESCUENTOS: >150k (7% Chapa) | >500k (7% Gral) | >2M (14%).
- MEGA (>10M): Precio Base -> Derivar a Martín Zimaro (3401 52-7780).
- FINANCIACIÓN: Promo FirstData (Mié/Sáb). Contado +3%.

CIERRE:
1. Pedir: Nombre, CUIT, Teléfono.
2. Link WhatsApp con resumen.
   [✅ ENVIAR PEDIDO CONFIRMADO](LINK)
   "📍 Retiro: [LINK_MAPS]"
"""

# 4. INTERFAZ
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # MODELO FLASH (EL MÁS SEGURO)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=sys_prompt)
        
        # Historial simple
        history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages if m["role"] != "system"]
        
        chat = model.start_chat(history=history)
        response = chat.send_message(prompt)
        
        st.chat_message("assistant").write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"❌ Error: {e}")
        if "404" in str(e):
            st.info("💡 Consejo: Creá una API Key nueva en un PROYECTO NUEVO en Google AI Studio.")
