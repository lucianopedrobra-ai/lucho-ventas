import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Cotizador Pedro Bravin S.A.", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    .whatsapp-btn {
        display: block; width: 100%; 
        background-color: #25D366; color: white !important;
        text-align: center; padding: 15px; border-radius: 10px;
        text-decoration: none; font-weight: bold; font-family: sans-serif;
        font-size: 1.1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .whatsapp-btn:hover {
        background-color: #1ebc57;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN Y CONFIGURACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de configuración: No se encontró la API KEY en los secretos.")
    st.stop()

# --- DEFINICIÓN DEL MODELO ---
# Aquí definimos el modelo que tú indicaste.
# Si en el futuro cambia a 'gemini-3.0', solo cambias esta variable.
MODELO_OBJETIVO = "gemini-2.5-pro" 

# --- BARRA LATERAL (HERRAMIENTA EXPERTA) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/google-logo.png", width=50)
    st.write("### Panel de Control IA")
    
    # Botón para verificar modelos disponibles en tu cuenta
    if st.button("🔍 Verificar Modelos Activos"):
        try:
            st.write("Consultando API de Google...")
            mis_modelos = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    mis_modelos.append(m.name)
            
            st.success(f"Modelos detectados: {len(mis_modelos)}")
            st.code("\n".join(mis_modelos))
            
            # Verificación específica
            if any(MODELO_OBJETIVO in m for m in mis_modelos):
                st.toast(f"✅ ¡{MODELO_OBJETIVO} está disponible y listo!", icon="🚀")
            else:
                st.warning(f"⚠️ No veo '{MODELO_OBJETIVO}' exacto en la lista. Verifica el nombre arriba.")
        except Exception as e:
            st.error(f"Error consultando modelos: {e}")

# --- 3. CARGA DE DATOS (LINK ACTUALIZADO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTUG5PPo2kN1HkP2FY1TNAU9-ehvXqcvE_S9VBnrtQIxS9eVNmnh6Uin_rkvnarDQ/pub?gid=2029869540&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.fillna("")
        return df 
    except Exception as e:
        st.error(f"Error leyendo inventario: {e}")
        return None

raw_data = load_data()

if raw_data is not None and not raw_data.empty:
    try:
        # Usamos to_string para ahorrar tokens si la tabla es gigante, markdown si es pequeña
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: BASE DE DATOS VACÍA."

# --- 4. CEREBRO DE VENTAS (PROMPT ACTUALIZADO PARA GEMINI 2.5) ---
sys_prompt = f"""
ROL: Eres Lucho, el IA Senior de Ventas de **Pedro Bravin S.A.**
MODELO MENTAL: Razonamiento Avanzado (Gemini 2.5). Analiza la intención oculta del cliente antes de responder.

BASE DE DATOS (PRECIOS NETOS - STOCK REAL):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

TUS 3 REGLAS DE ORO:
1.  **VERACIDAD TOTAL:** Solo vendes lo que está en la lista. Si no está, ofrece una alternativa similar que SÍ esté.
2.  **EXPERTO TÉCNICO:**
    - Si piden mallas, calcula la superficie (Mini 7.2m2 vs Maxi 14.4m2) y recomienda la que genere MENOS desperdicio.
    - Si piden perfiles para techo, pregunta la luz (distancia) entre apoyos si no la dijeron.
3.  **CIERRE DE VENTA:** Tu objetivo NO es chatear, es generar un TICKET DE PEDIDO para WhatsApp.

ESTRATEGIA DE PRECIOS:
- Precios de lista son + IVA.
- Compras > $300.000 tienen 15% de Descuento (¡Úsalo para upsell!).
- Siempre ofrece: Clavos y Alambre al cotizar hierros/mallas.

FORMATO DE SALIDA (Cuando el cliente confirma):
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web:
- (COD: [SKU]) [Producto] x [Cant]
Total Estimado: $[Monto]
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, soy Lucho de **Pedro Bravin S.A.** 🏗️\n\nEstoy conectado al inventario en tiempo real. ¿Qué materiales necesitas cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # INTENTO DE CONEXIÓN A GEMINI 2.5
        # Configuramos la generación para ser precisa (temperatura baja)
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        # Intentamos instanciar el modelo solicitado
        model = genai.GenerativeModel(
            model_name=MODELO_OBJETIVO, 
            system_instruction=sys_prompt,
            generation_config=generation_config
        )
        
        # Recuperar historial
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        
        st.session_state.chat_session = model.start_chat(history=initial_history)
        print(f"✅ Conectado exitosamente con {MODELO_OBJETIVO}")

    except Exception as e:
        # FALLBACK INTELIGENTE: Si 2.5 falla (por nombre incorrecto), usamos el más estable disponible
        st.error(f"⚠️ No pude conectar con '{MODELO_OBJETIVO}'. Revisa el nombre en la barra lateral. (Error: {e})")
        st.info("🔄 Intentando conectar con modelo de respaldo (gemini-1.5-pro)...")
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=[])
        except:
            st.error("❌ Error crítico: No hay modelos disponibles.")

# --- 6. CHAT ---
for msg in st.session_state.messages:
    avatar = "👷‍♂️" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Escribe aquí tu consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner(f"⚡ {MODELO_OBJETIVO} analizando stock..."):
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
        st.error(f"Error en la respuesta: {e}")
