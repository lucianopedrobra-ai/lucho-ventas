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

# --- 3. CARGA DE DATOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        # Leemos todo como string para proteger códigos y medidas
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

# --- 4. CEREBRO DE VENTAS (V. ACTUALIZADA CON LARGOS 12M Y TARJETAS) ---
sys_prompt = f"""
ROL: Eres Lucho, Ejecutivo Comercial Técnico de **Pedro Bravin S.A.**
TONO: **PROFESIONAL, TÉCNICO Y CONCISO.**
ESTRATEGIA: Genera una **mini urgencia** sutil para cerrar (ej: "tengo stock ahora", "antes de cambio de lista").

BASE DE DATOS (STOCK Y PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

🛠️ **REGLAS DE COTIZACIÓN (INTELIGENCIA DE PRODUCTO):**

1.  **CHAPAS TECHO:**
    * **Conversión:** Si piden $m^2$, asume 1 $m^2$ = 1 Metro Lineal.
    * **ACANALADA** = Busca precio COD 4.
    * **T101** = Busca precio COD 6.
    * **COLOR** = El precio en lista es por **METRO LINEAL**. Cotiza directo.

2.  **HIERROS/PERFILES (Calculadora de Precio por Barra):**
    * Fórmula: `Precio Kg Lista` * `Peso Barra` * `1.21`.
    * **REGLA DE LARGOS (¡MUY IMPORTANTE!):**
        * **12.00 Metros:** Perfil C (Negro/Galv) y Perfiles IPN/UPN mayores a 80mm.
        * **6.40 Metros:** Caños Epoxi (Gas), Galvanizados (Agua), Schedule.
        * **6.00 Metros:** Ángulos, Hierros construcción, Planchuelas, IPN/UPN chicos (<80mm).

3.  **TEJIDOS:**
    * Cotiza por **ROLLO CERRADO**.
    * Optimiza cortes (Eco 10m vs Acindar 15m) para reducir desperdicio.

💰 **POLÍTICA DE PRECIOS ($$$):**
**BASE:** (Precio CSV x 1.21).

**A. REGLA ORO (CHAPA Y HIERRO):**
* > $300.000 = **15% OFF DIRECTO**.
* > $3.000.000 = **18% OFF**.

**B. ESCALA GENERAL (RESTO):**
1. < $100k: **0%**.
2. $100k - $500k: **5%**.
3. $500k - $1M: **8%**.
4. $1M - $2M: **12%**.
5. $2M - $3M: **15%**.
6. > $3M: **18%**.

💳 **FINANCIACIÓN (COSTOS REALES):**
* Los precios con descuento son **CONTADO/TRANSFERENCIA**.
* **TARJETAS (Recargos sobre precio de lista):**
    * **Visa/Master:** 3 cuotas (+7.5%) | 6 cuotas (+14%).
    * **Amex:** 3 cuotas (+14%) | 6 cuotas (+25%).
* **PROMO:** *"¡Recordá que Miércoles y Sábados tenemos **PROMO BOMBA**!"* (Menciónala siempre).

**FORMATO FINAL (SOLO AL CONFIRMAR):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant]
Total Contado/Transf: $[Monto Final]
*Financiación: [Detalle si aplica]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho, Ejecutivo Comercial de **Pedro Bravin S.A.**\n\n¿Qué materiales necesitás cotizar hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # MODELO: gemini-2.0-flash (Inteligente y Rápido)
        model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
        
        st.session_state.chat_session = model.start_chat(history=initial_history)
    except Exception as e:
        # Fallback de seguridad
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
            st.session_state.chat_session = model.start_chat(history=initial_history)
        except:
            st.error(f"Error de conexión: {e}")

# --- 6. INTERFAZ ---
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

if prompt := st.chat_input("Ej: 10 Perfiles C 100..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Verificando stock y financiación..."):
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
