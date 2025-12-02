import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(
    page_title="Lucho | Pedro Bravin",
    page_icon="🧑‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS para optimización móvil y limpieza visual
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {padding-bottom: 20px;}
    /* Ajuste para que el avatar se vea bien */
    .stChatMessage .stChatMessageAvatar {
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("🚨 Error crítico: Verifica la GOOGLE_API_KEY en secrets.")
    st.stop()

# --- 3. CARGA DE DATOS (SIN FILTROS, TODO EL CONTEXTO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        df = df.dropna(how='all', axis=1) # Limpieza ligera
        return df 
    except Exception:
        return None

raw_data = load_data()

# Preparación del Contexto
if raw_data is not None:
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: No se pudo cargar la lista. Pide el teléfono manualmente."

# --- 4. CEREBRO DE VENTAS (PROMPT EXPERTO) ---
sys_prompt = f"""
ERES LUCHO. Ejecutivo Comercial de Pedro Bravin (Siderúrgica).
TU OBJETIVO: Cerrar la venta y conseguir el CLICK en WhatsApp.

BASE DE DATOS DE PRECIOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

COMPORTAMIENTO OBLIGATORIO:
1. **EXPERTO EN MÓVIL:** No uses tablas complejas. Usa listas simples y precios en negrita.
2. **PSICOLOGÍA DE TICKET ALTO:**
   - Si piden "chapa", cotiza la de MAYOR espesor primero (la más cara).
   - Si piden "aislante", ofrece el doble aluminio.
   - Solo baja la calidad si el cliente objeta el precio.
3. **CROSS-SELLING AGRESIVO PERO AMABLE:**
   - Nunca vendas un producto solo. "Te agrego los tornillos?", "Te calculo los perfiles?".
4. **CIERRE DE VENTA:**
   - No des precios sueltos sin preguntar: "¿Te lo reservo?", "¿Qué cantidad necesitas?".
   - SIEMPRE PRECIOS CON IVA INCLUIDO (x 1.21).

FORMATO FINAL PARA EL LINK (OCULTO):
[TEXTO_WHATSAPP]:
Hola Lucho, soy {{Nombre}}. Reservame:
- [Items]
Datos: {{DNI/Tel}}
"""

# --- 5. GESTIÓN DE SESIÓN Y MODELO (TU CONFIGURACIÓN) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy Lucho. 🧑‍💼\nEstoy listo para cotizar tu proyecto. ¿Qué materiales necesitas?"}
    ]

if "chat_session" not in st.session_state:
    try:
        # CONFIGURACIÓN SOLICITADA: GEMINI 2.5 PRO
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        # Reconstrucción del historial como solicitaste
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        # Fallback silencioso o reporte de error si la API falla
        st.error(f"⚠️ Error conectando con el modelo 2.5: {e}")
        st.stop()

# --- 6. INTERFAZ ---
st.title("🏗️ Lucho | Pedro Bravin")

# Mostrar Mensajes
for msg in st.session_state.messages:
    # Icono personalizado para Lucho
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias (Texto estático, NO botones, como pediste)
if len(st.session_state.messages) == 1:
    st.markdown("""
    <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; color: #666; font-size: 0.9em; margin-bottom: 10px;">
    💡 <b>Sugerencias:</b> Probá pidiendo <i>"Cotizar techo de 50m2"</i>, <i>"Precio de malla cima"</i> o <i>"Perfiles para galería"</i>.
    </div>
    """, unsafe_allow_html=True)

# --- 7. INPUT Y PROCESAMIENTO ---
if prompt := st.chat_input("Escribe tu consulta..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Lucho está calculando..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Extracción del Link de WhatsApp
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_data = full_text.split(WHATSAPP_TAG, 1)
                    
                    st.markdown(dialogue.strip())
                    
                    # Generar Link
                    encoded_msg = urllib.parse.quote(wa_data.strip())
                    wa_link = f"https://wa.me/5493401648118?text={encoded_msg}"
                    
                    # Botón GRANDE para celular
                    st.markdown(f"""
                    <a href="{wa_link}" target="_blank" style="
                        display: block; width: 100%; background-color: #25D366; color: white;
                        text-align: center; padding: 15px; border-radius: 10px;
                        text-decoration: none; font-weight: bold; font-size: 1.1em;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 10px;">
                        👉 CONFIRMAR PEDIDO EN WHATSAPP
                    </a>
                    """, unsafe_allow_html=True)
                    
                    history_text = dialogue.strip() + f"\n\n[Link generado: Pedido listo]"
                else:
                    st.markdown(full_text)
                    history_text = full_text

                st.session_state.messages.append({"role": "assistant", "content": history_text})

    except Exception as e:
        st.error(f"Error de red/modelo: {e}")
