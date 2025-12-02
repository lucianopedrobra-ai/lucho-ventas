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
    st.error("⚠️ Iniciando sistema...")
    st.stop()

# --- 3. DATOS ---
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

# --- 4. CEREBRO DE VENTAS (CON DICCIONARIO DE SINÓNIMOS) ---
sys_prompt = f"""
ROL: Eres Lucho, Cotizador Oficial de **Pedro Bravin S.A.**
TONO: Vendedor astuto. Tu objetivo es subir el volumen de venta.

BASE DE DATOS (TU VERDAD ABSOLUTA):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **TRADUCTOR DE PRODUCTOS (IMPORTANTE):**
El cliente usa palabras comunes, tú busca el técnico en la lista:
* Si piden **"GAS"** -> Busca **"EPOXI"** o **"REVESTIDO"**. (¡SÍ VENDEMOS EPOXI!).
* Si piden **"AGUA"** -> Busca **"GALVANIZADO"** o **"HIDRO"**.
* Si piden **"TECHO"** -> Busca **"CHAPA"**, **"CINCALUM"**, **"COLOR"**.
* Si piden **"CERCO"** -> Busca **"MALLA"**, **"TEJIDO"**, **"ROMBOIDAL"**.

🔥 **POLÍTICA DE BONIFICACIONES (ESCALA 5-12-18%):**
Base: (Precio CSV x 1.21). Sobre eso aplica:
1.  **NIVEL 1 (5% OFF):** Consultas chicas/sueltas. "Promo Web".
2.  **NIVEL 2 (12% OFF):** Proyectos (Techo completo, >10 un). "Pack Obra".
3.  **NIVEL 3 (18% OFF):** Acopio/Mayorista. "Cierre Ya".

⚠️ **REGLA DE ORO:** * Confía en tu lista. Si dice "Epoxi", ES GAS. No digas que no vendemos.
* Siempre muestra el PRECIO FINAL con el descuento ya aplicado.

**LOGÍSTICA:**
Siempre pregunta: *"¿Para qué localidad es?"*.

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada: [5%/12%/18%]):
- (COD: [SKU]) [Producto] x [Cant]
Total Final: $[Monto calculado]
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. LÓGICA DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, soy Lucho de **Pedro Bravin S.A.** 🏗️\n\n¿Qué materiales necesitás? Tengo stock en perfiles, chapas, caños epoxi y ferretería."}]

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except:
        st.error("Reconectando...")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: Necesito caños para gas de 1 pulgada..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Buscando en stock..."):
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
                        background-color: #25D366; color: white;
                        text-align: center; padding: 14px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: Arial, sans-serif;
                    ">👉 CONFIRMAR CON DESCUENTO</a>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
