import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(
    page_title="Lucho | Pedro Bravin",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ocultar elementos innecesarios de Streamlit para que parezca una App nativa
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {padding-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTENTICACIÓN Y MODELO ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("🚨 Error crítico: Verifica la GOOGLE_API_KEY en secrets.")
    st.stop()

# --- 3. CARGA DE DATOS (CATÁLOGO VIVO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600) # Recarga cada 10 min para mantener precios frescos
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        # Limpieza básica para ahorrar tokens: eliminar columnas vacías si existen
        df = df.dropna(how='all', axis=1) 
        return df 
    except Exception:
        return None

raw_data = load_data()

# Preparación del Contexto (Sin filtros rígidos, dejamos que la IA decida)
if raw_data is not None:
    csv_context = raw_data.to_string(index=False)
    system_status = "ONLINE"
else:
    csv_context = "ERROR: No se pudo cargar la lista de precios. Pide el teléfono al cliente manualmente."
    system_status = "OFFLINE"

# --- 4. CEREBRO DE VENTAS (SYSTEM PROMPT V100 - HIGH TICKET) ---
sys_prompt = f"""
ERES LUCHO. Tu trabajo NO es chatear, es VENDER materiales de construcción (Siderúrgica Pedro Bravin).
Tu métrica de éxito es UNA sola: Que el cliente haga clic en el enlace de WhatsApp.

CONTEXTO DE INVENTARIO (Léelo completo, aquí están los precios):
------------------------------------------------------------
{csv_context}
------------------------------------------------------------

DIRECTRICES DE COMPORTAMIENTO (IMPORTANTE):
1. **FORMATO VISUAL (MÓVIL):** El 90% de tus clientes usan celular.
   - NUNCA uses tablas markdown complejas. Se ven mal en móviles.
   - Usa Listas con viñetas claras.
   - Usa negritas para PRECIOS y TOTALES.

2. **ESTRATEGIA "TICKET ALTO" (INVISIBLE):**
   - Si el cliente pide un producto genérico (ej: "quiero chapa"), asume y cotiza SIEMPRE la opción de MEJOR CALIDAD o MAYOR ESPESOR disponible en la lista primero.
   - Preséntalo como "la opción recomendada para mayor durabilidad". No menciones la opción económica a menos que el cliente se queje del precio.
   - **Precios:** Multiplica siempre el precio de lista por 1.21 (IVA) antes de mostrarlo.

3. **TÉCNICA DE CROSS-SELLING (VENTA CRUZADA OBLIGATORIA):**
   - Si vendes TECHO (Chapa) -> OBLIGATORIO ofrecer: Aislante + Tornillos + Perfiles.
   - Si vendes PERFILES -> OBLIGATORIO ofrecer: Discos de corte + Electrodos + Antiácido.
   - Frase puente: *"Para que te lleves todo listo y no vuelvas, te calculo también los tornillos y aislante?"*

4. **PROTOCOLO DE RESPUESTA:**
   - **Paso 1 (Indagación):** Si faltan medidas, pídelas rápido.
   - **Paso 2 (Cotización):** Da el precio final con IVA.
   - **Paso 3 (Cierre):** *"¿Te reservo el material ahora antes de que cambie el precio?"*
   - **Paso 4 (Datos):** Pide Nombre y Teléfono.

5. **MANEJO DE ERRORES/NO STOCK:**
   - Si el producto NO está en el CSV, NO inventes. Di: *"Esa medida específica la valido en depósito por las dudas."* y genera el link de WhatsApp igual.

6. **GENERACIÓN DE LINK (FINAL DE LA VENTA):**
   - SOLO cuando tengas intención de compra o datos, genera el bloque final exacto.
   - Acepta cualquier formato de teléfono o nombre. No valides estrictamente, queremos el lead.

ESTRUCTURA DE SALIDA PARA CIERRE (Oculta para el usuario, leída por el sistema):
[TEXTO_WHATSAPP]:
Hola Lucho/Pedro, soy {{Nombre}}.
Me interesa reservar:
- [Detalle Productos]
Datos: {{DNI/Tel}}
Envío: {{Si/No}}
"""

# --- 5. GESTIÓN DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy Lucho de Pedro Bravin. 👋\n\n¿Qué materiales estás buscando cotizar hoy? (Chapas, Perfiles, Mallas...)"}
    ]

if "chat_session" not in st.session_state:
    # Usamos gemini-1.5-pro para mayor capacidad de análisis del CSV completo
    model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=sys_prompt)
    st.session_state.chat_session = model.start_chat(history=[])

# --- 6. INTERFAZ DE CHAT ---
st.title("🏗️ Cotizador Pedro Bravin")

# Renderizar mensajes previos
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias visuales (Solo texto, no botones interactivos)
if len(st.session_state.messages) == 1:
    st.caption("Escribe directamente lo que necesitas. Ejemplos: 'Cotizar techo 10x4', 'Precio malla cima', 'Perfiles C'")

# --- 7. LÓGICA DE PROCESAMIENTO ---
if prompt := st.chat_input("Escribe aquí tu consulta..."):
    
    # 1. Guardar y mostrar input usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    # 2. Procesar con Gemini
    try:
        chat = st.session_state.chat_session
        
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Consultando lista de precios..."):
                response = chat.send_message(prompt)
                full_text = response.text
                
                # 3. Lógica de separación de Link de WhatsApp
                WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
                
                if WHATSAPP_TAG in full_text:
                    # Separar el diálogo amigable del payload técnico
                    dialogue_part, whatsapp_payload = full_text.split(WHATSAPP_TAG, 1)
                    
                    # Mostrar la parte conversacional
                    st.markdown(dialogue_part.strip())
                    
                    # Construir la URL
                    clean_payload = whatsapp_payload.strip()
                    encoded_msg = urllib.parse.quote(clean_payload)
                    wa_link = f"https://wa.me/5493401648118?text={encoded_msg}"
                    
                    # Botón de Acción (Call to Action)
                    cta_html = f"""
                    <hr>
                    <a href="{wa_link}" target="_blank" style="
                        display: block;
                        width: 100%;
                        background-color: #25D366;
                        color: white;
                        text-align: center;
                        padding: 12px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: bold;
                        font-family: sans-serif;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    ">
                    👉 ENVIAR PEDIDO AHORA POR WHATSAPP
                    </a>
                    <br>
                    <div style="text-align:center; font-size:0.8em; color:gray;">
                        Al hacer clic se abrirá WhatsApp con el detalle listo.
                    </div>
                    """
                    st.markdown(cta_html, unsafe_allow_html=True)
                    
                    # Guardar en historial (con enlace markdown simple para persistencia)
                    history_text = dialogue_part.strip() + f"\n\n[👉 *Click aquí para retomar el pedido en WhatsApp*]({wa_link})"
                    st.session_state.messages.append({"role": "assistant", "content": history_text})
                    
                else:
                    # Respuesta normal sin cierre de venta aún
                    st.markdown(full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})

    except Exception as e:
        st.error(f"Error de conexión. Intenta de nuevo. ({e})")
