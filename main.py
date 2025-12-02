import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Cotizador Online", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de conexión.")
    st.stop()

# --- 3. CARGA DE DATOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        df = df.dropna(how='all', axis=1)
        return df 
    except Exception:
        return None

raw_data = load_data()
csv_context = raw_data.to_string(index=False) if raw_data is not None else "ERROR: Sin precios."

# --- 4. CEREBRO DE VENTAS (ESTABLE 1.5 PRO) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.** (CERO vulgaridad).

BASE DE DATOS (PRECIOS NETOS):
{csv_context}

TRADUCTOR TÉCNICO:
* "GAS" = EPOXI / REVESTIDO.
* "AGUA" = GALVANIZADO / HIDRO3.
* "TECHO" = CHAPA / T-101 / SINUSOIDAL.

POLÍTICA DE PRECIOS (5-12-18%):
Base: (Precio CSV x 1.21). Aplica:
1. NIVEL 1 (<$100k): 0% OFF.
2. NIVEL 2 ($100k-$500k): 5% OFF.
3. NIVEL 3 ($500k-$1M): 8% OFF.
4. NIVEL 4 ($1M-$2M): 12% OFF.
5. NIVEL 5 ($2M-$3M): 15% OFF.
6. NIVEL 6 (>$3M): 18% OFF.

REGLAS:
1. PRECIO: Siempre precio final con bonificación aplicada.
2. LOGÍSTICA: Pregunta siempre "¿Localidad de entrega?".
3. FINANCIACIÓN: "Tarjeta con recargo financiero. ¡Promo Miércoles y Sábados disponible!".

FORMATO FINAL (SOLO AL CONFIRMAR):
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant]
Total Final: $[Monto]
*Consulta Financiación: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\nIndícame material y medidas para cotizar."}]

if "chat_session" not in st.session_state:
    try:
        # MODELO: gemini-1.5-pro (El más estable para producción)
        model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except Exception as e:
        st.error(f"Error de sistema: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Escribe tu consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Cotizando..."):
                response = chat.send_message(prompt)
                full_text = response.text
                if "[TEXTO_WHATSAPP]:" in full_text:
                    dialogue, wa_part = full_text.split("[TEXTO_WHATSAPP]:", 1)
                    st.markdown(dialogue.strip())
                    wa_url = f"https://wa.me/5493401527780?text={urllib.parse.quote(wa_part.strip())}"
                    st.markdown(f"""<br><a href="{wa_url}" target="_blank" style="display: block; width: 100%; background-color: #25D366; color: white; text-align: center; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: bold; font-family: Arial, sans-serif;">👉 CONFIRMAR PEDIDO (A Martín)</a>""", unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
