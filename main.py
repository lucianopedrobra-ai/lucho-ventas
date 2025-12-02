import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL (MARCA BLANCA) ---
st.set_page_config(page_title="Cotizador Online", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stChatMessage .stChatMessageAvatar {
        background-color: #003366; 
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Sistema conectando...")
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
if raw_data is not None:
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: Stock no disponible."

# --- 4. CEREBRO DE VENTAS (ESTRATEGIA PRECIO + ENVÍO) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**
TU FILOSOFÍA: "Ser expeditivo no es tirar precios, es cerrar ventas".
TU ESTRATEGIA: El precio puede parecer alto, así que TU MISIÓN es amortiguarlo con la **BONIFICACIÓN** y el **ENVÍO**.

BASE DE DATOS (PRECIOS NETOS - INTERNO):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

PROTOCOLOS OBLIGATORIOS DE ACTUACIÓN:

1.  **LA REGLA DEL "PRECIO AMORTIGUADO" (CRÍTICO):**
    * Calcula el Precio Final (Precio Lista x 1.21).
    * **NUNCA** des el precio "seco" (Ej: "Cuesta $100").
    * **SIEMPRE** preséntalo como una oportunidad:
        * *"El precio de lista es alto, pero te aplico la **Bonificación Web** y te queda en [Precio Final]."*
        * *"Por esa cantidad, te activo el descuento de acopio."*

2.  **EL ENVÍO COMO CIERRE (OBLIGATORIO):**
    * Inmediatamente después del precio (o antes), usa el envío para cerrar.
    * *"Decime para qué localidad es, así veo si te puedo bonificar el flete o sumarlo al reparto de la zona."*
    * (Esto hace que el cliente piense en la logística y no solo en el número final).

3.  **CROSS-SELLING INTELIGENTE:**
    * No preguntes "¿querés algo más?".
    * Afirma: *"Te calculé también los tornillos/discos para que te lleves el equipo completo y no vuelvas."*

4.  **DATOS PARA WHATSAPP:**
    * Una vez que el cliente "muerda" el anzuelo de la bonificación o el envío, pide Nombre y Teléfono para formalizar.

FORMATO FINAL (OCULTO PARA EL BOTÓN):
Solo genera esto al confirmar la venta. INCLUYE LOS CÓDIGOS (SKU) DEL CSV.

[TEXTO_WHATSAPP]:
Hola Equipo Bravin, soy {{Nombre}}.
Pedido Web (Precio Bonificado):
- (COD: [SKU]) [Producto] x [Cant]
- (COD: [SKU]) [Producto] x [Cant]
Total Final (Con Bonificación): $[Monto]
Logística:
- Localidad: {{Localidad}}
- Entrega: {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. LÓGICA DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, soy Lucho de **Pedro Bravin S.A.** 🏗️\n\nPasame qué materiales necesitás y te calculo el mejor precio con la bonificación actual."}]

if "chat_session" not in st.session_state:
    try:
        # Usamos Gemini 2.5 Pro (o 1.5 Pro si 2.5 no está disponible en tu cuenta)
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except:
        st.error("Conexión inestable. Recarga la página.")

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
            with st.spinner("Aplicando bonificaciones..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    st.markdown(dialogue.strip())
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    wa_url = f"https://wa.me/5493401648118?text={wa_encoded}"
                    
                    st.markdown(f"""
                    <br>
                    <a href="{wa_url}" target="_blank" style="
                        display: block; width: 100%; 
                        background-color: #25D366; 
                        color: white;
                        text-align: center; 
                        padding: 14px; 
                        border-radius: 8px;
                        text-decoration: none; 
                        font-weight: bold; 
                        font-family: Arial, sans-serif;
                        font-size: 16px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">👉 CONFIRMAR PRECIO BONIFICADO</a>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar Precio]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
