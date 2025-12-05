import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re
import datetime
import requests  # Necesario para enviar datos al formulario

# --- 1. CONFIGURACIÓN DE ANALÍTICAS (GOOGLE FORMS) ---
# PASO 1: Crea un Google Form con 3 campos de texto.
# PASO 2: Obtén el "link prellenado" para sacar los ID de los campos (entry.123456).
URL_FORM_GOOGLE = ""  # Pega aquí la URL de acción del form (termina en /formResponse)
ID_CAMPO_CLIENTE = "entry.xxxxxx" # ID para el texto del cliente
ID_CAMPO_MONTO = "entry.xxxxxx"   # ID para el monto
ID_CAMPO_OPORTUNIDAD = "entry.xxxxxx" # ID para el nivel de oportunidad

# --- 2. VARIABLES DE NEGOCIO ---
DOLAR_BNA_REF = 1060.00 
CIUDADES_GRATIS = """
EL TREBOL, LOS CARDOS, LAS ROSAS, SAN GENARO, CENTENO, CASAS, CAÑADA ROSQUIN, 
SAN VICENTE, SAN MARTIN DE LAS ESCOBAS, ANGELICA, SUSANA, RAFAELA, SUNCHALES, 
PRESIDENTE ROCA, SA PEREIRA, CLUCELLAS, ESTACION CLUCELLAS, MARIA JUANA, SASTRE, 
SAN JORGE, LAS PETACAS, ZENON PEREYRA, CARLOS PELLEGRINI, LANDETA, MARIA SUSANA, 
PIAMONTE, VILA, SAN FRANCISCO.
"""

# --- 3. CONFIGURACIÓN VISUAL ---
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

    /* CHAT ESTILO WHATSAPP/MESSENGER */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) { background-color: #f8f9fa; border: 1px solid #eee; border-radius: 10px; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) .stChatMessageAvatar { background-color: #0f2c59; color: white; }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) { background-color: #fff; }

    /* TARJETA FINAL DE CIERRE */
    .final-action-card {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; text-align: center; padding: 18px; 
        border-radius: 12px; text-decoration: none; display: block;
        font-weight: 700; font-size: 1.1rem; margin-top: 20px;
        box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        transition: transform 0.2s;
        border: 2px solid white;
    }
    .final-action-card:hover { transform: translateY(-3px); box-shadow: 0 15px 25px rgba(37, 211, 102, 0.4); }
    
    /* MODAL DE CARGA */
    .stSpinner > div { border-top-color: #0f2c59 !important; }
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

# --- 4. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Sistema en mantenimiento.")
    st.stop()

# --- 5. CARGA DE DATOS ---
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
    csv_context = "ERROR CRÍTICO: Base de datos no accesible."

# --- 6. SISTEMA DE METRICAS Y LOGS ---
if "log_data" not in st.session_state:
    st.session_state.log_data = []

def enviar_a_google_form(cliente, monto, oportunidad):
    """Envía los datos silenciosamente a Google Forms si está configurado"""
    if URL_FORM_GOOGLE and "docs.google.com" in URL_FORM_GOOGLE:
        try:
            payload = {
                ID_CAMPO_CLIENTE: str(cliente),
                ID_CAMPO_MONTO: str(monto),
                ID_CAMPO_OPORTUNIDAD: str(oportunidad)
            }
            requests.post(URL_FORM_GOOGLE, data=payload, timeout=2)
        except:
            pass # Si falla, no interrumpimos al usuario

def log_interaction(user_text, bot_response):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunity = "NORMAL"
    monto_estimado = 0
    
    # Detección de Montos
    if "$" in bot_response:
        try:
            precios = [int(s.replace('.','')) for s in re.findall(r'\$([\d\.]+)', bot_response) if s.replace('.','').isdigit()]
            if precios:
                monto_estimado = max(precios)
                if monto_estimado > 300000:
                    opportunity = "🔥 ALTA (MAYORISTA)"
        except:
            pass

    # 1. Guardar en Memoria de Sesión (Para ver en Admin Panel ya mismo)
    st.session_state.log_data.append({
        "Fecha": timestamp,
        "Usuario": user_text[:50],
        "Oportunidad": opportunity,
        "Monto Max": monto_estimado
    })
    
    # 2. Enviar a la Nube (Google Forms)
    enviar_a_google_form(user_text, monto_estimado, opportunity)

# --- 7. CEREBRO DE VENTAS (MODO CIERRE AGRESIVO) ---
sys_prompt = f"""
ROL: Eres Lucho, **Experto en Cierre de Ventas** y Asesor Técnico de **Pedro Bravin S.A.**
OBJETIVO PRINCIPAL: No solo informar precios, sino **CONSEGUIR QUE EL CLIENTE HAGA CLIC EN "CONFIRMAR PEDIDO"**.

BASE DE DATOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
DATOS OPERATIVOS:
- DÓLAR BNA: ${DOLAR_BNA_REF}
- ZONA GRATIS: {CIUDADES_GRATIS}

🔥 **TÉCNICAS DE CIERRE OBLIGATORIAS:**
1.  **SENTIDO DE URGENCIA:** Si hay stock, menciona que "se mueve rápido" o "queda poco de este lote".
2.  **PRECIO ANCLA:** Si el total supera $200.000, felicítalo por estar cerca del descuento mayorista o aplícalo si corresponde.
3.  **SIEMPRE TERMINA CON PREGUNTA:** Nunca termines una frase con un punto. Termina invitando a la acción: 
    * "¿Te preparo el link para reservarlo ya?"
    * "¿Te parece bien el presupuesto para avanzar?"
    * "¿Lo confirmamos antes de que cambie el dólar?"

🚨 **REGLA DE PRECIOS (IMPUESTOS):**
* Precios CSV son **NETOS**.
* Salida OBLIGATORIA: "$ [Precio] + IVA".

🧠 **ESTRATEGIA LOGÍSTICA:**
* Si es zona GRATIS -> "¡Estás de suerte! Hoy tenemos logística bonificada a tu zona. Aprovechalo."
* Si no -> Calcula flete nodo cercano y véndelo como "Ahorro por Redireccionamiento".

📝 **FORMATO SALIDA FINAL (IMPORTANTE):**
[TEXTO_WHATSAPP]:
Hola Martín, quiero cerrar este pedido Web.
📍 Destino: [Localidad]
📋 Materiales:
- [Detalle]
💰 Total Aprox: $[Monto] + IVA
✅ Estado: Cliente listo para cerrar.
"""

# --- 8. GESTIÓN DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **¡Hola! Soy Lucho.**\n\nEstoy conectado al stock en tiempo real.\n\n**¿Qué materiales necesitas cotizar para cerrar tu obra hoy?**"}]

if "chat_session" not in st.session_state:
    try:
        # MODELO GEMINI 2.5 O 1.5 PRO
        generation_config = {"temperature": 0.3, "max_output_tokens": 8192} # Temp baja para ser preciso en precios
        model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt, generation_config=generation_config)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception:
        st.error("Error conectando con IA.")

# --- 9. INTERFAZ DE CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: Necesito 10 caños 40x40 para armar un galpón..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("🔍 Lucho está calculando el mejor precio..."):
            response = chat.send_message(prompt)
            full_text = response.text
            
            # REGISTRAR INTERACCIÓN (MÉTRICAS)
            log_interaction(prompt, full_text)
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in full_text:
                dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                
                # DETECCIÓN DE MAYORISTA PARA EFECTO VISUAL
                if "15%" in dialogue or "MAYORISTA" in dialogue:
                    st.balloons()
                    st.toast('🎉 ¡Tarifa Mayorista Aplicada!', icon='📉')
                
                st.markdown(dialogue.strip())
                st.session_state.messages.append({"role": "assistant", "content": dialogue.strip()})
                
                wa_encoded = urllib.parse.quote(wa_part.strip())
                wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                
                # BOTÓN DE CIERRE GIGANTE
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" class="final-action-card">
                    🚀 FINALIZAR PEDIDO AHORA<br>
                    <span style="font-size:0.8rem; font-weight:400;">Enviar detalle a Martín por WhatsApp</span>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")

# --- 10. PANEL DE CONTROL (ADMIN) ---
# Se muestra solo si escribes "admin" en el chat o expandes esto
with st.expander("🔐 Área Privada (Solo Dueños)"):
    st.write("### 📊 Métricas de Sesión Actual")
    if st.session_state.log_data:
        df_log = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df_log)
        
        # Botón descarga
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar Reporte CSV",
            csv,
            "reporte_ventas_lucho.csv",
            "text/csv",
            key='download-csv'
        )
        st.info("💡 Tip: Para tener métricas históricas de todos los días, configura la URL de Google Forms en el código.")
    else:
        st.warning("Aún no hay interacciones en esta sesión.")
