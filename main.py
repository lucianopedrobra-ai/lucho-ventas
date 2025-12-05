import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 2. CONFIGURACIÓN VISUAL (REBRANDING TOTAL) ---
st.set_page_config(
    page_title="Asesor Técnico | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inyectamos FontAwesome para los iconos dentro de Streamlit
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
    /* LIMPIEZA INTERFAZ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* FUENTE GLOBAL */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    }

    /* --- HEADER FLOTANTE MODERNO --- */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ffffff; /* Fondo Blanco Limpio */
        border-bottom: 1px solid #e0e0e0;
        padding: 10px 20px; z-index: 99999;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .header-branding {
        display: flex; flex-direction: column;
    }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .brand-disclaimer { color: #666; font-size: 0.75rem; margin-top: 2px; }
    
    /* BOTÓN WHATSAPP HEADER (Estilo Pastilla) */
    .wa-pill-btn {
        background-color: #25D366; color: white !important;
        text-decoration: none; padding: 8px 16px; border-radius: 50px;
        font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2); transition: transform 0.2s;
    }
    .wa-pill-btn:hover { transform: scale(1.05); background-color: #1ebc57; }

    /* ESPACIO PARA EL CHAT */
    .block-container { padding-top: 85px !important; padding-bottom: 40px !important; }

    /* --- CHAT BURBUJAS --- */
    /* Bot (Lucho) */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px;
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar {
        background-color: #0f2c59; color: white;
    }
    
    /* Usuario */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #fff;
    }

    /* BOTÓN FINAL DE CIERRE (TARJETA) */
    .final-action-card {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 700; font-size: 1.1rem; margin-top: 20px;
        box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        transition: transform 0.2s;
    }
    .final-action-card:hover { transform: translateY(-3px); box-shadow: 0 15px 30px rgba(37, 211, 102, 0.4); }

    /* AVISOS INTERNOS */
    .alert-box {
        padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem;
        border-left: 4px solid #ff6b00; background-color: #fff8f0; color: #555;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    @media (max-width: 600px) {
        .fixed-header { padding: 8px 15px; }
        .brand-disclaimer { font-size: 0.65rem; }
        .wa-pill-btn span { display: none; } /* En móvil solo icono */
        .wa-pill-btn { padding: 8px 12px; }
    }
    </style>
    
    <div class="fixed-header">
        <div class="header-branding">
            <span class="brand-name">Lucho | Pedro Bravin S.A.</span>
            <span class="brand-disclaimer">⚠️ Precios y Stock estimados (Web Parcial)</span>
        </div>
        <a href="https://wa.me/5493401527780" target="_blank" class="wa-pill-btn">
            <i class="fa-brands fa-whatsapp" style="font-size: 1.2rem;"></i>
            <span>Hablar con Martín</span>
        </a>
    </div>
    """, unsafe_allow_html=True)

# --- 3. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Sistema en mantenimiento.")
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
    csv_context = "ERROR: Base de datos no accesible."

# --- 5. CEREBRO DE VENTAS (Prompt Comercial) ---
sys_prompt = f"""
ROL: Eres Lucho, **Asesor Técnico Virtual** de **Pedro Bravin S.A.**
TONO: Profesional, Resolutivo, Experto.
OBJETIVO: Filtrar dudas técnicas, cotizar logística y cerrar ventas.

BASE DE DATOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
OPERACIONES:
- DÓLAR BNA: ${DOLAR_BNA_REF}
- ZONA GRATIS: {CIUDADES_GRATIS}

🧠 **ESTRATEGIA DE RESPUESTA:**

1.  **TRADUCCIÓN:** "Gas" = Epoxi, "Estructural" = Tubo c/costura, "Techo" = Cincalum.
2.  **LOGÍSTICA:**
    * Si es **ZONA GRATIS**: ¡Véndelo como beneficio!
    * Si es **LEJOS**: Calcula el redireccionamiento (KM x 2 x 0.85 USD). Sé transparente.
3.  **GAMIFICACIÓN DE PRECIOS:**
    * **< $200k:** Cierre normal.
    * **$200k - $299k:** ⚠️ "Estás cerca del MAYORISTA. Agrega algo para llegar a $300k y ganar el **15% OFF**".
    * **> $300k:** "¡Tarifa MAYORISTA activada (15% OFF)!".
4.  **ACOPIO:** "Congelá precio hoy y guardamos 6 meses gratis."

🚨 **REGLAS:**
* Si no está en lista: "No figura en web, pero consultame con Martín."
* Precios siempre **MAS IVA**.

📝 **FORMATO SALIDA:**
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual.
📍 Destino: [Localidad]
📋 Pedido:
- (COD: [SKU]) [Producto] x [Cant]
💰 Inversión Est. IA: $[Monto] ([Nota])
Solicito confirmación final.
Datos: [Nombre/DNI]
"""

# --- 6. GESTIÓN DE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Bienvenido a Pedro Bravin S.A.**\n\nSoy Lucho, tu asesor técnico. Cotizo materiales y logística en tiempo real.\n\n**¿Qué estás buscando hoy?**"}]

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
            st.error("Error de conexión.")

# --- 7. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 20 chapas para San Jorge..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Analizando stock y logística..."):
            response = chat.send_message(prompt)
            full_text = response.text
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_text:
                dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                
                st.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                # BOTÓN FINAL DE ALTO IMPACTO
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="final-action-card">
                    <i class="fa-brands fa-whatsapp"></i> CONFIRMAR PEDIDO CON MARTÍN
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception:
        st.error("Error de conexión. Use el botón superior.")
