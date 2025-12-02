import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re 
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🧑‍💼", layout="wide")

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

# 2. CARGA DE DATOS (Contexto Estático)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    """Carga los datos desde la URL de la hoja de cálculo y retorna el DataFrame. (MODIFICADO)"""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df # <-- Retorna el DataFrame
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg:
            st.error(
                f"🚨 Error 404 (Not Found) al cargar datos: El link en SHEET_URL es incorrecto o la hoja no está publicada como CSV."
            )
        else:
            st.error(f"Error inesperado leyendo la lista de productos: {e}")
        return "ERROR_DATA_LOAD_FAILED"

# --- MANEJO DE DATOS Y ESTADO ---
raw_data = load_data()
data_failure = (raw_data == "ERROR_DATA_LOAD_FAILED")

if not data_failure:
    st.session_state.df_data = raw_data # <-- Guarda el DF en session_state para filtrado dinámico
    csv_context = raw_data.to_string(index=False) # <-- String completo para el System Prompt inicial
else:
    csv_context = "ERROR_DATA_LOAD_FAILED"
    st.warning(
        "⚠️ Atención: El sistema de precios no pudo cargar la base de datos. "
        "Lucho solo podrá tomar tus datos de contacto y derivarte a un vendedor humano."
    )

# 2.6. FUNCIÓN DE VALIDACIÓN DE DATOS LOCAL
def validate_contact_data(text_input):
    """
    Busca patrones de CUIT/DNI y Teléfono en el texto y valida su formato.
    Si la validación local falla, retorna un mensaje de error para el usuario.
    """
    
    text_cleaned = re.sub(r'[^\d\s]', '', text_input) 
    numbers = re.findall(r'\b\d+\b', text_input)
    
    if len(text_input) < 50 and len(numbers) >= 2: 
        
        for num in numbers:
            length = len(num)
            
            if length == 11: 
                pass 
            
            elif length in [7, 8]: 
                pass
            
            elif length >= 7 and length <= 15:
                pass
            
            elif length > 1 and ('cuit' in text_input.lower() or 'dni' in text_input.lower() or 'tel' in text_input.lower()):
                if length > 15:
                    return "Disculpa, el **Teléfono** o **CUIT** que enviaste parece tener un formato incorrecto. Confírmame que el CUIT es de 11 dígitos y el teléfono (con código de área) está completo."
                elif length < 7:
                    return "Disculpa, para asegurar la reserva, necesito que revises el **DNI** (7 u 8 dígitos) o el **Teléfono** (al menos 7 dígitos). ¿Me lo confirmas, por favor?"

    return None

# 2.7. FUNCIÓN DE FILTRADO DINÁMICO DE CONTEXTO (NUEVO)
def filter_data_by_prompt(prompt, df_data):
    """Filtra el DataFrame por rubro para reducir el contexto enviado a Gemini."""
    prompt_lower = prompt.lower()
    
    keywords = {
        'chapa': ['chapa', 'techo', 'acanalada', 't-101', 'perfil-c'],
        'tejidos': ['tejido', 'cerco', 'alambre', 'poste', 'romboidal', 'malla'],
        'perfiles': ['perfil', 'viga', 'c', 'estructural', 'caño', 'tubo', 'hierro', 'planchuela', 'angulo', 'ipn'],
        'pintura': ['pintura', 'tersuave', 'sintetico', 'esmalte'],
        'aislante': ['aislante', 'aislacion', 'lana', 'rollo']
    }
    
    selected_rubros = set()
    for rubro_key, words in keywords.items():
        if any(word in prompt_lower for word in words):
            selected_rubros.add(rubro_key)

    if selected_rubros:
        try:
            # Asume la columna 'Rubro'
            mask = df_data['Rubro'].astype(str).str.lower().apply(lambda x: any(r in x for r in selected_rubros))
            df_filtered = df_data[mask]
            
            if not df_filtered.empty:
                return df_filtered.to_string(index=False)
        except KeyError:
            # Fallback si no encuentra la columna 'Rubro'
            pass
            
    # Fallback: si no se pudo filtrar, envía todo el contexto estático
    return df_data.to_string(index=False)


# 3. EL CEREBRO (PROMPT V93 - Protocolos Ordenados)

if data_failure:
    rol_persona = "ROL CRÍTICO: Eres Lucho, Ejecutivo Comercial Senior. Tu base de datos falló. NO DEBES COTIZAR NINGÚN PRECIO. Tu única función es disculparte por la 'falla temporal en el sistema de precios', tomar el Nombre, Localidad, CUIT/DNI y Teléfono del cliente, e informar que Martín Zimaro (3401 52-7780) le llamará de inmediato. IGNORA todas las reglas de cotización y enfócate en la derivación."
    base_data = "BASE DE DATOS: [Datos no disponibles por falla crítica]"
    reglas_cotizacion = "REGLAS DE INTERACCIÓN: 1. Saludo. 2. Disculpas y derivación. 3. Captura el Nombre, Localidad, CUIT/DNI y Teléfono del cliente. 4. Cierre inmediato con datos de Martín Zimaro."
else:
    rol_persona = "ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es cotizar rápido y derivar al humano. En tus sugerencias y cotizaciones consultivas, prioriza discretamente las opciones de mayor valor (ticket) para el cliente, sin usar adjetivos de valor como 'más económico' o 'mejor diseño'."
    
    base_data = f"""
    PRIORIDAD DE PRECIOS: Los precios en la BASE DE DATOS a continuación son la ÚNICA fuente de verdad. La cotización debe venir directamente de ellos.
    BASE DE DATOS:
    {csv_context}
    """
    
    reglas_cotizacion = """REGLAS DE INTERACCIÓN:
1. Saludo: **SOLO si el chat está vacío**, inicia con "Hola, buenas tardes."
2. Proactividad: **Si el cliente hace una pregunta vaga o no da información de rubro**, pregunta "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?". **En caso de recibir una consulta clara (ej. "quiero chapa"), salta esta regla y ve a cotizar o al protocolo de NO LISTADOS.**
3. Declaración de Servicio (OPTIMIZADA): Después de dar el precio de un producto, declara: "Te confirmo que tenemos Envío Sin Cargo en nuestra zona. Para verificar si aplica a tu proyecto o si prefieres retirar, necesito que me digas tu Localidad."
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".
4.5. Retoma de Datos (CRÍTICA): Si el cliente proporciona una respuesta parcial a una pregunta consultiva obligatoria (ej. solo el 'tipo de chapa' pero no el 'largo'), el modelo DEBE reconocer el dato provisto y SOLICITAR ÚNICAMENTE los datos faltantes (**enumerando lo que falta**) de forma concisa.
5. Proactividad ante Silencio (MEJORADA): Si en el turno anterior el cliente solo envió una respuesta corta o de confirmación (ej. "ok", "gracias", un emoji), o si su mensaje NO contiene una pregunta, ASUME que se detuvo y RETOMA la CONVERSACIÓN con la frase: "¿Pudiste revisar el presupuesto o necesitas que te cotice algo más?". Si el silencio persiste por TRES turnos consecutivos (incluyendo el de seguimiento), aplica el CIERRE CORTÉS.
""" 

sys_prompt = f"""
{rol_persona}
UBICACIÓN DE RETIRO: El Trébol, Santa Fe. (Asume que el punto de retiro es central en esta localidad).
{base_data}

{reglas_cotizacion}

**REGLA CRÍTICA DE FORMATO: ESTÁ TERMINANTEMENTE PROHIBIDO usar cualquier etiqueta interna (como 'Ticket:', 'Lógica:', 'FOLLOW-UP:', 'Cross-SELL:', 'CANDADO DE DATOS:').
LA ÚNICA Y ABSOLUTA EXCEPCIÓN ES LA ETIQUETA [TEXTO_WHATSAPP]:. 
Si el protocolo de cierre aplica (ya se tienen todos los datos del cliente), DEBE incluir la etiqueta **[TEXTO_WHATSAPP]:** como el **último elemento de la respuesta**, conteniendo el texto plano a enviar al vendedor. LA COMUNICACIÓN DEBE SER SIEMPRE diálogo natural y profesional.**

DICCIONARIO TÉCNICO Y MATEMÁTICA:
* IVA: Precios en la BASE DE DATOS son NETOS. MULTIPLICA SIEMPRE POR 1.21.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x 6.40m) | Estructural (x 6.00m).
* PLANCHUELAS: Precio por UNIDAD (Barra).
* RENDIMIENTO PINTURAS (Tersuave Sintético): 12 m² por litro por mano. Para estructuras metálicas y chapas, se recomiendan 2 manos (24 m² por litro, trabajo terminado).

PROTOCOLO DE VENTA POR RUBRO:
* TEJIDOS (Consultivo V93 - Máxima Precisión): No uses "Kit". El objetivo es cotizar la solución completa: Tejido, Alambre Tensión, Planchuelas, Accesorios.
    * **REGLA DE CONSULTA OBLIGATORIA (ÚNICA Y ORDENADA):** Si el cliente pregunta por cerco o tejido sin especificar dimensiones ni calidad, Lucho DEBE preguntar en un solo turno, usando un tono consultivo para clasificar el proyecto. El orden es inmutable:
        "Para cotizar una solución completa y precisa, necesito tres datos clave: 
        1. **Tipo de Proyecto:** ¿Buscas un cerco de **delimitación** (el tejido romboidal tradicional) o de **alta seguridad** (malla electrosoldada)?
        2. **Dimensiones:** ¿Qué **altura** y **longitud total** (en metros) tiene el cerco?
        3. **Calidad:** ¿Prefieres el **calibre estándar (calibre 14)** o uno más resistente (ej. calibre 12)?"
    * **Lucho DEBE esperar la respuesta a los tres puntos (Tipo, Dimensiones y Calidad) antes de cotizar o generar el TICKET final.**
    * Después de cotizar, si los postes o accesorios son material ferroso **NO galvanizado o epoxi**, pregunta si necesita pintura y accesorios de fijación extra.

* CHAPAS (Optimizado - Bundled V93):
    * **REGLA DE CONSULTA ÚNICA (OBLIGATORIA):** Si el cliente pide "chapa" o "techo" sin especificar variables, Lucho DEBE preguntar en un solo turno, enumerando las variables:
        "Para cotizar tu techo con precisión, necesito tres datos clave: 
        1. **Tipo de Perfil:** ¿Buscas Chapa Acanalada Común o el perfil T-101?
        2. **Largo y Cantidad:** ¿Qué **largo exacto** necesitas para la caída del agua y cuántas unidades?
        3. **Acabado:** ¿La prefieres en color (prepintada) o en galvanizada estándar?"
    * Lucho DEBE esperar la respuesta a esta pregunta multifacética antes de cotizar.
    * **LÓGICA DEL LARGO:** Si el cliente pregunta solo por el precio "por metro", usa el precio unitario del código base. Si pregunta por una cantidad total (ej. "30 metros de chapa"), cotiza el total multiplicando esa cantidad por el precio base.
    * **COLORES/ACABADOS:** El color implica un costo adicional por metro lineal sobre el precio base galvanizado. El bot debe considerar la opción de color en el precio final.
    * **CROSS-SELL PINTURA/FIJACIÓN:** La venta cruzada de pintura y fijación debe realizarse **INMEDIATAMENTE DESPUÉS** de la cotización principal, en el mismo turno, utilizando la frase experta definida.
    * FILTROS: Filtro Techo vs Lisa. Aislación consultiva. Estructura. (Solo pide el largo exacto **PARA PRESUPUESTO FINAL Y DETALLADO** después de haber dado el precio por metro).

* REJA/CONSTRUCCIÓN (Consultivo V93 - Perfiles C y Estructurales): Cotiza material. Muestra diagrama ASCII si es reja.
    * **REGLA DE CONSULTA ÚNICA (OBLIGATORIA):** Si el cliente pregunta por material de reja/estructura sin especificar, Lucho DEBE preguntar en un solo turno, enumerando las variables:
        "Para cotizar el material de tu estructura o reja, necesito tres datos:
        1. **Material:** ¿Buscas perfiles de **hierro macizo** o **caños estructurales (tubos)**?
        2. **Dimensiones:** ¿Qué medidas aproximadas (**largo y alto**) tiene tu proyecto?
        3. **Uso y Acabado:** ¿La estructura será soldada y necesita ser **galvanizada** o solo **con pintura base**?"
    * Después de cotizar el material, si el material es siderúrgico ferroso NO galvanizado, epoxi o prepintado, usa la frase de experto para la venta cruzada.
* NO LISTADOS: Si no está en BASE DE DATOS, fuerza handoff. La frase a usar es: "Disculpa, ese producto no figura en mi listado actual. Para una consulta inmediata de stock y precio en depósito, te pido que te contactes directamente con un [vendedor al 3401-648118](tel:+543401648118). ¡Ellos te ayudarán al instante!"

PROTOCOLO LOGÍSTICO (POST-LOCALIDAD):
* Si la Localidad del cliente está en la lista de ENVÍO SIN CARGO (ZONA), usa la frase: "¡Excelente! Estás dentro de nuestra zona de **Envío Sin Cargo**."
* Si la Localidad NO está en la lista de ENVÍO SIN CARGO (ZONA), usa la frase: "Para esa Localidad no aplica el Envío Sin Cargo. Tienes dos opciones: 1. **Retiro** en El Trébol, Santa Fe, o 2. Lo derivo a un vendedor para que verifique si la entrega es posible y cuál sería su costo. ¿Qué prefieres?"

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
* Usa la siguiente frase de Validación: "¿Cómo lo ves {{Nombre}}? ¿Cerramos así o ajustamos algo?"
* PROTOCOLO DE CIERRE (El modelo debe generar el diálogo de cierre inmediatamente después de la validación):
   1. PEDIDO FINAL (Contundente): El modelo debe decir: "Excelente. Para enviarle al depósito la reserva, solo me falta: Nombre, CUIT/DNI y Teléfono." (Ya tenés Localidad).
   2. GENERACIÓN DE TICKET FINAL (PASO CRÍTICO): Genera, después de la frase de Validación y la solicitud de Nombre, CUIT/DNI y Teléfono, un bloque de código oculto (sin mostrar al cliente) que contenga el texto plano (sin formato Markdown) que será enviado por WhatsApp al vendedor. Usa la etiqueta [TEXTO_WHATSAPP]:.
   3. CIERRE POR RECHAZO (CRÍTICO): Si el cliente desestima el pedido, el modelo NO debe solicitar datos. Debe solo despedirse con la frase: "Perfecto. Lamento que no podamos avanzar hoy. Quedo a tu disposición para futuros proyectos. ¡Que tengas un excelente día!"
"""

# 4. INTERFAZ
st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

# Inicializa el historial y el estado de la burbuja de sugerencias
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas tardes. Soy Lucho. ¿Qué proyecto tenés hoy?"}] # Saludo optimizado V93
if "suggestions_shown" not in st.session_state:
    st.session_state.suggestions_shown = False
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False
if "df_data" not in st.session_state and not data_failure:
    st.session_state.df_data = raw_data


# --- INICIALIZACIÓN DEL MODELO Y LA SESIÓN DE CHAT ---
if "chat_session" not in st.session_state:
    try:
        # 🚨 Gemini 2.5 Pro para mayor precisión de lógica comercial
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")
        

# --- FLUJO PRINCIPAL DE CHAT Y RENDERIZADO ---

for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "user" 
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Muestra las sugerencias solo en el primer turno
if len(st.session_state.messages) == 1 and not st.session_state.suggestions_shown:
    
    suggestions_text = [
        "**Cotizar Techo** (ej. 'Quiero cotizar un techo de 8x5 metros.')",
        "**Materiales Cerco** (ej. 'Necesito material para un cerco de 50 metros con tejido y postes.')",
        "**Cotizar Reja** (ej. 'Cotizame una reja de seguridad de 2x3 metros.')",
        "**Recomendación Siderúrgica** (ej. 'Qué tipo de perfil estructural me recomiendas para una viga de 6 metros?')"
    ]
    
    with st.chat_message("assistant"):
        st.markdown(
            "***Ejemplos de preguntas que puedes hacer:***"
        )
        for tip in suggestions_text:
            st.markdown(f"* {tip}")
            
    st.session_state.suggestions_shown = True 
            
# --- MANEJO DE INPUT (Campo de Texto) ---

if prompt := st.chat_input("Escribe tu consulta de cotización o proyecto..."):
    prompt_to_process = prompt
else:
    prompt_to_process = None

# 2. Procesamiento Centralizado del Chat
if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    st.chat_message("user").markdown(prompt_to_process)

    # Validación Local antes de llamar a Gemini
    local_error = validate_contact_data(prompt_to_process)
    
    if local_error:
        with st.chat_message("assistant", avatar="🧑‍💼"):
            st.markdown(local_error)
        st.session_state.messages.append({"role": "assistant", "content": local_error})
        st.rerun()

    try:
        if "chat_session" not in st.session_state:
             st.error("No se pudo iniciar la sesión de chat. Revise la autenticación.")
             st.stop()
                 
        chat = st.session_state.chat_session
        response = None
        
        # --- LÓGICA DE INYECCIÓN DE CONTEXTO DINÁMICO (MODIFICADO) ---
        if not data_failure:
            # 1. Filtra el DF con el prompt del usuario
            filtered_context = filter_data_by_prompt(prompt_to_process, st.session_state.df_data)
            
            # 2. Genera el prompt final inyectando el contexto relevante
            # Se le informa a Gemini que este es el contexto relevante.
            full_gemini_prompt = f"Consulta del cliente: {prompt_to_process}\n\n[CONTEXTO_RELEVANTE_PARA_COTIZAR]:\n{filtered_context}"
        else:
            # Si hubo falla en la carga de datos, el prompt es solo la consulta del cliente
            full_gemini_prompt = prompt_to_process 
        # --- FIN LÓGICA DE INYECCIÓN ---
            
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Lucho está cotizando..."):
                response = chat.send_message(full_gemini_prompt)
            
            final_response_text = response.text
            whatsapp_link_section = ""
            
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            if WHATSAPP_TAG in final_response_text:
                dialogue_part, whatsapp_part = final_response_text.split(WHATSAPP_TAG, 1)
                st.markdown(dialogue_part.strip())
                
                whatsapp_text = whatsapp_part.strip()
                encoded_text = urllib.parse.quote(whatsapp_text)
                whatsapp_url = f"https://wa.me/5493401648118?text={encoded_text}"
                
                whatsapp_link_section = f"""
---
Listo. Hacé clic abajo para confirmar con el vendedor:

[✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)]({whatsapp_url})

O escribinos al: 3401-648118

📍 Retiro: [Ver Ubicación en Mapa](https://www.google.com/maps/search/?api=1&query=Pedro+Bravin+Materiales+El+Trebol)
"""
                st.markdown(whatsapp_link_section)
                
                final_response_for_history = dialogue_part.strip() + "\n\n" + whatsapp_link_section.strip()
            else:
                st.markdown(response.text)
                final_response_for_history = response.text
                
        st.session_state.messages.append({"role": "assistant", "content": final_response_for_history})
        st.rerun()

    except Exception as e:
        error_message = str(e)
        st.error(f"❌ Error en la llamada a la API de Gemini: {e}")
        
        if "429" in error_message or "Quota exceeded" in error_message:
            st.info("🛑 **CUPO DE API EXCEDIDO (Error 429)**...")
        elif "400" in error_message and "valid role" in error_message:
              st.info("💡 **Error de Rol (400)**:...")
        elif "404" in error_message or "not found" in error_message.lower():
            st.info("💡 Consejo: El nombre del modelo puede ser incorrecto o su clave API no tiene acceso...")
        else:
            st.info("Revise los detalles del error en la consola o el administrador de su aplicación.")
