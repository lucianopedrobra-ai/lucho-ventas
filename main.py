import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL (MARCA BLANCA) ---
st.set_page_config(page_title="Cotizador Online", page_icon="🏗️", layout="wide")

# CSS para ocultar marcas de Streamlit y dar look profesional
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    st.error("🚨 Error: Falta la API Key en los Secrets.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Error de configuración: {e}")
    st.stop()

# --- 3. CARGA DE DATOS (SIN FILTROS - CONTEXTO TOTAL) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        df = df.dropna(how='all', axis=1) # Limpieza básica
        return df 
    except Exception:
        return None

raw_data = load_data()

# Aquí está la clave: NO filtramos. Convertimos TODO el Excel a texto para la IA.
if isinstance(raw_data, pd.DataFrame):
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: No se pudo cargar la lista de precios."
    st.warning("⚠️ El sistema funciona en modo manual (sin precios).")

# --- 4. CEREBRO COMERCIAL (PROMPT V95 + BONIFICACIÓN) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Senior de **Pedro Bravin S.A.**
TONO: Profesional, Expeditivo, Astuto.
OBJETIVO: Cerrar la venta obteniendo el clic en WhatsApp.

BASE DE DATOS (CATÁLOGO COMPLETO):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

REGLAS DE NEGOCIO OBLIGATORIAS:

1.  **MATEMÁTICA DEL PRECIO (LA BONIFICACIÓN):**
    * Los precios del CSV son NETOS.
    * **Cálculo Real:** Precio CSV x 1.21.
    * **Narrativa:** NO des el precio "seco". Presentalo así: *"El precio de lista es más alto, pero te aplico la **Bonificación Web** y te queda en $[Precio Calculado] final."*

2.  **LOGÍSTICA (EL CIERRE):**
    * Nunca termines una cotización sin resolver la entrega.
    * Pregunta: *"¿Para qué localidad es? Así veo si te puedo bonificar el envío con el reparto de la zona."*

3.  **CROSS-SELLING (FERRETERÍA):**
    * Como tienes toda la lista, ofrece complementos lógicos.
    * Si llevan Perfiles -> Ofrece Discos y Electrodos.
    * Si llevan Techo -> Ofrece Aislante y Tornillos.

4.  **FORMATO DE SALIDA (WHATSAPP):**
    * Solo cuando el cliente confirme, genera el bloque oculto.
    * **IMPORTANTE:** Incluye el CÓDIGO (SKU) que figura en el CSV para facilitar la facturación.

[TEXTO_WHATSAPP]:
Hola Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonificado):
- (COD: [SKU]) [Producto] x [Cant]
Total Final: $[Monto]
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. INICIALIZACIÓN DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, soy Lucho de **Pedro Bravin**. 🏗️\n\n¿Qué materiales estás buscando hoy? Te calculo el mejor precio."}]

if "chat_session" not in st.session_state:
    try:
        # Usamos el modelo solicitado. Si da error 404 es porque tu cuenta no tiene acceso a la beta 2.5 aún.
        # Si falla, cámbialo a 'gemini-1.5-pro' que es igual de potente.
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"Error al iniciar Lucho: {e}")

# --- 6. INTERFAZ GRÁFICA ---
# Renderizar chat previo
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# --- 7. PROCESAMIENTO ---
if prompt := st.chat_input("Escribe tu consulta..."):
    # Guardar input usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Consultando stock y bonificaciones..."):
                # Enviamos el prompt directo. La IA ya tiene el CSV en su memoria (system_instruction)
                response = chat.send_message(prompt)
                full_text = response.text
                
                # Detectar Bloque WhatsApp
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    dialogue_part, whatsapp_part = full_text.split(WHATSAPP_TAG, 1)
                    
                    # Mostrar respuesta verbal
                    st.markdown(dialogue_part.strip())
                    
                    # Crear Link
                    wa_encoded = urllib.parse.quote(whatsapp_part.strip())
                    wa_url = f"https://wa.me/5493401648118?text={wa_encoded}"
                    
                    # Botón CTA Profesional
                    st.markdown(f"""
                    <br>
                    <a href="{wa_url}" target="_blank" style="
                        display: block; width: 100%; 
                        background-color: #25D366; color: white;
                        text-align: center; padding: 12px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: sans-serif;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">👉 CONFIRMAR PEDIDO BONIFICADO</a>
                    """, unsafe_allow_html=True)
                    
                    # Guardar en historial
                    st.session_state.messages.append({"role": "assistant", "content": dialogue_part.strip() + f"\n\n[👉 Confirmar Pedido]({wa_url})"})
                else:
                    # Respuesta normal
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})

    except Exception as e:
        st.error(f"Error de comunicación: {e}")
