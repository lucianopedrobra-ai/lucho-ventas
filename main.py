import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA (Móvil First) ---
st.set_page_config(
    page_title="Lucho | Pedro Bravin S.A.",
    page_icon="🧑‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS para limpiar la interfaz y hacerla parecer una App nativa
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {padding-bottom: 20px;}
    .stChatMessage .stChatMessageAvatar {
        background-color: #f0f2f6; /* Fondo suave para el avatar */
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

# --- 3. CARGA DE DATOS (CATÁLOGO COMPLETO - SIN FILTROS RECORTADOS) ---
# Dejamos que la IA vea TODO para que pueda ofrecer Ferretería junto con Siderurgia
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        df = df.dropna(how='all', axis=1) 
        return df 
    except Exception:
        return None

raw_data = load_data()

if raw_data is not None:
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: El sistema de precios no cargó. Pide datos de contacto manualmente."

# --- 4. CEREBRO DE VENTAS (FUSIÓN: IDENTIDAD BRAVIN + REGLAS V95) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Senior de **PEDRO BRAVIN S.A.**
NEGOCIO: Somos Comercializadora de Siderurgia y Ferretería Industrial. (NO somos fábrica, somos distribuidores con stock).

BASE DE DATOS (TU STOCK):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

LINEAMIENTOS DE TRABAJO (TU PROTOCOLO OBLIGATORIO):

1. **BARRIDO DE STOCK E INTELIGENCIA:**
   - Tu prioridad es vender. Revisa exhaustivamente la lista.
   - Si no está en lista, di: *"Lo valido en depósito"* (No digas "no hay" de entrada).

2. **PSICOLOGÍA DE PRECIOS (REGLA DE ORO):**
   - **PRECIOS NETOS EN CSV:** Debes multiplicar SIEMPRE por **1.21** antes de dar el precio.
   - **TICKET ALTO:** Si piden "chapa", cotiza primero la de MAYOR CALIDAD/ESPESOR. Solo baja si el cliente lo pide.

3. **CROSS-SELLING (LA MAGIA DE LA FERRETERÍA):**
   - Vendes Chapa/Techo -> **OFRECE:** Aislante + Tornillos + Cumbreras.
   - Vendes Perfiles/Hierro -> **OFRECE:** Discos de corte, Electrodos, Guantes, Pintura.
   - *Frase:* "Para que te lleves todo listo y no vuelvas, ¿te agrego los insumos?"

4. **MANEJO DE PRODUCTOS TÉCNICOS:**
   - **Aislantes:** Si es cochera/galería sin cielorraso, recomienda **Doble Aluminio** por el sol.
   - **Chapas:** Si lleva color Cincalum, ofrece la lisa correspondiente (Cod 10).

5. **CIERRE Y DATOS:**
   - Genera urgencia: *"Cerremos la orden para asegurarte la entrega en la próxima salida"*.
   - OBJETIVO: Conseguir Nombre, Teléfono y CLICK en el enlace.

FORMATO FINAL OBLIGATORIO (SOLO AL CERRAR):
[TEXTO_WHATSAPP]:
Hola Equipo Bravin, soy {{Nombre}}.
Quiero reservar:
- [Lista detallada]
Datos: {{DNI/Tel}}
Entrega: {{Retiro/Envío}}
"""

# --- 5. GESTIÓN DE SESIÓN (Lógica V95 + Modelo 2.5) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy Lucho de **Pedro Bravin S.A.** 🏗️\n\n¿Qué proyecto tenés hoy? (Techos, Cercos, Estructuras...)"}
    ]

# Control de sugerencias iniciales (Solo una vez)
if "suggestions_shown" not in st.session_state:
    st.session_state.suggestions_shown = False

if "chat_session" not in st.session_state:
    try:
        # Usamos Gemini 2.5 como solicitaste para máximo razonamiento
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"⚠️ Error conectando al cerebro 2.5: {e}")
        st.stop()

# --- 6. INTERFAZ GRÁFICA ---
st.title("🏗️ Lucho | Pedro Bravin")

# Renderizar Historial
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias (Estilo visual simple)
if len(st.session_state.messages) == 1 and not st.session_state.suggestions_shown:
    st.info("💡 **Tips:** Probá buscando 'Materiales para techo 10x5' o 'Perfiles y discos de corte'.")
    st.session_state.suggestions_shown = True

# --- 7. PROCESAMIENTO INTELIGENTE ---
if prompt := st.chat_input("Escribe tu consulta..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Lucho está calculando precios y stock..."):
                # ENVIAMOS EL PROMPT DIRECTO (La IA filtra internamente mejor que Python)
                response = chat.send_message(prompt)
                full_text = response.text
                
                # PARSEO DEL LINK DE WHATSAPP
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    dialogue_part, whatsapp_part = full_text.split(WHATSAPP_TAG, 1)
                    
                    # 1. Mostrar texto del chat
                    st.markdown(dialogue_part.strip())
                    
                    # 2. Generar Link
                    clean_wa_text = whatsapp_part.strip()
                    encoded_text = urllib.parse.quote(clean_wa_text)
                    whatsapp_url = f"https://wa.me/5493401648118?text={encoded_text}"
                    
                    # 3. BOTÓN GRANDE (Mejor que el link de texto del código viejo)
                    cta_html = f"""
                    <br>
                    <a href="{whatsapp_url}" target="_blank" style="
                        display: block; width: 100%; background-color: #25D366; color: white;
                        text-align: center; padding: 12px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: sans-serif; font-size: 1.1em;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                    👉 CONFIRMAR PEDIDO EN WHATSAPP
                    </a>
                    """
                    st.markdown(cta_html, unsafe_allow_html=True)
                    
                    # Guardar en historial
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": dialogue_part.strip() + f"\n\n[👉 Confirmar Pedido en WhatsApp]({whatsapp_url})"
                    })
                else:
                    # Respuesta normal
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})

    except Exception as e:
        st.error(f"Error de comunicación: {e}")
