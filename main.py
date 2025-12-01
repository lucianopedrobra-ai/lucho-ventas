import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🏗️", layout="centered")

# --- 1. CONEXIÓN SEGURA CON GOOGLE ---
try:
    # Busca la clave en los secretos de Streamlit
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("🚨 Error Crítico: No se encontró la API KEY en los Secrets de Streamlit.")
    st.stop()

# --- 2. CONFIGURACIÓN DEL MODELO ---
# Usamos el modelo más compatible y rápido
MODELO_ELEGIDO = "gemini-1.5-flash"

generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
}

# --- 3. BASE DE DATOS (PRECIOS) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def cargar_precios():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except:
        return "Error al cargar la lista de precios."

csv_context = cargar_precios()

# --- 4. EL CEREBRO DE LUCHO (PROMPT V72) ---
SYSTEM_PROMPT = f"""
ROL: Eres Lucho, Ejecutivo Comercial Senior de Pedro Bravin Materiales.
OBJETIVO: Cotizar rápido, maximizar ticket y derivar a WhatsApp.

BASE DE DATOS (TU MEMORIA):
{csv_context}

REGLAS DE INTERACCIÓN:
1. Saludo: "Hola, buenas [mañanas/tardes]."
2. PROACTIVIDAD: "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. CANDADO DE DATOS: Antes de dar precio final, preguntá: "¿Tu Nombre y Localidad? (Para chequear envío gratis)".
4. LÍMITE: Tú solo reservas pedidos.

MATEMÁTICA Y PRODUCTOS:
* IVA: Precios del CSV son NETOS. **MULTIPLICA SIEMPRE POR 1.21**.
* TUBOS: Se venden por tira de 6.40m (Conducción) o 6.00m (Estructural).
* PLANCHUELAS: Precio por Unidad.
* AISLANTES: <$10k es x m2. >$10k es x rollo.

PROTOCOLOS DE VENTA:
* CHAPAS: Filtro Techo vs Lisa. Aislante Consultiva. Acopio Bolsa de Metros.
* TEJIDOS: Kit Completo (Eco -> Acindar).
* CONSTRUCCIÓN: Hierro ADN vs Liso. Upsell Alambre/Clavos.
* NO LISTADO: "Consulto stock en depósito".

CIERRE Y WHATSAPP:
1. Pedir: Nombre, CUIT, Teléfono.
2. Link WhatsApp con resumen.
   [✅ ENVIAR PEDIDO CONFIRMADO](LINK)
   "📍 Retiro: [LINK_MAPS]"
"""

# --- 5. INTERFAZ DE CHAT ---
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy? ¿Techado, rejas, pintura o construcción?"}
    ]

# Mostrar historial
for message in st.session_state.messages:
    avatar = "👷‍♂️" if message["role"] == "model" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Capturar input y responder
if prompt := st.chat_input("Escribí acá..."):
    # Mostrar usuario
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generar respuesta
    try:
        # Configurar modelo con el prompt de sistema
        model = genai.GenerativeModel(
            model_name=MODELO_ELEGIDO,
            system_instruction=SYSTEM_PROMPT
        )
        
        # Convertir historial al formato de la librería clásica
        chat_history = []
        for m in st.session_state.messages:
            if m["role"] != "system": # Ignoramos el system prompt en el historial
                role = "user" if m["role"] == "user" else "model"
                chat_history.append({"role": role, "parts": [m["content"]]})

        # Iniciar chat
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(prompt)
        
        # Mostrar respuesta
        text_response = response.text
        with st.chat_message("model", avatar="👷‍♂️"):
            st.markdown(text_response)
        st.session_state.messages.append({"role": "model", "content": text_response})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            st.warning("⏳ Estamos recibiendo muchas consultas. Por favor esperá 10 segundos e intentá de nuevo.")
        else:
            st.error(f"❌ Error de conexión: {error_msg}")
