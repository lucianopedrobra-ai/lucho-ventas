import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import time

# --- 1. VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Asesor Técnico | Pedro Bravin S.A.",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }

    /* HEADER FLOTANTE */
    .fixed-header {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ffffff; border-bottom: 1px solid #e0e0e0;
        padding: 10px 20px; z-index: 99999;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .header-branding { display: flex; flex-direction: column; }
    .brand-name { color: #0f2c59; font-weight: 800; font-size: 0.95rem; text-transform: uppercase; }
    .brand-disclaimer { color: #666; font-size: 0.75rem; }
    
    .wa-pill-btn {
        background-color: #25D366; color: white !important;
        text-decoration: none; padding: 8px 16px; border-radius: 50px;
        font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2); transition: transform 0.2s;
    }
    .wa-pill-btn:hover { transform: scale(1.05); background-color: #1ebc57; }

    .block-container { padding-top: 85px !important; padding-bottom: 40px !important; }

    /* CHAT */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

    /* TARJETA FINAL */
    .final-action-card {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 700; font-size: 1.1rem; margin-top: 20px;
        box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        transition: transform 0.2s;
    }
    .final-action-card:hover { transform: translateY(-3px); }
    
    @media (max-width: 600px) {
        .fixed-header { padding: 8px 15px; }
        .wa-pill-btn span { display: none; }
    }
    </style>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
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
    st.error("⚠️ Error crítico de API KEY. Verifique secrets.")
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
    csv_context = "ERROR CRÍTICO: No se pudo leer la lista de precios."

# --- 5. LOGS ---
def log_interaction(user_text, bot_response):
    opportunity = "NORMAL"
    if "$" in bot_response:
        try:
            precios = [int(s.replace('.','')) for s in re.findall(r'\$([\d\.]+)', bot_response) if s.replace('.','').isdigit()]
            if any(p > 300000 for p in precios):
                opportunity = "🔥 ALTA (MAYORISTA)"
        except:
            pass
    print(f"LOG: {user_text} | Oportunidad: {opportunity}")

# --- 6. CEREBRO DE VENTAS ---
sys_prompt = f"""
ROL: Eres Lucho, **Asesor Técnico Virtual** de **Pedro Bravin S.A.** (El Trébol, SF).
OBJETIVO: Cotizar EXCLUSIVAMENTE lo que hay en lista, calcular logística y cerrar.

BASE DE DATOS (INVENTARIO WEB):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR BNA: ${DOLAR_BNA_REF}
- ZONA GRATIS: {CIUDADES_GRATIS}

🚨 **REGLA DE ORO (IMPUESTOS):**
* Los precios del CSV son **NETOS**.
* **OBLIGATORIO:** Escribe **"+ IVA"** al lado de cada precio.
* **PROHIBIDO:** Decir "Precio Final".

🔒 **PROTOCOLOS DE SEGURIDAD:**
1.  **SI ESTÁ EN CSV:** Cotiza precio exacto + IVA. Confirma Stock.
2.  **SI NO ESTÁ:** DI: "No figura en mi lista web, pero **te lo agrego al pedido como 'A cotizar'** para que Martín te pase el precio." (No inventes precio).

🧠 **ESTRATEGIA COMERCIAL:**
1.  **TRADUCCIÓN:** "Gas"=EPOXI, "Estructural"=Tubo c/costura, "Techo"=Cincalum.
2.  **LOGÍSTICA:**
    * GRATIS -> ¡Véndelo como beneficio!
    * NO GRATIS -> Busca NODO CERCANO. Calcula (KM ida y vuelta al nodo) x 0.85 USD x Dolar.
3.  **GAMIFICACIÓN:**
    * $200k-$299k -> "⚠️ Estás cerca del MAYORISTA (15% OFF). ¿Agregamos algo?".
    * >$300k -> "🎉 ¡Tarifa MAYORISTA activada (15% OFF)!".
4.  **CIERRE:** "Acopio 6 meses gratis."

📝 **FORMATO SALIDA:**
[TEXTO_WHATSAPP]:
Hola Martín, vengo del Asesor Virtual.
📍 Destino: [Localidad]
📋 Pedido Web:
- (COD: [SKU]) [Producto] x [Cant]
⚠️ A Cotizar Manual (Sugeridos):
- [Items sin precio web]
💰 Inversión Est. IA: $[Monto] + IVA ([Nota])
Solicito confirmación final.
Datos: [Nombre/DNI]
"""

# --- 7. GESTIÓN DE SESIÓN INTELIGENTE (EL BUSCADOR DE CEREBROS) ---
def get_working_chat_session(system_instruction):
    # Lista de prioridad de modelos (Del más potente al más compatible)
    model_candidates = [
        "gemini-1.5-pro",       # EL MEJOR (Estable)
        "gemini-1.5-flash",     # El rápido (Backup sólido)
        "gemini-2.0-flash-exp", # Experimental
        "gemini-pro"            # El viejo confiable
    ]
    
    generation_config = {"temperature": 0.2, "max_output_tokens": 8192}

    for model_name in model_candidates:
        try:
            # Intento de conexión
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction, generation_config=generation_config)
            chat = model.start_chat(history=[])
            # Prueba de fuego (opcional): verificar si el objeto chat se creó bien
            if chat:
                print(f"✅ Conectado exitosamente con: {model_name}") 
                return chat
        except Exception as e:
            print(f"⚠️ Falló {model_name}, intentando siguiente...")
            continue
    
    return None # Si fallan los 4, devolvemos Vacío

# Inicialización de Mensajes
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Bienvenido a Pedro Bravin S.A.**\n\nSoy Lucho, tu asesor técnico.\n\n**¿Qué materiales necesitas cotizar hoy?**"}]

# Inicialización del Chat (Con Lógica Anti-Caídas)
if "chat_session" not in st.session_state:
    with st.spinner("Conectando con el servidor inteligente..."):
        session = get_working_chat_session(sys_prompt)
        if session:
            st.session_state.chat_session = session
        else:
            st.error("⚠️ Error Crítico: Los servidores de IA están ocupados. Por favor recarga la página en 30 segundos.")

# --- 8. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 20 chapas para San Jorge..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        # Verificamos si la sesión está viva antes de usarla
        if "chat_session" in st.session_state and st.session_state.chat_session:
            chat = st.session_state.chat_session
            with st.spinner("Analizando stock y calculando (Precios + IVA)..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                log_interaction(prompt, full_text)
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    
                    if "15%" in dialogue or "MAYORISTA" in dialogue:
                        st.balloons()
                        st.toast('🎉 ¡Ahorro Mayorista Detectado!', icon='💰')
                    
                    st.markdown(dialogue.strip())
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                    
                    st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="final-action-card">
                        <i class="fa-brands fa-whatsapp" style="margin-right:8px;"></i> CONFIRMAR PEDIDO CON MARTÍN
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
        else:
             st.warning("🔄 Reconectando sesión...")
             # Reintento de emergencia
             new_session = get_working_chat_session(sys_prompt)
             if new_session:
                 st.session_state.chat_session = new_session
                 st.rerun() # Recargar para procesar el mensaje
             else:
                 st.error("No hay conexión disponible.")
                
    except Exception as e:
        # Si falla en medio de la charla, intentamos reconectar una vez más
        st.warning("⚠️ Pequeña interrupción. Reintentando...")
        try:
            st.session_state.chat_session = get_working_chat_session(sys_prompt)
            st.rerun()
        except:
            st.error("Error de conexión. Por favor usa el botón verde superior.")
