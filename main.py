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
    .stChatMessage .stChatMessageAvatar {background-color: #003366; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Error de conexión.")
    st.stop()

# --- 3. CARGA DE DATOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        # Leemos todo como string para proteger códigos y evitar formateo automático
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip', dtype=str)
        df = df.dropna(how='all', axis=1)
        df = df.fillna("")
        return df 
    except Exception:
        return None

raw_data = load_data()

# Contexto de Precios
if raw_data is not None and not raw_data.empty:
    try:
        csv_context = raw_data.to_markdown(index=False)
    except ImportError:
        csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR: LISTA VACÍA."

# --- 4. CEREBRO DE VENTAS (CON REGLA DE M2 PARA TECHOS) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Técnico de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.**

BASE DE DATOS (STOCK Y PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🏠 **REGLA TÉCNICA: CHAPAS DE TECHO (POR M2 vs LINEAL):**
El precio de lista suele ser por METRO LINEAL.
Si el cliente pide **METROS CUADRADOS (m2)** y no da medidas de corte:
1.  **Conversión:** Asume que **1 m2 = 1 Metro Lineal** (Ancho útil estandar 1m).
2.  **SELECCIÓN DE CÓDIGO (IMPORTANTE):**
    * Si pide **CINCALUM ACANALADA** (Común): Usa el precio del **CÓDIGO 4**.
    * Si pide **CINCALUM T-101** (Trapezoidal): Usa el precio del **CÓDIGO 6**.
    * Si pide **COLOR**: Busca el precio por metro del color en lista.

📏 **REGLA DE LARGOS (PERFILES):**
1.  **6.40m:** Epoxi, Galvanizado, Schedule, Mecánico.
2.  **6.00m:** Ángulos, Planchuelas, Hierros, Estructurales.
*(Cálculo de precio hierros: Precio Kg x Peso x Largo x 1.21)*.

💰 **POLÍTICA DE PRECIOS ($$$):**
**BASE:** (Precio CSV x 1.21).

**A. REGLA COMPETITIVA (CHAPA Y HIERRO):**
* > $300.000: **15% OFF DIRECTO**.
* > $3.000.000: **18% OFF**.

**B. ESCALA GENERAL (RESTO):**
1. < $100k: **0%**.
2. $100k - $500k: **5%**.
3. $500k - $1M: **8%**.
4. $1M - $2M: **12%**.
5. $2M - $3M: **15%**.
6. > $3M: **18%**.

💳 **FINANCIACIÓN:**
* Precios con descuento son **CONTADO/TRANSFERENCIA**.
* **Tarjeta:** Tiene recargo. *"¡Promo BOMBA Miércoles y Sábados disponible!"*.

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant/Metros]
Total Contado/Transf: $[Monto Final]
*Consulta Tarjeta/Promo: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # MODELO: gemini-2.0-flash (Inteligente y Rápido)
        # Si da error, volver a gemini-1.5-pro
        model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except Exception as e:
        st.error(f"Error de sistema: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 100 m2 de chapa acanalada cincalum..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Calculando m2 y descuentos..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    st.markdown(dialogue.strip())
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    
                    # DESTINO: MARTÍN
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
