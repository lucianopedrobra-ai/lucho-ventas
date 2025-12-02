import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🧑‍💼", layout="wide")

# Estilos visuales limpios (Móvil First)
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
except Exception as e:
    st.error(f"🚨 Error de configuración de Gemini: {e}")
    st.stop()

# --- 3. CARGA DE DATOS (CATÁLOGO COMPLETO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        df = df.dropna(how='all', axis=1) # Limpieza básica
        return df 
    except Exception:
        return "ERROR_DATA_LOAD_FAILED"

raw_data = load_data()

if isinstance(raw_data, pd.DataFrame):
    # La IA lee TODO el Excel para poder sacar los códigos
    csv_context = raw_data.to_string(index=False)
else:
    csv_context = "ERROR_DATA_LOAD_FAILED"
    st.warning("⚠️ El sistema de precios falló. Modo captura de contacto.")

# --- 4. PROMPT DE VENTA (V95 + CODIFICACIÓN INTERNA) ---
sys_prompt = f"""
ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es obtener el CLICK del cliente en el enlace de WhatsApp para enviar la orden.

BASE DE DATOS Y BÚSQUEDA (STOCK COMPLETO):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------
**INSTRUCCIÓN DE BARRIDO:** Tu prioridad es vender. Revisa EXHAUSTIVAMENTE el listado disponible. Si el producto está en la lista, TIENES que ofrecerlo.

PSICOLOGÍA DE VENTA (BENEFICIOS Y URGENCIA):
* **NO NEGOCIES, OTORGA:** Tú no "bajas precios". Tú "aplicas bonificaciones por volumen" o "destrabas beneficios".
* **GENERAR URGENCIA:** Usa frases sutiles para inducir el cierre AHORA: *"Te recomiendo reservar esto hoy para congelar el precio"*, *"El stock de esto rota muy rápido"*, *"Cerremos la orden para asegurarte la entrega en la próxima salida"*.
* **EL VOLUMEN ES LA LLAVE:** Antes de dar el precio, pregunta la cantidad sugiriendo una oportunidad: *"Decime qué cantidad necesitás, así veo si puedo activarte la tarifa mayorista o algún beneficio de acopio."*

DICCIONARIO TÉCNICO Y LOGICA DE PRODUCTO:
* **PRECIOS E IVA:** Los precios base son NETOS. Multiplica SIEMPRE por 1.21.
* **AISLANTES:** Si es cochera/galería (sol directo/indirecto) y sin cielorraso -> RECOMIENDA **"Isolant Doble Aluminio"**.
* **CHAPAS:** Techo -> Ofrece: Aislante + Tornillos + Perfiles.
* **SIDERÚRGICA:** Perfiles/Tubos -> Ofrece: Electrodos, discos, guantes.

MANEJO DE "NO LISTADO":
Si no está en el CSV, genera un enlace directo: "Ese producto lo valido en depósito. Consultalo acá:" seguido del link markdown: `[👉 Consultar Stock WhatsApp](https://wa.me/5493401648118?text=Busco%20precio%20de%20este%20producto%20no%20listado...)`.

PROTOCOLO DE CIERRE Y LOGÍSTICA (EL EMBUDO):
1. **Validación:** *"¿Cómo lo ves {{Nombre}}? ¿Te preparo la reserva?"*
2. **Logística:** *"¿Preferís retirar o te lo enviamos? (Pasame tu dirección para ver si te bonificamos el envío)."*
3. **OBTENCIÓN DE DATOS:** Pide Nombre, CUIT/DNI y Teléfono.

**FORMATO FINAL OBLIGATORIO (TEXTO OCULTO PARA WHATSAPP):**
Solo cuando el cliente confirma compra y da sus datos, cierra con este bloque exacto.
IMPORTANTE: Para facilitar la facturación al vendedor, debes incluir el **CÓDIGO (ID/SKU)** de cada producto extraído de la tabla CSV.

[TEXTO_WHATSAPP]:
Hola, soy {{Nombre}}. Quiero reservar:
- (COD: [Insertar Codigo CSV]) [Producto] x [Cantidad] 
- (COD: [Insertar Codigo CSV]) [Producto] x [Cantidad]
Total Aprox: $[Total con IVA]
Datos Cliente:
- DNI/CUIT: {{DNI}}
- Tel: {{Teléfono}}
- Entrega: {{Retiro/Envío}}

(No muestres códigos en el chat visible, solo en el bloque [TEXTO_WHATSAPP]).
"""

# --- 5. GESTIÓN DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas tardes. Soy Lucho. ¿Qué proyecto tenés hoy?"}]

if "chat_session" not in st.session_state:
    try:
        # Mantenemos Gemini 2.5 Pro como solicitaste
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")

# --- 6. INTERFAZ GRÁFICA ---
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

# Historial
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "user"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias visuales
if len(st.session_state.messages) == 1:
    st.info("💡 **Tips:** Cotizá 'Techo de chapa 8x4', 'Perfiles C' o 'Malla Romboidal'.")

# --- 7. LÓGICA DE PROCESAMIENTO ---
if prompt := st.chat_input("Escribe tu consulta..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Lucho está calculando..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # PARSEO DEL LINK WHATSAPP
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    dialogue_part, whatsapp_part = full_text.split(WHATSAPP_TAG, 1)
                    
                    st.markdown(dialogue_part.strip())
                    
                    # Generar Link
                    clean_wa_text = whatsapp_part.strip()
                    encoded_text = urllib.parse.quote(clean_wa_text)
                    whatsapp_url = f"https://wa.me/5493401648118?text={encoded_text}"
                    
                    # Botón de Cierre
                    st.markdown(f"""
                    <br>
                    <a href="{whatsapp_url}" target="_blank" style="
                        display: block; width: 100%; background-color: #25D366; color: white;
                        text-align: center; padding: 12px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; font-family: sans-serif; font-size: 1.1em;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                    👉 CONFIRMAR PEDIDO EN WHATSAPP
                    </a>
                    """, unsafe_allow_html=True)
                    
                    history_content = dialogue_part.strip() + f"\n\n[👉 Pedido listo para enviar]({whatsapp_url})"
                else:
                    st.markdown(full_text)
                    history_content = full_text
                
                st.session_state.messages.append({"role": "assistant", "content": history_content})

    except Exception as e:
        st.error(f"Error de comunicación: {e}")
