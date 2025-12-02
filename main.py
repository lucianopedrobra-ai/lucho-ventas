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
        # Leemos todo como string para proteger la data
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.fillna("")
        return df 
    except Exception:
        return None

raw_data = load_data()

# Contexto simplificado para la IA
if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: LISTA VACÍA."

# --- 4. CEREBRO DE VENTAS (FUSIÓN: LÓGICA + CIERRE AGRESIVO) ---
sys_prompt = f"""
ROL: Eres Lucho, Vendedor de **Pedro Bravin S.A.**
TU MISIÓN: Cotizar rápido y conseguir que el cliente haga CLIC en el botón de WhatsApp.

BASE DE DATOS (PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

⚡ **REGLAS DE ORO (STOCK Y MEDIDAS):**
1.  **NO INVENTES:** Si el producto no está en la lista, di: *"No tengo eso exacto, pero te ofrezco esto que es similar:"* y da la opción de la lista.
2.  **MEDIDAS EXACTAS:**
    * Si piden **Tejido 1.50m**, busca códigos con "150". Si solo hay "125", **AVISA**: *"Tengo de 1.25m en oferta"*.
    * Caños: Vienen de 6.40m.
    * Perfiles: Vienen de 6.00m.

💰 **MOTOR DE PRECIOS (TU CALCULADORA):**
1.  Toma el Precio de Lista del CSV.
2.  Súmale IVA (**x 1.21**).
3.  Multiplica por la cantidad.
4.  **APLICA DESCUENTO AUTOMÁTICO (SEGÚN TOTAL):**
    * < $100k: 0% OFF.
    * $100k - $500k: 5% OFF.
    * $500k - $1M: 8% OFF.
    * > $1M: 12% OFF.
    * > $3M: 18% OFF.
    * **SI ES CHAPA/HIERRO > $300k:** **15% OFF DIRECTO.**

🚀 **EL CIERRE (OBLIGATORIO):**
En cuanto des el precio, **NO PREGUNTES "¿TE GUSTA?"**.
Di esto:
*"El precio de lista es $X, pero con la Bonificación Web te queda en **$Y Final**. ¿Para qué localidad es? Confirmame y te reservo el stock ya."*

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Martín, soy {{Nombre}}.
Quiero reservar:
- (COD: [SKU]) [Producto] x [Cant]
Total c/Descuento: $[Monto]
Datos: {{Localidad}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho de **Pedro Bravin S.A.** 🏗️\n\n¿Qué materiales estás buscando hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # INTENTO 1: Modelo Nuevo (Rápido)
        model = genai.GenerativeModel('gemini-2.0-flash-lite-preview-02-05', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        # INTENTO 2: Modelo Estable (Seguro)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception as e:
            st.error(f"Error de sistema: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 40 metros de tejido 1.50..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Cotizando..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    st.markdown(dialogue.strip())
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                    
                    st.markdown(f"""
                    <br>
                    <a href="{wa_url}" target="_blank" style="
                        display: block; width: 100%; 
                        background-color: #25D366; color: white;
                        text-align: center; padding: 14px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: Arial, sans-serif;
                    ">👉 CONFIRMAR PEDIDO (A Martín)</a>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
