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
    /* Avatar Corporativo */
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de conexión. Verifique la API Key.")
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
    csv_context = "ERROR: No se pudo cargar la lista de precios. Cotizar manual."

# --- 4. CEREBRO DE VENTAS (MODO ESTABLE 1.5 FLASH) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.** (CERO vulgaridad. No uses 'maestro', 'genio'. Sé breve y directo).

BASE DE DATOS (STOCK Y PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **TRADUCTOR TÉCNICO:**
* "GAS" = EPOXI / REVESTIDO.
* "AGUA" = GALVANIZADO / HIDRO3.
* "TECHO" = CHAPA / T-101 / SINUSOIDAL.

🔥 **POLÍTICA DE PRECIOS (ESCALA 0-18%):**
Base de cálculo: (Precio CSV x 1.21).
Calcula el total y aplica descuento según escala:
1.  **< $100.000:** 0% OFF (Precio Lista).
2.  **$100k - $500k:** 5% OFF.
3.  **$500k - $1M:** 8% OFF.
4.  **$1M - $2M:** 12% OFF.
5.  **$2M - $3M:** 15% OFF.
6.  **> $3M:** 18% OFF.

⚠️ **REGLAS DE VENTA:**
1.  **PRECIOS:** Aclara siempre que son **CONTADO / TRANSFERENCIA**.
2.  **TARJETAS:** "Con tarjeta aplica recargo financiero. ¡Aprovechá la PROMO BOMBA Miércoles y Sábados!".
3.  **LOGÍSTICA:** Obligatorio preguntar: "¿Localidad de entrega?" para coordinar.

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant]
Total Contado/Transf: $[Monto]
*Consulta Financiación: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\nIndícame qué materiales necesitás y te paso el mejor precio de contado."}]

if "chat_session" not in st.session_state:
    try:
        # CORRECCIÓN DEFINITIVA: Usamos 'gemini-1.5-flash'. 
        # Es el modelo más estable y rápido para producción web hoy.
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=sys_prompt)
        
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

if prompt := st.chat_input("Ej: 5 caños de gas 1 pulgada..."):
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
                    
                    # DESTINO: MARTÍN (3401 52-7780)
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
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar Pedido]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
