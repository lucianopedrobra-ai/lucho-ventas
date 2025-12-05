import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. VARIABLES DE NEGOCIO (EL CEREBRO FINANCIERO) ---
DOLAR_BNA_REF = 1060.00  # Actualizar según cotización BNA Venta

# LISTA OFICIAL DE NODOS LOGÍSTICOS (ENVÍO GRATIS)
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 2. CONFIGURACIÓN VISUAL Y ESTILOS ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos nativos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- HEADER FIJO (STICKY) --- */
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

    /* Ajuste para que el chat no quede tapado por el header */
    .block-container { padding-top: 85px !important; }
    
    /* BOTÓN FINAL DE CIERRE */
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

# --- 5. CEREBRO DE VENTAS (OPTIMIZADO CON GAMIFICACIÓN) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.** (El Trébol, SF).
OBJETIVO: Traducir pedidos, definir rol, OPTIMIZAR LOGÍSTICA, y **MAXIMIZAR EL TICKET DE VENTA**.

BASE DE DATOS (PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR REFERENCIA: ${DOLAR_BNA_REF} (BNA Venta).
- **ZONA GRATIS (NODOS):** {CIUDADES_GRATIS}

🧠 **PROCESO DE PENSAMIENTO (4 FASES):**

**FASE 1: TRADUCTOR TÉCNICO**
* "Gas" -> EPOXI. "Agua" -> Galvanizado. "Hierro" -> ADN 420. "Malla 6" -> Q188. "Techo" -> Cincalum.

**FASE 2: ROL (Psicología)**
* **Commodity:** Se RÁPIDO.
* **Técnico:** Se CONSULTIVO (pregunta uso).

**FASE 3: CALCULADORA LOGÍSTICA INTELIGENTE (NODOS)**
Pregunta: "¿Para qué localidad es?".
1.  **¿Está en la lista GRATIS?** -> "¡Envío SIN CARGO!".
2.  **¿NO está en la lista? (Redireccionamiento)**
    * Busca mentalmente la ciudad de la 'ZONA GRATIS' más cercana al cliente (El Nodo).
    * *Ejemplo:* Si pide Esperanza -> Nodo más cercano: RAFAELA.
    * Calcula KM solo de ese tramo (Nodo <-> Cliente).
    * **FÓRMULA:** (KM del tramo x 2) * 0.85 USD * {DOLAR_BNA_REF} = Costo Estimado.
    * *Explicación:* "El envío va gratis hasta [Nodo] y solo cobramos el tramo ida y vuelta hasta tu obra ($XXX aprox)."

**FASE 4: CIERRE FINANCIERO Y GAMIFICACIÓN (GATILLOS)**
1.  **CÁLCULO DE TOTALES:** Suma mentalmente el total del pedido.
2.  **ESTRATEGIA DE DESCUENTO:**
    * **Si Total < $200.000:** Ofrece acopio y cierre normal.
    * **Si Total entre $200.000 y $299.999:** ⚠️ ALERTA DE OPORTUNIDAD.
      * *Di:* "⚠️ **¡Estás muy cerca!** Te faltan solo unos pesos para llegar a los $300.000 y desbloquear el **15% DE DESCUENTO MAYORISTA**. ¿Agregamos algo más (alambre, clavos, discos) para que te salga más barato?"
    * **Si Total >= $300.000:** 🎉 ÉXITO.
      * *Di:* "¡Felicitaciones! Accediste a la **TARIFA MAYORISTA (15% OFF)**."
3.  **ACOPIO:** "Podés congelar el precio hoy y lo acopiamos por **6 meses** sin cargo."

🚨 **REGLAS DE ORO:**
1.  **STOCK:** Solo confirma lo que ves en lista.
2.  **PRECIO:** Aclara "(Precio + IVA)".
3.  **CROSS-SELL:** Siempre intenta subir la venta si están cerca del descuento.

🚨 **FORMATO SALIDA WHATSAPP:**
[TEXTO_WHATSAPP]:
Hola Martín, cliente Web.
📍 Destino: [Localidad] (Logística: [Gratis / $Monto Redireccionado])
📋 Pedido (Acopio 6 meses posible):
- (COD: [SKU]) [Producto] x [Cant]
💰 Total Mat. IA: $[Monto] ([Aviso de Descuento si aplica])
¿Me confirmas final?
Datos: [Nombre/DNI]
"""

# --- 6. MODELO IA ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hola, soy Lucho de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás? (Hierros, perfiles, chapas...). Decime tu localidad para ver si tenés envío gratis."}]

if "chat_session" not in st.session_state:
    try:
        # Intento Principal: Gemini 2.5
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        try:
            # Fallback: Gemini 1.5 Pro
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except Exception:
            st.error("Error de conexión. Habla con Martín.")

# --- 7. CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 20 perfiles C para San Jorge..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Lucho está calculando costos y logística..."):
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
