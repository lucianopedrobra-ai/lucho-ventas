import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL Y ESTILOS ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos nativos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- HEADER FIJO (STICKY) --- */
    /* Esto crea la barra superior que se mueve con la pantalla */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: #fff3cd; /* Amarillo suave alerta */
        border-bottom: 2px solid #ffeeba;
        color: #856404;
        padding: 10px 20px;
        z-index: 99999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-family: sans-serif;
    }
    
    /* Botón Martín dentro del Header */
    .header-btn {
        background-color: #128c7e;
        color: white !important;
        text-decoration: none;
        padding: 8px 15px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9rem;
        white-space: nowrap;
        transition: background 0.3s;
    }
    .header-btn:hover { background-color: #075e54; }
    
    /* Texto del aviso */
    .header-text {
        font-size: 0.9rem;
        line-height: 1.3;
        margin-right: 15px;
    }

    /* --- AJUSTE DE CUERPO --- */
    /* Empujamos el chat hacia abajo para que no quede tapado por el header */
    .block-container {
        padding-top: 85px !important;
    }
    
    /* --- BOTÓN FINAL (VERDE WHATSAPP - GRANDE) --- */
    .whatsapp-btn-final {
        display: block; width: 100%; 
        background-color: #25D366; color: white !important;
        text-align: center; padding: 15px; border-radius: 10px;
        text-decoration: none; font-weight: bold; font-family: sans-serif;
        font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px; transition: all 0.2s;
    }
    .whatsapp-btn-final:hover { transform: scale(1.02); background-color: #1ebc57; }
    
    /* Avatar del Chat */
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    
    /* Ajuste para móviles */
    @media (max-width: 600px) {
        .fixed-header { flex-direction: column; gap: 8px; text-align: center; padding: 10px; }
        .block-container { padding-top: 110px !important; }
        .header-text { margin-right: 0; font-size: 0.8rem; }
        .header-btn { width: 100%; padding: 6px; }
    }
    </style>
    
    <div class="fixed-header">
        <div class="header-text">
            🤖 <strong>IA:</strong> Precios/Stock estimados. <strong>Lista Web Parcial (Consultar otros).</strong><br>
            Cotización final sujeta a revisión por Martín.
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="header-btn">
            💬 Hablar con Martín
        </a>
    </div>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de sistema. Por favor usa el botón de WhatsApp directo.")
    st.stop()

# --- 3. CARGA DE DATOS ---
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

# Preparar contexto CSV
if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: Lista no disponible. Derivar a vendedor humano."

# --- 4. CEREBRO DE VENTAS (MISMAS REGLAS CONFIRMADAS) ---
sys_prompt = f"""
ROL: Eres Lucho, Experto en Aceros de **Pedro Bravin S.A.**
OBJETIVO: Interpretar pedidos técnicos, verificar stock y cerrar ventas en WhatsApp.

BASE DE DATOS (PRECIOS NETOS + STOCK REAL):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **FASE 1: TRADUCTOR SIDERÚRGICO (ARGENTINA)**
Traduce el lenguaje coloquial del cliente a tu CSV:
* "Caño de Gas" -> Busca **"EPOXI"**.
* "Caño de Agua" -> Busca **"Galvanizado"** o **"Polipropileno"**.
* "Hierro del [4.2/6/8/10]" -> Busca Barras **ADN 420** del diámetro correspondiente.
* "Malla del 6" -> Busca Malla **15x15 Ø6 (Q188)**.
* "Chapa de Techo" -> Busca **"Cincalum"** (Acannalada/Trapezoidal).
* "Chapa Negra" -> Busca **"Laminada Caliente"**.

🧠 **FASE 2: ESTRATEGIA DE VENTA (EL ROL)**
Una vez identificado el producto, actúa según su tipo:
* **SI ES COMMODITY (Hierros, Mallas, Clavos, Caños Standard):**
    * MODO: **"Despachante Rápido"**.
    * ACCIÓN: Confirma stock ("✅ Hay stock"), da precio total y pide cerrar. ¡No des vueltas!
    * *Tip Mallas:* Si piden m2, calcula optimización (Mini vs Maxi) para reducir desperdicio.
* **SI ES TÉCNICO (Perfiles C/U, Chapas Especiales, Galpones):**
    * MODO: **"Ingeniero Consultivo"**.
    * ACCIÓN: Antes de dar precio, valida el uso. "¿Para qué luz de techo es?" "¿Qué espesor de chapa (14, 16, 18) buscás?". Asesora y luego vende.

🚨 **REGLAS COMERCIALES BLINDADAS:**
1.  **STOCK:** Solo confirmas lo que está en el CSV. Si no hay, di: **"No lo veo en la lista web, pero consultame con Martín que seguro lo conseguimos"**.
2.  **PRECIO:** Siempre aclara **"(Precio + IVA, sujeto a confirmación)"**.
3.  **DESCUENTOS:** Compra > $300.000 = **15% OFF**.
4.  **CROSS-SELL:** Hierros -> Ofrece Alambre/Clavos. Perfiles -> Ofrece Electrodos.

📝 **FORMATO SALIDA WHATSAPP (OBLIGATORIO):**
[TEXTO_WHATSAPP]:
Hola Martín, soy cliente Web.
Cotización (A revisar):
- (COD: [SKU]) [Producto Detectado] x [Cant]
Total Estimado IA: $[Monto]
¿Me confirmas disponibilidad?
Datos: [Nombre/DNI]
"""

# --- 5. GESTIÓN DE MODELOS ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola, soy Lucho. ¿Qué materiales necesitas? (Ej: Caño gas, malla del 6, perfiles...)"}]

if "chat_session" not in st.session_state:
    try:
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión IA. Por favor habla con Martín.")

# --- 6. INTERFAZ DE CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Escribe tu consulta aquí..."):
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
                <a href="{wa_url}" target="_blank" class="whatsapp-btn-final">
                👉 CONFIRMAR CON MARTÍN
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception:
        st.error("Error de conexión. Usa el botón superior para contactar a Martín.")
