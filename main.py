import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho - Ventas", page_icon="🏗️", layout="centered")
API_KEY = st.secrets["AIzaSyCpVXuNBECIdpBVHU3bwRSv50AX1GI8i2c"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def cargar_precios():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string()
    except Exception as e:
        return f"ERROR CRÍTICO: No puedo leer la lista de precios. {e}"

csv_context = cargar_precios()

system_instruction = f"""
ROL: Eres Lucho, Ejecutivo Comercial Senior. Conciso.
OBJETIVO: Cotizar, Maximizar Ticket y Derivar.

BASE DE DATOS: {csv_context}

REGLAS:
1. Saludo: "Hola, buenas [mañanas/tardes]."
2. PROACTIVIDAD: "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. CANDADO: No des precio sin saber CANTIDAD.
4. LÍMITE: Tú solo "reservas la orden".

DICCIONARIO TÉCNICO:
* IVA: Precios CSV son NETOS. MULTIPLICA SIEMPRE POR 1.21.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x6.40m) | Estructural (x6.00m).
* PLANCHUELAS: Precio por UNIDAD.

PROTOCOLOS:
* CHAPAS: Filtro Techo vs Lisa. Aislación Consultiva. Acopio "Bolsa de Metros".
* TEJIDOS (Kit): Menor a Mayor. Ticket con Accesorios.
* REJA: Macizo vs Estructural. Diagrama ASCII.
* NO LISTADOS: Si no está en CSV, fuerza handoff: "Consulto stock".

CROSS-SELL: Soldadura, Corte, Pintura, Protección.

MATRIZ NEGOCIACIÓN:
* ENVÍO GRATIS: El Trébol, San Jorge, Sastre, Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
* DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% Gral) | >$2M (14%).
* MEGA (>10M): Muestra Base -> Deriva a Martín Zimaro (3401 52-7780).
* FINANCIACIÓN: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado +3%.

CIERRE:
1. Pedir: Nombre, CUIT/DNI, Teléfono.
2. Link WhatsApp: https://wa.me/5493401648118
"""

st.title("🏗️ Hablá con Lucho")
st.markdown("**Tu Ejecutivo Comercial Experto | Acindar Pymes**")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés en mente hoy?"})

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="👷‍♂️" if message["role"] == "model" else "👤"):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribí tu consulta..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        client = genai.Client(api_key=API_KEY)
        historial = []
        for m in st.session_state.messages:
            r = "user" if m["role"] == "user" else "model"
            historial.append(types.Content(role=r, parts=[types.Part.from_text(text=m["content"])]))

        chat = client.chats.create(model="gemini-2.0-flash", config=types.GenerateContentConfig(system_instruction=system_instruction), history=historial)
        response = chat.send_message(prompt)
        
        with st.chat_message("model", avatar="👷‍♂️"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "model", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
