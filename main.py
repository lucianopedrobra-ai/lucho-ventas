import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Cotizador Online", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    /* Avatar Corporativo */
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de conexión. Verifique la API Key.")
    st.stop()

# --- 3. CARGA DE DATOS (BLINDADA) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        # Forzamos la lectura como string para que no se pierdan ceros ni códigos
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1) # Eliminar columnas vacías
        df = df.fillna("") # Rellenar huecos con vacío para no romper el texto
        return df 
    except Exception:
        return None

raw_data = load_data()

# Construcción del Contexto (Formato Texto Plano Claro)
if raw_data is not None and not raw_data.empty:
    # Convertimos el DataFrame a un formato de lista legible para la IA
    csv_context = raw_data.to_markdown(index=False)
else:
    csv_context = "ADVERTENCIA: LA LISTA DE PRECIOS ESTÁ VACÍA O NO CARGÓ. NO INVENTES PRECIOS."

# --- 4. CEREBRO DE VENTAS (MODO ESTRICTO: SOLO LO QUE HAY) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**
OBJETIVO: Vender productos EXCLUSIVAMENTE de nuestro stock.

🛑 **REGLA DE ORO (INSTRUCCIÓN DE SEGURIDAD):**
Tu conocimiento sobre productos se divide en dos fases:
1. **EXISTENCIA Y PRECIO:** ÚNICAMENTE puedes sacar esta información de la "LISTA DE STOCK" de abajo. Si el cliente pide algo que NO figura ahí (ej: ladrillos, cemento), di: *"Disculpá, no trabajamos ese material, pero tengo..."* y ofrece una alternativa de la lista. **NO INVENTES PRECIOS NI STOCK.**
2. **DESCRIPCIÓN TÉCNICA:** Una vez que confirmaste que el producto ESTÁ en la lista, USA tu conocimiento de internet para explicar sus beneficios (ej: si vendes una chapa T101 de la lista, puedes explicar que es resistente al granizo).

LISTA DE STOCK Y PRECIOS BASE (TU ÚNICA VERDAD):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🧠 **TRADUCTOR TÉCNICO (Sinónimos permitidos):**
* "GAS" = Busca en lista: EPOXI / REVESTIDO.
* "AGUA" = Busca en lista: GALVANIZADO / HIDRO3.
* "TECHO" = Busca en lista: CHAPA / T-101 / SINUSOIDAL / CINCALUM.

🔥 **POLÍTICA DE PRECIOS ($$$):**
(El precio de lista es el del CSV. Tu trabajo es calcular el PRECIO FINAL con IVA y Descuento).
Cálculo: (Precio CSV x 1.21). Sobre ese total aplica:
1.  **< $100.000:** 0% OFF (Precio de Lista).
2.  **$100k - $500k:** 5% OFF.
3.  **$500k - $1M:** 8% OFF.
4.  **$1M - $2M:** 12% OFF.
5.  **$2M - $3M:** 15% OFF.
6.  **> $3M:** 18% OFF.

⚠️ **REGLAS DE INTERACCIÓN:**
1.  **PRECIO:** Aclara siempre que es **CONTADO / TRANSFERENCIA**.
2.  **TARJETAS:** "Con tarjeta aplica recargo financiero. ¡Promo Miércoles y Sábados disponible!".
3.  **LOGÍSTICA:** Pregunta siempre: "¿Para qué localidad es?".

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant]
Total Contado/Transf: $[Monto]
*Consulta Financiación: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # Usamos el modelo Flash Lite 2.0 (Rápido y capaz)
        model = genai.GenerativeModel('gemini-2.0-flash-lite-preview-02-05', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except Exception as e:
        # Fallback de seguridad
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=initial_history)
        except:
            st.error(f"Error de conexión: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 5 caños de gas 1 pulgada..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Verificando stock en depósito..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    st.markdown(dialogue.strip())
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                    
                    st.markdown(f"""
                    <br>
                    <a href="{wa_url}" target="_blank" style="
                        display: block; width: 100%; 
                        background-color: #25D366; color: white;
                        text-align: center; padding: 14px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: Arial, sans-serif;
                    ">👉 CONFIRMAR PEDIDO (A Martín)</a>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar Pedido]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
