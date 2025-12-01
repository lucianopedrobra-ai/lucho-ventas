import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🏗️", layout="centered")

# 1. AUTENTICACIÓN
try:
    # Intenta obtener la API key de los secretos de Streamlit
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    # Si la clave no se encuentra, muestra un error y detiene la ejecución
    st.error("🚨 Error: Falta la API Key 'GOOGLE_API_KEY' en los Secrets de Streamlit.")
    st.stop()
except Exception as e:
    # Maneja otros errores de configuración
    st.error(f"🚨 Error de configuración de Gemini: {e}")
    st.stop()

# 2. CARGA DE DATOS
# URL para la hoja de cálculo de Google Sheet en formato CSV
# ¡CORREGIDA! Ahora usando el enlace más reciente proporcionado por el usuario.
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    """Carga los datos desde la URL de la hoja de cálculo y los convierte a string."""
    try:
        # Intenta leer el CSV
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        # Convierte el DataFrame a una cadena de texto sin el índice para usar como contexto
        return df.to_string(index=False)
    except Exception as e:
        # Manejo de errores de carga de datos
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg:
            st.error(
                f"🚨 Error 404 (Not Found) al cargar datos: El link en SHEET_URL es incorrecto o la hoja de cálculo NO está publicada 'al público' como archivo CSV. "
                f"Vaya a 'Archivo > Compartir > Publicar en la web', seleccione el formato '.csv' y reemplace el link en la variable SHEET_URL."
            )
        else:
            st.error(f"Error inesperado leyendo la lista de productos: {e}")
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

# Inicializa el historial de mensajes
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?"}]

# Muestra los mensajes anteriores en el chat
for msg in st.session_state.messages:
    # Mapea el rol de la API a la función de mensaje de Streamlit
    role = "assistant" if msg["role"] == "model" else msg["role"]
    st.chat_message(role).write(msg["content"])

# Captura la entrada del usuario
if prompt := st.chat_input():
    # Muestra el mensaje del usuario
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # Usamos el identificador del modelo gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025', system_instruction=sys_prompt)
        
        # Prepara el historial para la API
        history = [
            {"role": "model" if m["role"] == "assistant" else m["role"], "parts": [{"text": m["content"]}]}
            for m in st.session_state.messages if m["role"] != "system"
        ]
        
        # Inicia el chat con el historial
        chat = model.start_chat(history=history)
        
        # Envía el mensaje y espera la respuesta
        response = chat.send_message(prompt)
        
        # Muestra la respuesta y la guarda en el estado de sesión
        st.chat_message("assistant").write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        # Manejo de errores
        st.error(f"❌ Error en la llamada a la API de Gemini: {e}")
        if "404" in str(e) or "not found" in str(e).lower():
            # Consejo para el usuario en caso de error 404
            st.info("💡 Consejo: El nombre del modelo puede ser incorrecto o su clave API no tiene acceso. Intente usar un alias diferente o crear una nueva clave.")
