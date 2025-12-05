import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

# Ocultamos elementos de la interfaz de Streamlit que no sirven al cliente
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    
    /* Estilo del Botón de WhatsApp */
    .whatsapp-btn {
        display: block; width: 100%; 
        background-color: #25D366; color: white !important;
        text-align: center; padding: 15px; border-radius: 10px;
        text-decoration: none; font-weight: bold; font-family: sans-serif;
        font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px;
    }
    .whatsapp-btn:hover {
        background-color: #1ebc57;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error interno de configuración. Contacte a soporte.")
    st.stop()

# --- 3. CARGA DE DATOS (INVENTARIO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.fillna("")
        return df 
    except Exception:
        return None

raw_data = load_data()

if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ADVERTENCIA: No se pudo leer la lista de precios. Responde cordialmente que verifiquen por WhatsApp."

# --- 4. PROMPT MAESTRO (ESTRATEGIA FUSIÓN) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.** (Materiales Siderúrgicos).
OBJETIVO: Asesorar técnicamente y cerrar la venta enviando al cliente a WhatsApp.

BASE DE DATOS (STOCK REAL Y PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **PROTOCOLO DE ATENCIÓN INTELIGENTE:**

1.  **DETECTAR EL ROL DEL PRODUCTO:**
    * Si piden **Hierros/Mallas/Clavos (Commodities)**: Sé RÁPIDO. Confirma stock, da el precio total y pide cerrar.
    * Si piden **Perfiles/Chapas/Galpones (Técnico)**: Sé CONSULTIVO. Pregunta para qué lo usarán (techo, entrepiso, columna) y valida si el material es el correcto antes de dar precio.

2.  **REGLAS DE ORO:**
    * **Stock:** Si está en la lista, di "✅ Tengo stock disponible en Santa Fe".
    * **Mallas:** Si piden $m^2$, calcula cuántas hojas (Mini o Maxi) necesitan para tener MENOS desperdicio.
    * **Precios:** Son Netos + IVA.
    * **Descuentos:** Si la suma supera $300.000, aplica 15% de descuento y avísalo con entusiasmo.
    * **Cross-Sell:** Al vender hierros, ofrece siempre alambre y clavos.

3.  **CIERRE (EL EMBUDO):**
    * Calcula el total estimado.
    * Pregunta: "¿Te preparo el pedido para congelar el precio?"

📝 **FORMATO SALIDA WHATSAPP (Solo al confirmar):**
[TEXTO_WHATSAPP]:
Hola Martín, soy cliente Web.
Cotización (A confirmar):
- (COD: [SKU]) [Producto] x [Cant]
- [Accesorio Sugerido]
Total Estimado: $[Monto]
¿Me confirmas disponibilidad para transferir?
Datos: [Nombre/DNI]
"""

# --- 5. GESTIÓN DE MODELOS (REDUNDANCIA) ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola, soy **Lucho**. Estoy conectado al depósito.\n\n¿Qué materiales necesitas cotizar hoy? (Perfiles, mallas, chapas, etc.)"}]

if "chat_session" not in st.session_state:
    try:
        # INTENTO 1: Usar la potencia de Gemini 2.5 (Si está disponible)
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        # Intentamos nombres comunes del modelo nuevo
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            # INTENTO 2: Fallback a Gemini 1.5 Pro (Estable)
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception as e:
            st.error(f"Error de conexión con IA. Refresca la página.")

# --- 6. INTERFAZ DE CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: Necesito 100m2 de malla y perfiles C..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Lucho está calculando..."):
            response = chat.send_message(prompt)
            full_text = response.text
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_text:
                dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                st.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="whatsapp-btn">
                👉 FINALIZAR PEDIDO EN WHATSAPP
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception as e:
        st.error("Hubo un pequeño error de comunicación. Por favor intenta de nuevo.")
