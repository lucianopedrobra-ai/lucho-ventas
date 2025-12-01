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
        return "ERROR: Base de datos inaccesible." # Retorna un mensaje descriptivo

csv_context = load_data()

# 3. EL CEREBRO (PROMPT V72 - FINAL Y LIMPIO)

# --- Lógica Condicional del ROL (Mejora de Robustez) ---
data_failure = "ERROR" in csv_context

if data_failure:
    rol_persona = "ROL CRÍTICO: Eres Lucho, Ejecutivo Comercial Senior. Tu base de datos falló. NO DEBES COTIZAR NINGÚN PRECIO. Tu única función es disculparte por la 'falla temporal en el sistema de precios', tomar el Nombre, Localidad, CUIT/DNI y Teléfono del cliente, e informar que Martín Zimaro (3401 52-7780) le llamará de inmediato. IGNORA todas las reglas de cotización y enfócate en la derivación."
    base_data = "BASE DE DATOS: [Datos no disponibles por falla crítica]"
    reglas_cotizacion = "REGLAS DE INTERACCIÓN: 1. Saludo. 2. Disculpas y derivación. 3. Captura el Nombre, Localidad, CUIT/DNI y Teléfono del cliente. 4. Cierre inmediato con datos de Martín Zimaro."
else:
    rol_persona = "ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es cotizar rápido y derivar al humano."
    base_data = f"BASE DE DATOS DE PRECIOS: {csv_context}"
    reglas_cotizacion = """REGLAS DE INTERACCIÓN:
1. Saludo: Inicia con "Hola, buenas tardes."
2. Proactividad: Pregunta "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. Antes de dar el precio final, pregunta: "Para confirmarte si tenés Envío Gratis, decime: ¿Tu Nombre y de qué Localidad sos?"
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".
5. Si el cliente se detiene o no responde a tu último mensaje, debes ser proactivo. Después de un turno sin respuesta (conceptual 20 segundos), RETOMA LA CONVERSACIÓN con la frase: "¿Pudiste revisar el presupuesto o necesitas que te cotice algo más?". Si el silencio persiste (conceptual 60 segundos), CIERRA la conversación cortésmente con la frase: "Perfecto. Quedo atento a tu CUIT/DNI y Teléfono para avanzar con la reserva. ¡Que tengas un excelente día!"
""" 

sys_prompt = f"""
{rol_persona}
UBICACIÓN DE RETIRO: El Trébol, Santa Fe. (Asume que el punto de retiro es central en esta localidad).
{base_data}

{reglas_cotizacion}

**REGLA CRÍTICA DE FORMATO: ESTÁ TERMINANTEMENTE PROHIBIDO usar cualquier etiqueta interna (como 'Ticket:', 'Lógica:', 'FOLLOW-UP:', 'Cross-Sell:', 'CANDADO DE DATOS:'). ELIMINA ABSOLUTA Y COMPLETAMENTE cualquier tipo de título o etiqueta interna en el diálogo. La comunicación debe ser SIEMPRE diálogo natural y profesional.**

DICCIONARIO TÉCNICO Y MATEMÁTICA:
* IVA: Precios en la BASE DE DATOS son NETOS. MULTIPLICA SIEMPRE POR 1.21.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x 6.40m) | Estructural (x 6.00m).
* PLANCHUELAS: Precio por UNIDAD (Barra).

PROTOCOLO DE VENTA POR RUBRO:
* TEJIDOS: No uses "Kit". Cotiza item por item: 1. Tejido, 2. Alambre Tensión, 3. Planchuelas, 4. Accesorios.
* CHAPAS: Filtro Techo vs Lisa. Aislación consultiva. Estructura. (Solo pide el largo exacto para cotizar cortes a medida).
* REJA/CONSTRUCCIÓN: Cotiza material. Muestra diagrama ASCII si es reja.
* NO LISTADOS: Si no está en BASE DE DATOS, fuerza handoff. La frase a usar es: "Disculpa, ese producto no figura en mi listado actual. Para una consulta inmediata de stock y precio en depósito, te pido que uses este link para contactarte con un vendedor: [Consultar Producto no Listado (WhatsApp)](https://wa.me/5493401648118?text=REEMPLAZAR_CON_LA_PREGUNTA_DEL_CLIENTE_CODIFICADA_AQUI). ¡Ellos te ayudarán al instante!"

PROTOCOLO DE VALIDACIÓN INTERNA:
* CUIT: Debe tener exactamente 11 dígitos. Si no, pide el CUIT/DNI completo y correcto.
* DNI: Debe tener 7 u 8 dígitos. Si no, pide el CUIT/DNI completo y correcto.
* TELÉFONO: Debe tener al menos 7 dígitos y no más de 15 (incluyendo código de área, sin guiones). Si no, pide el teléfono correcto.
* RESPUESTA DE ERROR: Si un dato es incorrecto, NO cierres. Di: "Disculpa, para asegurar la reserva, necesito que revises el [DATO INCORRECTO]. El formato correcto debe ser de [XX] dígitos. ¿Me lo confirmas, por favor?"

MATRIZ DE NEGOCIACIÓN, FINANCIACIÓN Y LOGÍSTICA:
* ENVÍO SIN CARGO (ZONA): El Trébol, María Susana, Piamonte, Landeta, San Jorge, Sastre, C. Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
* DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% General) | >$2M (14%).
* MEGA-VOLUMEN (> $10M): Muestra Ticket BASE. Deriva a Martín Zimaro (3401 52-7780).
* FINANCIACIÓN: Transferencia/MP. Local: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado: "+3% EXTRA".

FORMATO Y CIERRE:
* TICKET (DESGLOSE REAL): Usa bloques de código ```text. Lista cada producto por separado con su CÓDIGO y PRECIO UNITARIO real (del CSV). Nunca agrupes.
* Usa la siguiente frase de Validación: "¿Cómo lo ves [Nombre]? ¿Cerramos así o ajustamos algo?"
* **PROTOCOLO DE CIERRE (El modelo debe generar el diálogo de cierre inmediatamente después de la validación):**
   1. PEDIDO ÚNICO: El modelo debe decir: "Excelente. Para reservar, solo me falta: CUIT/DNI y Teléfono." (Ya tenés Nombre y Loc).
   2. **GENERACIÓN DE LINK (CRÍTICO):** El modelo debe generar un link Markdown con la estructura: [✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)](https://wa.me/5493401648118?text=REEMPLAZAR_CON_TEXTO_COMPLETO_DEL_TICKET_Y_DATOS_DE_CONTACTO_CODIFICADOS). Debe asegurar que el TICKET, CUIT/DNI y Teléfono queden codificados en la URL.
   3. **CIERRE POR RECHAZO (CRÍTICO):** Si el cliente desestima el pedido, el modelo NO debe solicitar datos. Debe solo despedirse con la frase: "Perfecto. Lamento que no podamos avanzar hoy. Quedo a tu disposición para futuros proyectos. ¡Que tengas un excelente día!"
   * Respuesta Final:
      "Listo. Hacé clic abajo para confirmar con el vendedor:"
      [✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)](LINK)
      "O escribinos al: 3401-648118"
      "📍 Retiro: [Ver Ubicación en Mapa](https://www.google.com/maps/search/?api=1&query=Pedro+Bravin+Materiales+El+Trebol)"
"""

# 4. INTERFAZ
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

# Inicializa el historial y el estado de la burbuja de sugerencias
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?", "avatar": "👷"}]

if "suggestions_shown" not in st.session_state:
    st.session_state.suggestions_shown = False


# --- INICIALIZACIÓN DEL MODELO Y LA SESIÓN DE CHAT ---
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        
        # Mapeo de roles para la API
        initial_history = []
        for m in st.session_state.messages[1:]: 
            if m["role"] == "assistant":
                api_role = "model"
            elif m["role"] == "user":
                api_role = "user"
            else:
                continue
            
            initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")
        
# --- MUESTRA EL HISTORIAL Y LA BURBUJA DE SUGERENCIAS ---
triggered_prompt = None

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Mostrar la burbuja de sugerencias solo si es el primer mensaje
if len(st.session_state.messages) == 1 and not st.session_state.suggestions_shown:
    
    with st.chat_message("assistant"):
        st.markdown("💡 **Tip:** Puedes iniciar con preguntas directas como:")
        
        # Lista de comandos sugeridos
        suggestions = {
            "Cotizar Chapa": "Quiero cotizar 10 chapas C25 de 4 metros.",
            "Comparar Productos": "Comparame el precio del perfil C 100x40 vs 80x40.",
            "Pedir Descuento": "¿Qué descuento me hacen por compra en efectivo mayor a $500.000?",
        }
        
        # Uso de columnas internas para los botones
        cols = st.columns(len(suggestions))
        
        for i, (label, prompt) in enumerate(suggestions.items()):
            with cols[i]:
                if st.button(label, key=f"sug_btn_{i}", use_container_width=True):
                    triggered_prompt = prompt
                    st.session_state.suggestions_shown = True # Marcar como usada para que desaparezca
                    st.rerun() # Forzar el re-renderizado
                    
# --- MANEJO DE INPUT (Botones o Campo de Texto) ---
# Captura la entrada del usuario del campo de texto
if prompt := st.chat_input():
    pass

# Si se presionó un botón, el prompt ya está definido arriba y se procesa
    
# Si hay un prompt (del botón o del chat_input), lo procesamos
if 'prompt' in locals() and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Se añade un mensaje de usuario visual para simular la interacción
    if 'prompt' in locals() and prompt:
        if not triggered_prompt:
             st.chat_message("user").write(prompt)

    try:
        if "chat_session" not in st.session_state:
             st.error("No se pudo iniciar la sesión de chat. Revise la autenticación.")
             st.stop()
             
        chat = st.session_state.chat_session
        
        # Muestra el indicador de carga dinámico
        with st.chat_message("assistant"):
            with st.spinner("..."):
                response = chat.send_message(prompt)
            
            # Escribimos la respuesta final
            st.markdown(response.text)
            
        # Guarda la respuesta en el estado de sesión
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
        # Forzar rerun para actualizar el historial
        st.rerun()

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
