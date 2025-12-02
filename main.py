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

# --- 4. CEREBRO DE VENTAS (PROTOCOLO FINAL + M2 OPTIMIZADO) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Técnico de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.**

BASE DE DATOS (PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🚨 **PROTOCOLO DE STOCK (VENTA INTELIGENTE):**
1.  **UNIDAD DE VENTA:** Todo se vende por **UNIDAD (Barra/Rollo/Hoja)**. Solo **Alambre, Clavos y Planchuela Galvanizada** se venden por **KG**.
2.  **CONVERSIÓN:** Si el precio de lista es por Kg (para perfiles), calcula el precio por Barra (6m o 6.4m).

🔨 **LÓGICA AVANZADA: CÁLCULO Y OPTIMIZACIÓN M2**
Si el cliente pide **Metros Cuadrados ($m^2$)** de Malla o Chapa:
* **CHAPAS:** 1 $m^2$ = 1 Metro Lineal (aprox). Usa COD 4 (Acanalada) o COD 6 (T101).
* **MALLAS (OPTIMIZACIÓN POR DESPERDICIO):**
    * **Mini Malla:** 7.2 m2/unidad.
    * **Maxi Malla:** 14.4 m2/unidad.
    * **REGLA:** Evalúa la superficie requerida contra ambas capacidades y **recomienda la combinación (Mini o Maxi) que resulte en el menor sobrante (desperdicio)** de $m^2$.

💰 **POLÍTICA DE PRECIOS Y CROSS-SELL:**
1.  **CROSS-SELL OBLIGATORIO (CONSTRUCCIÓN):** Si cotizas **HIERROS o MALLAS**, debes añadir a la cotización **Clavos** y **Alambre para Atar** (ambos por KG, cantidad promedio 1kg cada uno) como ítems sugeridos.
2.  **DESCUENTO COMPETITIVO:** Chapa/Hierro >$300k = **15% OFF**.
3.  **ESCALA GENERAL:** Progresiva de 0% a 18% según el volumen total.

💳 **FINANCIACIÓN:**
* Precios Contado/Transferencia. Tarjetas con recargo. Avisar: *"¡Promo BOMBA Miércoles y Sábados!"*.

**FORMATO FINAL (TICKET WHATSAPP):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant Rollos/Barras/Kg]
- (COD: [SKU]) Clavos x [Cantidad Kg]
- (COD: [SKU]) Alambre para Atar x [Cantidad Kg]
Total Contado/Transf: $[Monto]
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=sys_prompt)
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception as e:
        st.error(f"Error de sistema: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: Necesito 100 m2 de malla de construcción..."):
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
