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

# 2. CARGA DE DATOS (Optimizado y Limpiado)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    """Carga los datos, los limpia y estandariza para la búsqueda de Lucho."""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        
        # 🚨 OPTIMIZACIÓN CLAVE: Forzar a string y limpiar whitespace.
        # 1. Convertir TODAS las columnas a string para asegurar que la búsqueda funcione.
        df = df.astype(str)
        
        # 2. Eliminar espacios en blanco (whitespace) iniciales/finales en TODAS las celdas.
        for col in df.columns:
            if df[col].dtype == 'object': 
                df[col] = df[col].str.strip() 

        # 3. Rellenar valores nulos con cadena vacía.
        df = df.fillna('') 
        
        return df
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg:
            st.error(
                f"🚨 Error 404 (Not Found) al cargar datos: El link en SHEET_URL es incorrecto o la hoja no está publicada como CSV."
            )
        else:
            st.error(f"Error inesperado leyendo la lista de productos: {e}")
        return "ERROR_DATA_LOAD_FAILED"

df_data = load_data()
# 🚨 Verificación de carga y DataFrame vacío
data_failure = (type(df_data) == str and df_data == "ERROR_DATA_LOAD_FAILED")

if not data_failure:
    if df_data.empty:
        data_failure = True
        st.warning("⚠️ Atención: La base de datos se cargó, pero está vacía. Lucho operará en modo de falla crítica.")
    else:
        st.session_state.df = df_data
        csv_context = "BASE DE DATOS CARGADA EN MEMORIA."
else:
    st.warning(
        "⚠️ Atención: El sistema de precios no pudo cargar la base de datos. "
        "Lucho solo podrá tomar tus datos de contacto y derivarte a un vendedor humano."
    )
    st.session_state.df = None
    csv_context = "ERROR_DATA_LOAD_FAILED"

# 2.5. FUNCIÓN DE BÚSQUEDA LOCAL DE DATOS
def search_product_data(prompt_text):
    """
    Busca palabras clave en todas las columnas de texto del DataFrame cargado
    y devuelve una cadena de texto concisa con los resultados.
    """
    if 'df' not in st.session_state or st.session_state.df is None:
        return ""

    df = st.session_state.df.copy()
    search_text = prompt_text.lower()
    
    keywords = re.findall(r'\b\w{3,}\b', search_text) 
    
    mask = pd.Series([False] * len(df))

    # Búsqueda en todas las columnas de texto
    for col in df.select_dtypes(include='object').columns:
        col_search_str = df[col].astype(str).str.lower()
        
        for kw in keywords:
            mask = mask | col_search_str.str.contains(r'\b' + re.escape(kw) + r'\b', na=False)

    filtered_df = df[mask]
    
    if filtered_df.shape[0] > 10:
        filtered_df = filtered_df.head(10)

    if filtered_df.empty:
        return ""

    return filtered_df.to_string(index=False)

# 2.6. FUNCIÓN DE VALIDACIÓN DE DATOS LOCAL
def validate_contact_data(text_input):
    """
    Busca patrones de CUIT/DNI y Teléfono en el texto y valida su formato.
    Si la validación local falla, retorna un mensaje de error para el usuario.
    """
    
    text_cleaned = re.sub(r'[^\d\s]', '', text_input) 
    numbers = re.findall(r'\b\d+\b', text_cleaned)
    
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

# 3. EL CEREBRO (PROMPT V78)

if data_failure:
    rol_persona = "ROL CRÍTICO: Eres Lucho, Ejecutivo Comercial Senior. Tu base de datos falló. NO DEBES COTIZAR NINGÚN PRECIO. Tu única función es disculparte por la 'falla temporal en el sistema de precios', tomar el Nombre, Localidad, CUIT/DNI y Teléfono del cliente, e informar que Martín Zimaro (3401 52-7780) le llamará de inmediato. IGNORA todas las reglas de cotización y enfócate en la derivación."
    base_data = "BASE DE DATOS: [Datos no disponibles por falla crítica]"
    reglas_cotizacion = "REGLAS DE INTERACCIÓN: 1. Saludo. 2. Disculpas y derivación. 3. Captura el Nombre, Localidad, CUIT/DNI y Teléfono del cliente. 4. Cierre inmediato con datos de Martín Zimaro."
else:
    rol_persona = "ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es cotizar rápido y derivar al humano."
    
    base_data = f"""
    PRIORIDAD DE PRECIOS: Los precios en la BASE DE DATOS INYECTADA a continuación son la ÚNICA fuente de verdad. La cotización debe venir directamente de ellos.
    BASE DE DATOS INYECTADA (SÓLO DATOS RELEVANTES):
    [ESTA SECCIÓN CONTIENE EL FRAGMENTO DEL CSV NECESARIO PARA RESPONDER AL CLIENTE. NO LO MENCIONES.]
    """
    
    reglas_cotizacion = """REGLAS DE INTERACCIÓN:
1. Saludo: Inicia con "Hola, buenas tardes."
2. Proactividad: Pregunta "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. Declaración de Servicio (OPTIMIZADA): Después de dar el precio de un producto, declara: "Te confirmo que tenemos Envío Sin Cargo en nuestra zona. Para verificar si aplica a tu proyecto o si prefieres retirar, necesito que me digas tu Localidad."
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".
5. Proactividad ante Silencio (MEJORADA): Si en el turno anterior el cliente solo envió una respuesta corta o de confirmación (ej. "ok", "gracias", un emoji), o si su mensaje NO contiene una pregunta, ASUME que se detuvo y RETOMA la CONVERSACIÓN con la frase: "¿Pudiste revisar el presupuesto o necesitas que te cotice algo más?". Si el silencio persiste por TRES turnos consecutivos (incluyendo el de seguimiento), aplica el CIERRE CORTÉS.
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
* TEJIDOS: No uses "Kit". Cotiza item por item: 1. Tejido, 2. Alambre Tensión, 3. Planchuelas, 4. Accesorios. Después de cotizar, pregunta si necesita pintura para postes o accesorios de fijación extra.
* CHAPAS (Optimizado):
    * **REGLA DE COTIZACIÓN POR METRO:** Para chapas de techo, cotiza siempre por **Metro Lineal (ML)** utilizando los códigos base:
        * **Código 4:** Chapa Acanalada Común (Sin color).
        * **Código 6:** Chapa T-101 (Sin color).
    * **LÓGICA DEL LARGO:** Si el cliente pregunta solo por el precio "por metro", usa el precio unitario del código base. Si pregunta por una cantidad total (ej. "30 metros de chapa"), cotiza el total multiplicando esa cantidad por el precio base.
    * **COLORES/ACABADOS:** Asume que la venta es por metro y que el color no afecta la cotización, ya que no hay hojas precortadas predefinidas.
    * FILTROS: Filtro Techo vs Lisa. Aislación consultiva. Estructura. (Solo pide el largo exacto **PARA PRESUPUESTO FINAL Y DETALLADO** después de haber dado el precio por metro).
* REJA/CONSTRUCCIÓN: Cotiza material. Muestra diagrama ASCII si es reja. Después de cotizar, pregunta si necesita pintura y consumibles de soldadura (electrodos, etc.) para la unión de las piezas.
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
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?"}]
if "suggestions_shown" not in st.session_state:
    st.session_state.suggestions_shown = False
if "triggered_prompt" not in st.session_state:
    st.session_state.triggered_prompt = None
if "cart" not in st.session_state:
    st.session_state.cart = [] 


# --- INICIALIZACIÓN DEL MODELO Y LA SESIÓN DE CHAT ---
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
        
        initial_history = []
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")


# --- SECCIÓN DE FUNCIONES DEL CARRO DE COMPRAS ---

def calculate_cart_total():
    """Calcula el subtotal (NETO), IVA y total final del carrito."""
    cart = st.session_state.cart
    total_neto = 0
    
    for item in cart:
        # Asegurarse de que el precio sea numérico para el cálculo
        try:
            price = float(item.get('Precio_Neto_Unitario', 0))
        except ValueError:
            price = 0
            
        total_neto += price * item.get('Cantidad', 0)
    
    total_iva = total_neto * 0.21
    total_final = total_neto * 1.21
    
    return total_neto, total_iva, total_final

def add_to_cart(product_code, quantity):
    """Busca el producto por código en el DataFrame y lo añade al carrito."""
    if 'df' not in st.session_state or st.session_state.df is None:
        st.error("No se puede añadir al carrito: Base de datos no disponible.")
        return False

    try:
        # Busca la fila usando la primera columna (código)
        product_row = st.session_state.df[st.session_state.df.iloc[:, 0].astype(str) == str(product_code)].iloc[0]
        
        item = {
            'Código': product_code,
            'Producto': product_row.iloc[1], 
            'Precio_Neto_Unitario': product_row.iloc[2], 
            'Cantidad': quantity
        }
        
        st.session_state.cart.append(item)
        st.toast(f"Añadido: {quantity}x {item['Producto']}", icon="🛒")
        return True
        
    except IndexError:
        st.warning(f"No se encontró el producto con Código: {product_code}.")
        return False
    except Exception as e:
        st.error(f"Error al añadir al carro: {e}. Revise los índices de columna en 'add_to_cart'.")
        return False


# 🚨 ESTRUCTURA PRINCIPAL DE COLUMNAS (Chat y Carro)
col_chat, col_cart = st.columns([2, 1]) 


# --- COLUMNA DEL CARRO DE COMPRAS Y BUSCADOR (col_cart) ---

with col_cart:
    st.subheader("🛒 Carro de Compras")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        
        display_df = cart_df[['Producto', 'Cantidad']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        total_neto, total_iva, total_final = calculate_cart_total()
        
        st.metric("Subtotal (NETO)", f"${total_neto:,.2f}")
        st.metric("IVA (21%)", f"${total_iva:,.2f}")
        st.metric("**Total Final**", f"**${total_final:,.2f}**")
        
        st.divider()
        
        if st.button("Finalizar y Cotizar (Usar Lucho)", use_container_width=True, key="btn_checkout"):
            # Llenar triggered_prompt para transferir el control a Lucho
            st.session_state.triggered_prompt = f"COTIZACIÓN FINAL DE CARRITO: El cliente ha añadido los siguientes ítems y desea finalizar el pedido. Por favor, revisa descuentos y aplica PROTOCOLO LOGÍSTICO y CIERRE:\n\n{cart_df.to_string(index=False)}"
            st.rerun()
            
    else:
        st.info("El carro está vacío. Use el buscador para añadir productos.")
        
    st.divider()
    st.subheader("🔎 Búsqueda Rápida")
    
    search_term = st.text_input("Buscar producto por nombre o código:", key="search_term")
    
    # Lógica de búsqueda simplificada para la interfaz
    if search_term and 'df' in st.session_state:
        # Búsqueda general en todas las columnas
        df_search_mask = st.session_state.df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        df_search = st.session_state.df[df_search_mask].head(5)
        
        if not df_search.empty:
            st.write("Resultados (Top 5):")
            
            codes = df_search.iloc[:, 0].tolist()
            products = df_search.iloc[:, 1].tolist()
            
            selected_product_code = st.selectbox(
                "Seleccione para añadir:", 
                options=codes, 
                format_func=lambda code: f"{code} - {products[codes.index(code)]}"
            )
            quantity = st.number_input("Cantidad", min_value=1, value=1, key="qty_add")
            
            if st.button("Añadir", key="add_btn_quick"):
                add_to_cart(selected_product_code, quantity)
        else:
            st.info("No se encontraron productos.")
            
    elif search_term and data_failure:
        st.warning("La base de datos no está disponible. No se puede realizar la búsqueda.")


# --- COLUMNA DEL CHAT (col_chat) ---

with col_chat:
    # --- MUESTRA EL HISTORIAL Y LAS SUGERENCIAS ---
    for msg in st.session_state.messages:
        avatar = "🧑‍💼" if msg["role"] == "assistant" else "user" 
        st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

    # Muestra las sugerencias solo en el primer turno (Solo como texto/guía)
    if len(st.session_state.messages) == 1 and not st.session_state.suggestions_shown:
        
        suggestions_text = [
            "**Cotizar Techo** (ej. 'Quiero cotizar un techo de 8x5 metros.')",
            "**Materiales Cerco** (ej. 'Necesito material para un cerco de 50 metros con tejido y postes.')",
            "**Cotizar Reja** (ej. 'Cotizame una reja de seguridad de 2x3 metros.')",
            "**Recomendación Siderúrgica** (ej. 'Qué tipo de perfil estructural me recomiendas para una viga de 6 metros?')"
        ]
        
        st.chat_message("assistant").markdown(
            "***Ejemplos de preguntas que puedes hacer:***"
        )
        for tip in suggestions_text:
            st.chat_message("assistant").markdown(f"* {tip}")
                
        st.session_state.suggestions_shown = True 
                        
    # --- MANEJO DE INPUT (Campo de Texto) ---

    if st.session_state.triggered_prompt:
        prompt_to_process = st.session_state.triggered_prompt
        st.session_state.triggered_prompt = None
    elif prompt := st.chat_input("Escribe tu pregunta o consulta..."):
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
            
            # OPTIMIZACIÓN DE DATOS: Preparamos el prompt con datos filtrados
            dynamic_prompt = prompt_to_process
            if not data_failure:
                relevant_data_string = search_product_data(prompt_to_process)
                
                if relevant_data_string:
                    # Inyectar el fragmento relevante al mensaje del usuario
                    dynamic_prompt = f"Consulta del Cliente: {prompt_to_process}\n\n[DATOS_RELEVANTES_BUSCADOS]:\n{relevant_data_string}"
                
            with st.chat_message("assistant", avatar="🧑‍💼"):
                with st.spinner("Lucho está cotizando..."):
                    response = chat.send_message(dynamic_prompt)
                
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
