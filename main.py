import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🏗️", layout="centered")

# 1. AUTENTICACIÓN
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    st.error("🚨 Error: Falta la API Key 'GOOGLE_API_KEY' en los Secrets de Streamlit.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Error de configuración de Gemini: {e}")
    st.stop()

# 2. CARGA DE DATOS
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    """Carga los datos desde la URL de la hoja de cálculo y los convierte a string."""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg:
            st.error(
                f"🚨 Error 404 (Not Found) al cargar datos: El link en SHEET_URL es incorrecto o la hoja no está publicada como CSV."
            )
        else:
            st.error(f"Error inesperado leyendo la lista de productos: {e}")
        # Retorna una cadena de error que será detectada por el prompt
        return "ERROR_DATA_LOAD_FAILED"

csv_context = load_data()

# 3. EL CEREBRO (PROMPT V72 - Limpio de etiquetas internas)

# --- Lógica Condicional del ROL (Mejora de Robustez) ---
data_failure = "ERROR" in csv_context

if data_failure:
    rol_persona = "ROL CRÍTICO: Eres Lucho, Ejecutivo Comercial Senior. Tu base de datos falló. NO DEBES COTIZAR NINGÚN PRECIO. Tu única función es disculparte por la 'falla temporal en el sistema de precios', tomar el Nombre, Localidad, CUIT/DNI y Teléfono del cliente, e informar que Martín Zimaro (3401 52-7780) le llamará de inmediato. IGNORA todas las reglas de cotización y enfócate en la derivación."
    base_data = "BASE DE DATOS: [Datos no disponibles por falla crítica]"
    # ESTRATEGIA INTERNA LIMPIA: Solo la acción de captura
    reglas_cotizacion = "REGLAS DE INTERACCIÓN: 1. Saludo. 2. Disculpas y derivación. 3. Captura el Nombre, Localidad, CUIT/DNI y Teléfono del cliente. 4. Cierre inmediato con datos de Martín Zimaro."
else:
    rol_persona = "ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es cotizar rápido y derivar al humano."
    base_data = f"BASE DE DATOS DE PRECIOS: {csv_context}"
    # ESTRATEGIA INTERNA LIMPIA: Eliminación de etiquetas como CANDADO DE DATOS y PRE-COTIZACIÓN.
    reglas_cotizacion = """REGLAS DE INTERACCIÓN:
1. Saludo: Inicia con "Hola, buenas tardes."
2. Proactividad: Pregunta "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. Antes de dar el precio final, pregunta: "Para confirmarte si tenés Envío Gratis, decime: ¿Tu Nombre y de qué Localidad sos?"
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".
5. Si el cliente se detiene o no responde a tu último mensaje, debes ser proactivo. Después de un turno sin respuesta (conceptual 20 segundos), realiza un FOLLOW-UP: "¿Te ayudo con algún otro producto para optimizar el envío?". Si el silencio persiste (conceptual 60 segundos), CIERRA la conversación cortésmente con la frase: "Perfecto. Quedo atento a tu CUIT/DNI y Teléfono para avanzar con la reserva. ¡Que tengas un excelente día!""""

sys_prompt = f"""
{rol_persona}
UBICACIÓN DE RETIRO: El Trébol, Santa Fe. (Asume que el punto de retiro es central en esta localidad).
{base_data}

{reglas_cotizacion}

**REGLA DE FORMATO: NUNCA uses etiquetas internas (como 'Follow-Up:', 'Cross-Sell:', 'Ticket:', 'Lógica:'). Usa solo diálogo natural y el formato TICKET.**

DICCIONARIO TÉCNICO Y MATEMÁTICA:
* IVA: Precios en la BASE DE DATOS son NETOS. MULTIPLICA SIEMPRE POR 1.21.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x 6.40m) | Estructural (x 6.00m).
* PLANCHUELAS: Precio por UNIDAD (Barra).

PROTOCOLO DE VENTA POR RUBRO:
* TEJIDOS: No uses "Kit". Cotiza item por item: 1. Tejido, 2. Alambre Tensión, 3. Planchuelas, 4. Accesorios.
* CHAPAS: Filtro Techo vs Lisa. Aislación consultiva. Estructura. (Solo pide el largo exacto para cotizar cortes a medida).
* REJA/CONSTRUCCIÓN: Cotiza material. Muestra diagrama ASCII si es reja.
* NO LISTADOS: Si no está en BASE DE DATOS, fuerza handoff: "Consulto stock en depósito".

MATRIZ DE NEGOCIACIÓN, FINANCIACIÓN Y LOGÍSTICA:
* ENVÍO SIN CARGO (ZONA): El Trébol, María Susana, Piamonte, Landeta, San Jorge, Sastre, C. Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
* DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% General) | >$2M (14%).
* MEGA-VOLUMEN (> $10M): Muestra Ticket BASE. Deriva a Martín Zimaro (3401 52-7780).
* FINANCIACIÓN: Transferencia/MP. Local: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado: "+3% EXTRA".

FORMATO Y CIERRE:
* TICKET (DESGLOSE REAL): Usa bloques de código ```text. Lista cada producto por separado con su CÓDIGO y PRECIO UNITARIO real (del CSV). Nunca agrupes.
* FASE DE VALIDACIÓN: "¿Cómo lo ves [Nombre]? ¿Cerramos así o ajustamos algo?"
* PROTOCOLO DE CIERRE:
   1. PEDIDO ÚNICO: "Excelente. Para reservar, solo me falta: CUIT/DNI y Teléfono." (Ya tenés Nombre y Loc).
   2. LINK: Genera el link Markdown.
   * Respuesta Final:
      "Listo. Hacé clic abajo para confirmar con el vendedor:"
      [✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)](LINK)
      "O escribinos al: 3401-648118"
      "📍 Retiro: [Ver Ubicación en Mapa](https://www.google.com/maps/search/?api=1&query=Pedro+Bravin+Materiales+El+Trebol)"
"""

# 4. INTERFAZ
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

# Inicializa el historial de mensajes
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?"}]

# --- INICIALIZACIÓN DEL MODELO Y LA SESIÓN DE CHAT (Para mejorar la velocidad) ---
if "chat_session" not in st.session_state:
    try:
        # **CORRECCIÓN DE MODELO: Se usa el alias del modelo estable 'gemini-2.5-flash'**
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        
        # CORRECCIÓN CRÍTICA (Error 400):
        # Mapeamos 'assistant' a 'model' y EXCLUIMOS el primer mensaje (el saludo de bienvenida) 
        # para que la secuencia de roles sea válida para la API.
        initial_history = []
        # Iteramos a partir del índice 1, ya que el índice 0 es el mensaje de bienvenida de Streamlit.
        for m in st.session_state.messages[1:]: 
            if m["role"] == "assistant":
                api_role = "model"
            elif m["role"] == "user":
                api_role = "user"
            else:
                continue # Saltar roles inesperados
            
            initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")
        
# Muestra los mensajes anteriores en el chat
for msg in st.session_state.messages:
    # El rol en st.session_state ya es 'user' o 'assistant'
    st.chat_message(msg["role"]).write(msg["content"])

# Captura la entrada del usuario
if prompt := st.chat_input():
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        if "chat_session" not in st.session_state:
             st.error("No se pudo iniciar la sesión de chat. Revise la autenticación o el prompt inicial.")
             st.stop()
             
        chat = st.session_state.chat_session
        
        # Muestra el indicador de carga en la burbuja del asistente
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            # --- MODIFICACIÓN DEL MENSAJE DE CARGA AQUÍ ---
            message_placeholder.markdown("estoy pensando aguardame que te puedo sorprender")
        
            response = chat.send_message(prompt)
        
            # Reemplaza el texto de carga con la respuesta final
            message_placeholder.markdown(response.text)
            
        # Guarda la respuesta en el estado de sesión
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        error_message = str(e)
        st.error(f"❌ Error en la llamada a la API de Gemini: {e}")
        
        if "429" in error_message or "Quota exceeded" in error_message:
            st.info(
                "🛑 **CUPO DE API EXCEDIDO (Error 429)**: Ha alcanzado el límite de tokens de entrada para el plan gratuito. "
                "Espere unos minutos antes de intentar de nuevo o considere revisar y actualizar su plan de facturación en Google AI Studio. "
                "[Más información sobre límites de cuota](https://ai.google.dev/gemini-api/docs/rate-limits)."
            )
        elif "400" in error_message and "valid role" in error_message:
             st.info("💡 **Error de Rol (400)**: Hubo un problema con la estructura del historial de chat. Se ha corregido el mapeo de roles.")
        elif "404" in error_message or "not found" in error_message.lower():
            st.info("💡 Consejo: El nombre del modelo puede ser incorrecto o su clave API no tiene acceso. Intente usar un alias diferente o crear una nueva clave.")
        else:
            st.info("Revise los detalles del error en la consola o el administrador de su aplicación.")
