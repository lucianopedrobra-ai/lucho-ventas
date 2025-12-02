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
        # Leemos todo como string para proteger la data cruda
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

# --- 4. CEREBRO DE VENTAS (MODO CIERRE) ---
sys_prompt = f"""
ROL: Eres Lucho, el Mejor Vendedor de **Pedro Bravin S.A.**
TU OBJETIVO ÚNICO: **QUE EL CLIENTE HAGA CLIC EN EL BOTÓN DE WHATSAPP**.
ACTITUD: Proactiva, Ejecutiva, Resolutiva. No dudes. Cotiza y cierra.

BASE DE DATOS (PRECIOS NETOS):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

⚡ **PROTOCOLOS DE ACCIÓN RÁPIDA:**

1.  **INTERPRETACIÓN INTELIGENTE (NO PREGUNTES OBVIEDADES):**
    * Si piden "Gas" -> Cotiza **Epoxi**.
    * Si piden "Techo" -> Cotiza **Chapa Cincalum + Perfil C**.
    * Si piden "Cerrar lote" -> Cotiza **Tejido Romboidal**.
    * **Medidas:**
        * Caños (Gas/Agua/Mecánico): Tiras de **6.40m**.
        * Perfiles/Hierros: Tiras de **6.00m**.
        * Tejidos: Vende por **ROLLO**. (Si piden 40m, ofrece 4 rollos de 10m Eco o 3 de 15m Acindar).

2.  **MOTOR DE PRECIOS (MATEMÁTICA INTERNA):**
    * **Paso A:** Busca el precio en lista. Si está en Kg, pásalo a UNIDAD (Barra/Rollo) multiplicando por el peso/largo.
    * **Paso B:** Súmale IVA (**x 1.21**).
    * **Paso C (DESCUENTO):** Aplica la bonificación según el total:
        * **REGLA ORO (Chapa/Hierro):** >$300k = **15% OFF**.
        * **ESCALA COMÚN:** <$100k (0%), $100k-$500k (5%), $500k-$1M (8%), $1M-$2M (12%), $2M-$3M (15%), >$3M (18%).

3.  **EL CIERRE (TU PRIORIDAD):**
    * Una vez que das el precio, **NO TE QUEDES CALLADO**.
    * Genera el link de WhatsApp INMEDIATAMENTE.
    * **Argumento:** *"El precio de lista es $X, pero con la **Bonificación Web** te queda en **$Y Final**. ¿Para qué localidad es? Te preparo el pedido ya."*

💳 **INFO DE PAGO:**
* Precio es **CONTADO/TRANSFERENCIA**.
* Tarjeta: *"Tiene recargo, pero aprovechá la PROMO MIÉRCOLES Y SÁBADOS."*

**FORMATO FINAL OBLIGATORIO (GENERA ESTO SIEMPRE QUE COTICES):**
[TEXTO_WHATSAPP]:
Hola Martín / Equipo Bravin, soy {{Nombre}}.
Pedido Web (Bonif. Aplicada):
- (COD: [SKU]) [Producto] x [Cant]
Total Contado/Transf: $[Monto]
*Consulta Tarjeta/Promo: [SI/NO]*
Logística: {{Localidad}} - {{Retiro/Envío}}
Datos: {{DNI}} - {{Teléfono}}
"""

# --- 5. SESIÓN Y MODELO ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola. Soy Lucho de **Pedro Bravin S.A.** 🏗️\n\nPasame tu lista de materiales y te armo la cotización con descuento ahora mismo."}]

if "chat_session" not in st.session_state:
    try:
        # MODELO: gemini-2.0-flash (Velocidad + Razonamiento)
        # Si prefieres más "cerebro" y menos velocidad, cambia a 'gemini-1.5-pro'
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

if prompt := st.chat_input("Ej: 5 caños de gas 1 pulgada..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Cotizando y aplicando descuentos..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                if WHATSAPP_TAG in full_text:
                    dialogue, wa_part = full_text.split(WHATSAPP_TAG, 1)
                    st.markdown(dialogue.strip())
                    
                    wa_encoded = urllib.parse.quote(wa_part.strip())
                    
                    # DESTINO: MARTÍN (3401 52-7780)
                    wa_url = f"https://wa.me/5493401527780?text={wa_encoded}"
                    
                    # BOTÓN DE CIERRE AGRESIVO
                    st.markdown(f"""
                    <br>
                    <a href="{wa_url}" target="_blank" style="
                        display: block; width: 100%; 
                        background-color: #25D366; color: white;
                        text-align: center; padding: 14px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: Arial, sans-serif;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                        font-size: 1.1em;
                    ">👉 CONFIRMAR PEDIDO (Enviar a Martín)</a>
                    <div style="text-align:center; font-size:0.8em; color:gray; margin-top:5px;">
                        Hacé clic para reservar el stock y congelar el precio.
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": dialogue.strip() + f"\n\n[👉 Confirmar Pedido]({wa_url})"})
                else:
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
    except Exception as e:
        st.error(f"Error: {e}")
