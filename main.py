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
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gBxIaV7-P7wP4aRNYQIGKaTHxBdOg7iV6cyndtLvKds/export?format=csv"

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
    csv_context = "ERROR: LISTA VACÍA."

# --- 4. CEREBRO DE VENTAS (FINAL) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Técnico de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.**

🚨 **PROTOCOLO 001: VERIFICACIÓN DE INVENTARIO (PRIORIDAD ABSOLUTA):**
1.  **LÍMITE:** Tu inventario es esta lista. No cotices nada que no veas aquí.
2.  **CONVERSIÓN:** Todo se vende por **UNIDAD (Tira/Rollo)**. Si el precio es por Kg, debes calcular el precio de la unidad (Barra) antes de cotizar.

LISTA DE STOCK Y PRECIOS NETOS:
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🛠️ **REGLAS TÉCNICAS Y DE CÁLCULO:**
* **LARGOS:** Caños (Epoxi/Galv): 6.40m. Perfiles/Hierros: 6.00m (o 12m si es Perfil C/IPN grande).
* **TEJIDOS:** Vende por **ROLLO**. Optimiza entre 10m y 15m para menos desperdicio.
* **MEDIDAS:** Respeta la altura exacta. No ofrezcas medidas menores sin avisar.

💰 **POLÍTICA DE DESCUENTOS (0-18%):**
**BASE:** (Precio CSV x 1.21).

**A. REGLA COMPETITIVA (CHAPA Y HIERRO):** >$300.000 = **15% OFF**.

**B. ESCALA GENERAL:** Progresiva de 0% a 18% según el volumen total.

💳 **FINANCIACIÓN:**
* Precios Contado/Transferencia.
* Tarjetas: Tiene recargo. Avisar: *"¡Promo BOMBA Miércoles y Sábados disponible!"*.

**FORMATO FINAL (TICKET WHATSAPP):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant Rollos/Barras]
Total Contado/Transf: $[Monto]
*Consulta Tarjeta/Promo: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
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

if prompt := st.chat_input("Ej: Necesito 40 metros de tejido 1.50..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.spinner("Verificando stock y bonificaciones..."):
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
