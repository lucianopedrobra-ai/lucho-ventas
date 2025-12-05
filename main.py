import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00  # Dólar Venta BNA

# NODOS LOGÍSTICOS (Lugares donde el camión ya va gratis)
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* HEADER FIJO */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #fff3cd; border-bottom: 2px solid #ffeeba;
        color: #856404; padding: 10px 20px; z-index: 99999;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-family: sans-serif;
    }
    .header-btn {
        background-color: #128c7e; color: white !important; text-decoration: none;
        padding: 8px 15px; border-radius: 5px; font-weight: bold; font-size: 0.9rem;
        white-space: nowrap; transition: background 0.3s;
    }
    .header-btn:hover { background-color: #075e54; }
    .header-text { font-size: 0.9rem; line-height: 1.3; margin-right: 15px; }
    .block-container { padding-top: 85px !important; }
    
    /* BOTÓN WHATSAPP */
    .whatsapp-btn-final {
        display: block; width: 100%; background-color: #25D366; color: white !important;
        text-align: center; padding: 15px; border-radius: 10px; text-decoration: none;
        font-weight: bold; font-family: sans-serif; font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 10px; transition: all 0.2s;
    }
    .whatsapp-btn-final:hover { transform: scale(1.02); background-color: #1ebc57; }
    
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    
    @media (max-width: 600px) {
        .fixed-header { flex-direction: column; gap: 8px; text-align: center; padding: 10px; }
        .block-container { padding-top: 110px !important; }
    }
    </style>
    
    <div class="fixed-header">
        <div class="header-text">
            🤖 <strong>IA:</strong> Precios/Stock y Fletes estimados. <strong>Lista Web Parcial.</strong><br>
            Cotización final sujeta a revisión por Martín.
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="header-btn">
            💬 Hablar con Martín
        </a>
    </div>
    """, unsafe_allow_html=True)

# --- 3. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de sistema. Contacte a Martín.")
    st.stop()

# --- 4. CARGA DE DATOS ---
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
    csv_context = "ERROR: Lista no disponible."

# --- 5. CEREBRO DE VENTAS (LOGÍSTICA IDA Y VUELTA REFORZADA) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.** (El Trébol, SF).
OBJETIVO: Traducir pedidos, definir rol, OPTIMIZAR LOGÍSTICA (Nodos) y cerrar venta.

BASE DE DATOS (PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR REF: ${DOLAR_BNA_REF} (BNA Venta).
- **ZONA GRATIS (NODOS):** {CIUDADES_GRATIS}

🧠 **PROCESO DE PENSAMIENTO (4 FASES):**

**FASE 1: TRADUCTOR TÉCNICO**
* "Gas" -> EPOXI. "Agua" -> Galvanizado. "Hierro" -> ADN 420. "Malla 6" -> Q188. "Techo" -> Cincalum.

**FASE 2: ROL (Psicología)**
* **Commodity:** Se RÁPIDO.
* **Técnico:** Se CONSULTIVO (pregunta uso).

**FASE 3: CALCULADORA LOGÍSTICA INTELIGENTE (IDA Y VUELTA AL NODO)**
Pregunta: "¿Para qué localidad es?".
1.  **¿Está en la lista GRATIS?** -> "¡Envío SIN CARGO!".
2.  **¿NO está en la lista? (Ej: Esperanza, Gálvez)**
    * Busca en tu mapa mental la ciudad de la 'ZONA GRATIS' más cercana (El Nodo).
    * *Ejemplo:* Si pide Esperanza -> El Nodo gratis más cercano es RAFAELA.
    * Calcula los KM solo de ese tramo (Rafaela <-> Esperanza).
    * **FÓRMULA OBLIGATORIA:** (KM del tramo x 2) * 0.85 USD * {DOLAR_BNA_REF} = Costo Estimado.
    * *Explicación al cliente:* "El envío va gratis hasta [Nodo Cercano] y solo te cobramos el redireccionamiento ida y vuelta hasta tu obra ($XXX aprox)."

**FASE 4: CIERRE (Acopio)**
* **ACOPIO:** "Podés congelar el precio hoy y lo acopiamos por **6 meses** sin cargo."
* **MAYORISTA:** > $300.000 = **15% OFF**.

🚨 **REGLAS DE ORO:**
1.  **STOCK:** Solo confirma lo que ves en lista.
2.  **PRECIO:** Aclara "(Precio + IVA)".
3.  **CROSS-SELL:** Ofrece complementos.

🚨 **FORMATO SALIDA WHATSAPP:**
[TEXTO_WHATSAPP]:
Hola Martín, cliente Web.
📍 Destino: [Localidad] (Logística: [Gratis / $Monto por Redireccionamiento])
📋 Pedido (Acopio 6 meses posible):
- (COD: [SKU]) [Producto] x [Cant]
💰 Total Mat. IA: $[Monto]
¿Me confirmas final?
Datos: [Nombre/DNI]
"""

# --- 6. MODELO IA ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola, soy Lucho de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás? Decime tu localidad para calcular si el envío es gratis."}]

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
            st.error("Error de conexión. Habla con Martín.")

# --- 7. CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 10 chapas para Esperanza..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Lucho está calculando logística..."):
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
                👉 CONFIRMAR PEDIDO Y FLETE
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception:
        st.error("Error de conexión. Usa el botón superior.")
