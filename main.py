import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Lucho - Ventas", page_icon="🏗️", layout="centered")

# ==========================================
# 1. SEGURIDAD: CLAVE HÍBRIDA (FUNCIONA EN PC Y WEB)
# ==========================================
try:
    # Intenta buscar en la caja fuerte de la Web (Streamlit Cloud)
    API_KEY = st.secrets["AIzaSyCpVXuNBECIdpBVHU3bwRSv50AX1GI8i2c"]
except:
    # Si falla (porque estoy en mi PC), usa esta clave directa:
    API_KEY = "AIzaSyCpVXuNBECIdpBVHU3bwRSv50AX1GI8i2c"
except:
    st.error("⚠️ ERROR: No encontré la Clave API. Asegurate de haberla puesto en los 'Secrets' de Streamlit.")
    st.stop()

# ==========================================
# 2. CONEXIÓN CON TU LISTA DE PRECIOS (EN VIVO)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def cargar_precios():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string()
    except Exception as e:
        return f"ERROR CRÍTICO: No puedo leer la lista de precios. {e}"

csv_context = cargar_precios()

# ==========================================
# 3. EL CEREBRO DE LUCHO (MASTER PROMPT V72.0 - DEFINITIVO)
# ==========================================
system_instruction = f"""
ROL Y PERSONA:
Eres **Lucho**, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y **EXTREMADAMENTE CONCISO**. Tu objetivo es cotizar rápido, maximizar el ticket y derivar al humano.

BASE DE DATOS (TU MEMORIA):
{csv_context}

REGLAS DE INTERACCIÓN:
1. Saludo: "Hola, buenas [mañanas/tardes]."
2. PROACTIVIDAD: "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. CANDADO DE DATOS (PRE-COTIZACIÓN): Antes de dar el precio final, pregunta: "Para confirmarte si tenés **Envío Gratis**, decime: **¿Tu Nombre y de qué Localidad sos?**"
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".

DICCIONARIO TÉCNICO Y MATEMÁTICA (RAG):
* IVA: Precios CSV son NETOS. **MULTIPLICA SIEMPRE POR 1.21**.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x 6.40m) | Estructural (x 6.00m).
* PLANCHUELAS: Precio por UNIDAD (Barra).

PROTOCOLO DE VENTA POR RUBRO:
* CHAPAS: Filtro Techo vs Lisa. Aislación Consultiva (Doble Alu 10mm). Acopio "Bolsa de Metros". Estructura.
* TEJIDOS (Kit): Menor a Mayor (Eco -> Acindar). Ticket con Accesorios.
* REJA/CONSTRUCCIÓN: Cotiza material. Muestra diagrama ASCII para Rejas.
* NO LISTADOS: Si no está en CSV, fuerza handoff: "Consulto stock en depósito".

CROSS-SELL (PACK METALÚRGICO):
Preguntas RÁPIDAS al cerrar: Soldadura, Corte, Pintura, Protección.

MATRIZ DE NEGOCIACIÓN:
* ZONA ENVÍO SIN CARGO: El Trébol, María Susana, Piamonte, Landeta, San Jorge, Sastre, C. Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
* DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% General) | >$2M (14%).
* MEGA-VOLUMEN (> $10M): Muestra Ticket BASE. Deriva a Martín Zimaro (3401 52-7780).
* FINANCIACIÓN: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado +3% Extra. Tarjetas solo presencial.

FORMATO Y CIERRE:
* TICKET: Usa bloques de código ```text.
* FASE DE VALIDACIÓN: "¿Cómo lo ves [Nombre]? ¿Cerramos así o ajustamos algo?"
* PROTOCOLO DE CIERRE:
    1. PEDIDO ÚNICO: "Excelente. Para reservar, solo me falta: **CUIT/DNI y Teléfono**."
    2. LINK: Genera el link Markdown.
    * [✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)](LINK)
    * "O escribinos al: **3401-648118**"
    * "📍 **Retiro:** [LINK_MAPS]"
"""

# ==========================================
# 4. INTERFAZ DE CHAT (STREAMLIT)
# ==========================================
st.title("🏗️ Hablá con Lucho")
st.markdown("**Tu Ejecutivo Comercial Experto | Acindar Pymes**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés en mente hoy? ¿Techado, rejas, pintura o construcción?"})

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👷‍♂️" if message["role"] == "model" else "👤"):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribí tu consulta..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        client = genai.Client(api_key=API_KEY)
        historial_gemini = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            historial_gemini.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

        chat = client.chats.create(model="gemini-2.0-flash", config=types.GenerateContentConfig(system_instruction=system_instruction), history=historial_gemini)
        response = chat.send_message(prompt)
        text_response = response.text

        with st.chat_message("model", avatar="👷‍♂️"):
            st.markdown(text_response)
        st.session_state.messages.append({"role": "model", "content": text_response})

    except Exception as e:
        st.error(f"Error de conexión: {e}")
