import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA (LIMPIA Y RÁPIDA) ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🧑‍💼", layout="wide")

# CSS para ocultar elementos innecesarios y centrar la atención en el chat
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {padding-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    st.error("🚨 Error: Falta la API Key 'GOOGLE_API_KEY' en los Secrets.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Error de configuración: {e}")
    st.stop()

# --- 3. CARGA DE DATOS (CONTEXTO COMPLETO - SIN FILTROS) ---
# Aquí está el cambio clave: NO filtramos con Python. Le damos todo a la IA.
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        # Limpieza técnica básica (eliminar columnas vacías fantasma)
        df = df.dropna(how='all', axis=1)
        return df 
    except Exception:
        return None

raw_data = load_data()

# Preparamos el contexto. Si falla, modo error. Si funciona, modo IA Completa.
if isinstance(raw_data, pd.DataFrame):
    # Convertimos TODO el Excel a texto para que la IA lo lea
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: No se pudo cargar la lista de precios. Pide el teléfono y nombre manualmente."

# --- 4. CEREBRO DE VENTAS (TUS REGLAS + MAGIA IA) ---
sys_prompt = f"""
ROL Y PERSONALIDAD: 
Eres Lucho, Ejecutivo Comercial Senior de Pedro Bravin.
Tu tono es: **EJECUTIVO, RÁPIDO Y CÓMPLICE.**
Menos "Hola, ¿en qué puedo ayudarle?" y más "¿Qué tal? ¿Qué material estás buscando hoy?".
Tu objetivo NO es conversar, es **CERRAR LA RESERVA** para que hagan click en WhatsApp.

BASE DE DATOS (STOCK TOTAL):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

TUS REGLAS DE ORO (INNEGOCIABLES):

1. **BARRIDO DE INVENTARIO:**
   - Tienes acceso a TODA la lista arriba. Úsala.
   - Si el producto está, véndelo. Si no está, ofrece una alternativa o di "Lo valido en depósito".

2. **PSICOLOGÍA DE VENTA (PRECIOS Y URGENCIA):**
   - **IVA:** Los precios de la lista son NETOS. **SIEMPRE multiplica por 1.21** antes de darlos.
   - **NO NEGOCIES, OTORGA:** Si piden descuento, di: *"Por esa cantidad te puedo activar precio de acopio si cerramos hoy"*.
   - **TICKET ALTO:** Si piden "chapa", cotiza primero la de MAYOR espesor. Si piden "aislante", ofrece el Doble Aluminio. Solo baja si se quejan.

3. **CROSS-SELLING (EL COMBO):**
   - **Techo:** Ofrece Aislante + Tornillos + Perfiles.
   - **Perfiles/Hierro:** Ofrece Discos de corte, Electrodos, Pintura.
   - *Frase:* "Para que no vuelvas dos veces, ¿te agrego los tornillos y discos?"

4. **PROTOCOLO DE CIERRE RÁPIDO:**
   - No des vueltas. Da el precio y pregunta: *"¿Te lo separo?"* o *"¿Qué cantidad necesitas?"*.
   - Pasos: Validar Stock -> Dar Precio con IVA -> Pedir Datos (Nombre/Tel) -> Generar Link.

FORMATO FINAL OBLIGATORIO (TEXTO OCULTO):
Solo cuando tengas los datos, genera este bloque exacto al final:
[TEXTO_WHATSAPP]:
Hola Lucho. Quiero reservar:
- [Lista de Productos]
Datos Cliente:
- Nombre: {{Nombre}}
- DNI/CUIT: {{DNI}}
- Tel: {{Teléfono}}
- Entrega: {{Retiro/Envío}}
"""

# --- 5. GESTIÓN DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola. Soy Lucho. 🧑‍💼\n¿Qué materiales necesitas cotizar? Voy directo al grano."}
    ]

if "chat_session" not in st.session_state:
    try:
        # Usamos 1.5 Pro porque 2.5 da error 404, pero 1.5 Pro es igual de inteligente para esto.
        model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error de sistema: {e}")

# --- 6. INTERFAZ VISUAL ---
st.title("🏗️ Lucho | Pedro Bravin")

# Historial
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias visuales (sin botones, solo texto para educar al cliente)
if len(st.session_state.messages) == 1:
    st.info("💡 **Tips:** Probá buscando 'Techo completo 40m2', 'Malla cima' o 'Perfiles y discos'.")

# --- 7. PROCESAMIENTO ---
if prompt := st.chat_input("Escribe tu consulta..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Calculando..."):
                # ENVIAMOS EL PROMPT DIRECTO (Sin filtros de Python, la IA hace todo)
                response = chat.send_message(prompt)
                full_text = response.text
                
                # PARSEO DEL LINK
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    dialogue_part, whatsapp_part = full_text.split(WHATSAPP_TAG, 1)
                    
                    st.markdown(dialogue_part.strip())
                    
                    # Generar Link
                    clean_wa_text = whatsapp_part.strip()
                    encoded_text = urllib.parse.quote(clean_wa_text)
                    whatsapp_url = f"https://wa.me/5493401648118?text={encoded_text}"
                    
                    # BOTÓN DE CIERRE (GRANDE Y CLARO)
                    st.markdown(f"""
                    <br>
                    <a href="{whatsapp_url}" target="_blank" style="
                        display: block; width: 100%; background-color: #25D366; color: white;
                        text-align: center; padding: 12px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: sans-serif; font-size: 1.1em;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                    👉 FINALIZAR PEDIDO EN WHATSAPP
                    </a>
                    """, unsafe_allow_html=True)
                    
                    history_content = dialogue_part.strip() + f"\n\n[👉 Finalizar en WhatsApp]({whatsapp_url})"
                else:
                    st.markdown(full_text)
                    history_content = full_text
                    
                st.session_state.messages.append({"role": "assistant", "content": history_content})

    except Exception as e:
        st.error(f"Error de conexión: {e}")
