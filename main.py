import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL Y ESTILOS ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos nativos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    
    /* ESTILO BOTÓN FINAL (VERDE WHATSAPP - GRANDE) */
    .whatsapp-btn-final {
        display: block; width: 100%; 
        background-color: #25D366; color: white !important;
        text-align: center; padding: 15px; border-radius: 10px;
        text-decoration: none; font-weight: bold; font-family: sans-serif;
        font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px; transition: all 0.2s;
    }
    .whatsapp-btn-final:hover { transform: scale(1.02); background-color: #1ebc57; }
    
    /* ESTILO BOTÓN SUPERIOR (CONTACTO DIRECTO - DISCRETO) */
    .martin-btn-top {
        display: inline-flex; align-items: center; justify-content: center; width: 100%;
        background-color: #128c7e; color: white !important;
        padding: 8px; border-radius: 6px; text-decoration: none;
        font-weight: 600; font-size: 0.9rem; margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .martin-btn-top:hover { background-color: #075e54; }
    
    /* AVATAR DEL CHAT */
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de sistema. Por favor contacta a Martín directamente.")
    st.stop()

# --- 3. CARGA DE DATOS (INVENTARIO CONFIRMADO) ---
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

# Preparación del contexto para la IA
if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ADVERTENCIA CRÍTICA: La lista de precios no está disponible. Pide al cliente que contacte a Martín."

# --- 4. ZONA FIJA SUPERIOR (SEGURIDAD Y CONTACTO) ---
with st.container():
    col_aviso, col_btn = st.columns([0.7, 0.3])
    
    with col_aviso:
        st.warning("🤖 **AVISO IA:** Precios y stock son estimados. Cotización final sujeta a confirmación por el vendedor.", icon="⚠️")
    
    with col_btn:
        # Enlace directo al WhatsApp de Martín (Salida de emergencia)
        st.markdown("""
        <a href="https://wa.me/5493401527780" target="_blank" class="martin-btn-top">
            💬 Hablar con Martín
        </a>
        """, unsafe_allow_html=True)

# --- 5. CEREBRO DE VENTAS (FUSIÓN DE ESTRATEGIAS) ---
sys_prompt = f"""
ROL: Eres Lucho, Asistente Virtual Especialista de **Pedro Bravin S.A.**
OBJETIVO: Asesorar técnicamente, cotizar y derivar el cierre a WhatsApp.

BASE DE DATOS (PRECIOS NETOS + STOCK):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **CEREBRO DUAL (TU LÓGICA DE ATENCIÓN):**

1.  **SI PIDEN COMMODITIES (Hierro, Malla, Clavos):**
    * MODO: "Despachante Rápido".
    * ACCIÓN: Confirma stock ("✅ Hay stock"), calcula precio total y cierra.
    * MALLAS: Si piden m2, calcula optimización (Mini vs Maxi) para menos desperdicio.

2.  **SI PIDEN TÉCNICOS (Perfiles, Chapas, Galpones):**
    * MODO: "Consultor Técnico".
    * ACCIÓN: Pregunta el uso (techo/entrepiso/luz) antes de dar precio para asegurar que lleven lo correcto.
    * CROSS-SELL: Ofrece siempre complementos (electrodos, discos).

🚨 **REGLAS DE ORO (OBLIGATORIAS):**
* **STOCK:** Solo vendes lo que ves en la lista. Si no está, ofrece alternativa.
* **PRECIO:** Siempre aclara: **"(Precio + IVA, sujeto a confirmación)"**.
* **DESCUENTO:** Si la suma > $300.000, aplica 15% OFF y celébralo.
* **ALAMBRE/CLAVOS:** Véndelos por KG (ofrece 1kg promedio).

📝 **FORMATO DE SALIDA (SOLO AL CONFIRMAR/CERRAR):**
[TEXTO_WHATSAPP]:
Hola Martín, soy cliente Web.
Cotización Pendiente de Revisión:
- (COD: [SKU]) [Producto] x [Cant]
Total Estimado IA: $[Monto]
¿Me confirmas stock y precio final?
Datos: [Nombre/DNI]
"""

# --- 6. GESTIÓN DE MODELOS (REDUNDANCIA 2.5 -> 1.5) ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola, soy Lucho. Estoy conectado al inventario.\n\n¿Qué materiales necesitas cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # INTENTO 1: Gemini 2.5 (Potencia máxima para contexto largo)
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            # INTENTO 2: Fallback a Gemini 1.5 Pro (Estabilidad)
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión. Por favor usa el botón de 'Hablar con Martín'.")

# --- 7. INTERFAZ DE CHAT ---
# Renderizar historial
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Capturar entrada usuario
if prompt := st.chat_input("Escribe aquí (Ej: Necesito 100m2 de malla)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Consultando precios y stock..."):
            response = chat.send_message(prompt)
            full_text = response.text
            
            # DETECCIÓN DE CIERRE (TAG WHATSAPP)
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_text:
                dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                
                # Mostrar respuesta verbal
                st.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                # Preparar Link WhatsApp
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                # Mostrar Botón de Cierre
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="whatsapp-btn-final">
                👉 CONFIRMAR PEDIDO CON MARTÍN
                </a>
                """, unsafe_allow_html=True)
            else:
                # Respuesta normal
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception as e:
        st.error("Hubo un error de conexión. Presiona el botón verde de arriba para hablar con Martín.")
