import streamlit as st
import pandas as pd
import google.generativeai as genai
import urllib.parse
import re

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
    """Carga los datos desde la URL de la hoja de cálculo y retorna el DataFrame."""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df 
    except Exception as e:
        return "ERROR_DATA_LOAD_FAILED"

# --- MANEJO DE DATOS Y ESTADO ---
raw_data = load_data()

if isinstance(raw_data, pd.DataFrame):
    data_failure = False
    if "df_data" not in st.session_state:
        st.session_state.df_data = raw_data
    csv_context = raw_data.to_string(index=False)
else:
    data_failure = True
    csv_context = "ERROR_DATA_LOAD_FAILED"
    st.warning("⚠️ Atención: El sistema de precios no pudo cargar la base de datos. Lucho funcionará en modo 'Captura de Contacto' para derivación.")

# 2.5. FUNCIÓN DE FILTRADO DINÁMICO
def filter_data_by_prompt(prompt, df_data):
    """Filtra el DataFrame por rubro para reducir el contexto enviado a Gemini."""
    prompt_lower = prompt.lower()
    
    keywords = {
        'chapa': ['chapa', 'techo', 'acanalada', 't-101', 'perfil-c', 'cumbrera', 'cenefa'],
        'tejidos': ['tejido', 'cerco', 'alambre', 'poste', 'romboidal', 'malla'],
        'perfiles': ['perfil', 'viga', 'c', 'estructural', 'caño', 'tubo', 'hierro', 'planchuela', 'angulo', 'ipn'],
        'pintura': ['pintura', 'tersuave', 'sintetico', 'esmalte'],
        'aislante': ['aislante', 'aislacion', 'lana', 'rollo', 'isolant']
    }
    
    selected_rubros = set()
    for rubro_key, words in keywords.items():
        if any(word in prompt_lower for word in words):
            selected_rubros.add(rubro_key)

    if selected_rubros:
        try:
            if 'Rubro' in df_data.columns:
                mask = df_data['Rubro'].astype(str).str.lower().apply(lambda x: any(r in x for r in selected_rubros))
                df_filtered = df_data[mask]
                if not df_filtered.empty:
                    return df_filtered.to_string(index=False)
        except Exception:
            pass 
            
    # Fallback: envía todo el contexto si no hay coincidencia clara o falla el filtro
    return df_data.to_string(index=False)


# 3. DEFINICIÓN DEL PROMPT (V95 - LÓGICA COMERCIAL)
# Se define AQUI antes de inicializar el chat para evitar NameErrors.

if data_failure:
    # Modo Fallo: Solo captura datos
    sys_prompt = """Eres Lucho. El sistema de precios falló.
    TU ÚNICO OBJETIVO: Disculparte y pedir Nombre y Teléfono para que un vendedor llame urgente.
    Al tener los datos, genera el bloque [TEXTO_WHATSAPP]: con los datos del cliente."""
else:
    # Modo V95 Completo
    sys_prompt = f"""
ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es obtener el CLICK del cliente en el enlace de WhatsApp para enviar la orden.

BASE DE DATOS Y BÚSQUEDA:
[CONTEXTO_DINAMICO_AQUI] (Se inyectará en cada turno).
**INSTRUCCIÓN DE BARRIDO:** Tu prioridad es vender. Revisa EXHAUSTIVAMENTE el listado disponible. Si el producto está en la lista, TIENES que ofrecerlo. Producto que no se muestra, no se vende.

PSICOLOGÍA DE VENTA (BENEFICIOS Y URGENCIA):
* **NO NEGOCIES, OTORGA:** Tú no "bajas precios". Tú "aplicas bonificaciones por volumen" o "destrabas beneficios".
* **GENERAR URGENCIA:** Usa frases sutiles para inducir el cierre AHORA: *"Te recomiendo reservar esto hoy para congelar el precio"*, *"El stock de esto rota muy rápido"*, *"Cerremos la orden para asegurarte la entrega en la próxima salida"*.
* **EL VOLUMEN ES LA LLAVE:** Antes de dar el precio, pregunta la cantidad sugiriendo una oportunidad: *"Decime qué cantidad necesitás, así veo si puedo activarte la tarifa mayorista o algún beneficio de acopio."*

DICCIONARIO TÉCNICO Y LOGICA DE PRODUCTO:
* **PRECIOS E IVA:** Los precios base son NETOS. Multiplica SIEMPRE por 1.21.
* **AISLANTES (Venta Técnica):**
    * Precio bajo en CSV = $m^2$. Precio alto = Rollo cerrado. (Verifica cobertura en descripción).
    * **Asesoramiento UV:** Si el cliente menciona "cochera", "galería abierta" o "semicubierto" (luz solar directa/indirecta) y NO va a poner cielorraso, RECOMIENDA **"Isolant Doble Aluminio"**. Explicación: *"Para que la espuma no se degrade con el sol, te conviene que quede la cara de aluminio a la vista."*
* **CHAPAS Y PACKS (Cross-Sell Obligatorio):**
    * Techo -> Ofrece: Aislante + Tornillos 14x2 + Perfiles C + Cumbreras + Cenefas.
    * **Hoja Lisa (Para plegados):** Si lleva Techo Cincalum/Plateado -> Ofrece Lisa **Cod 10**. Si lleva Negra -> Ofrece Lisa **Cod 71**. (Busca la equivalente siempre).
* **SIDERÚRGICA:**
    * Perfiles/Tubos -> Ofrece: Electrodos, discos, guantes, pintura.

MANEJO DE "NO LISTADO":
Si no está en el CSV, genera un enlace directo: "Ese producto lo valido en depósito. Consultalo acá:" seguido del link markdown: `[👉 Consultar Stock WhatsApp](https://wa.me/5493401648118?text=Busco%20precio%20de%20este%20producto%20no%20listado...)`.

PROTOCOLO DE CIERRE Y LOGÍSTICA (EL EMBUDO):
1. **Validación:** *"¿Cómo lo ves {{Nombre}}? ¿Te preparo la reserva para asegurar el stock?"*
2. **Logística (Beneficio VIP):** Una vez confirmado el pedido (SOLO AL FINAL): *"¿Preferís retirar o te lo enviamos? (Pasame tu dirección para ver si te bonificamos el envío)."* (No pongas mapas, solo pregunta).
3. **OBTENCIÓN DE DATOS (El Click es Prioridad):**
    * Pide: Nombre, CUIT/DNI y Teléfono.
    * **MANEJO DE DATOS IMPERFECTOS:** Si el cliente pasa un DNI raro o un teléfono incompleto, **NO LO FRENES**. Acepta el dato y genera el Link de WhatsApp igual.
    * En el Texto Oculto para el vendedor, marca el dato dudoso con `(VERIFICAR)`.
    * **TU OBJETIVO ES QUE EL CLIENTE HAGA CLICK EN EL ENLACE.**

**FORMATO FINAL OBLIGATORIO (TEXTO OCULTO):**
Solo cuando el cliente confirma compra y da sus datos, cierra con este bloque exacto al final:
[TEXTO_WHATSAPP]:
Hola, soy {{Nombre}}. Quiero reservar:
- [Listado Productos con Precios Reales]
- [Totales]
Datos Cliente:
- DNI/CUIT: {{DNI}}
- Tel: {{Teléfono}}
- Entrega: {{Retiro/Envío}}

(NO uses etiquetas internas como 'Ticket:', 'Lógica:', etc. en el chat visible).
"""

# 4. INICIALIZACIÓN DE SESIÓN Y MODELO

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas tardes. Soy Lucho. ¿Qué proyecto tenés hoy?"}]
if "suggestions_shown" not in st.session_state:
    st.session_state.suggestions_shown = False

if "chat_session" not in st.session_state:
    try:
        # Se usa Gemini 2.5 para mejor razonamiento lógico
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_prompt)
        
        initial_history = []
        # Reconstruir historia si existe (excepto el saludo inicial hardcodeado)
        if len(st.session_state.messages) > 1:
            for m in st.session_state.messages[1:]: 
                api_role = "model" if m["role"] == "assistant" else "user"
                initial_history.append({"role": api_role, "parts": [{"text": m["content"]}]})
            
        st.session_state.chat_session = model.start_chat(history=initial_history)
        
    except Exception as e:
        st.error(f"❌ Error al inicializar el modelo/chat: {e}")


# 5. INTERFAZ GRÁFICA

st.title("🏗️ Hablá con Lucho")
st.markdown("**Atención Comercial | Pedro Bravin**")

# Renderizar historial
for msg in st.session_state.messages:
    avatar = "🧑‍💼" if msg["role"] == "assistant" else "user" 
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# Sugerencias (Solo al inicio)
if len(st.session_state.messages) == 1 and not st.session_state.suggestions_shown:
    suggestions_text = [
        "**Cotizar Techo** (ej. 'Quiero cotizar chapa para un techo de 8x5.')",
        "**Materiales Cerco** (ej. 'Necesito material para cercar 50 metros.')",
        "**Perfiles y Hierro** (ej. 'Busco perfil C galvanizado.')"
    ]
    with st.chat_message("assistant"):
        st.markdown("***Opciones rápidas:***")
        for tip in suggestions_text:
            st.markdown(f"* {tip}")
    st.session_state.suggestions_shown = True 

# 6. LÓGICA DE PROCESAMIENTO
if prompt := st.chat_input("Escribe tu consulta..."):
    # Guardar input usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    try:
        if "chat_session" not in st.session_state:
             st.error("Error de sesión. Recarga la página.")
             st.stop()
                 
        chat = st.session_state.chat_session
        
        # INYECCIÓN DE CONTEXTO
        if not data_failure and "df_data" in st.session_state:
            filtered_context = filter_data_by_prompt(prompt, st.session_state.df_data)
            full_gemini_prompt = f"Consulta del cliente: {prompt}\n\n[CONTEXTO_DINAMICO_AQUI]:\n{filtered_context}"
        else:
            full_gemini_prompt = prompt 
            
        with st.chat_message("assistant", avatar="🧑‍💼"):
            with st.spinner("Lucho está calculando..."):
                response = chat.send_message(full_gemini_prompt)
            
            final_response_text = response.text
            
            # PARSEO DEL HANDOFF A WHATSAPP
            WHATSAPP_TAG = "[TEXTO_WHATSAPP]:"
            
            if WHATSAPP_TAG in final_response_text:
                dialogue_part, whatsapp_part = final_response_text.split(WHATSAPP_TAG, 1)
                
                # Mostrar diálogo normal
                st.markdown(dialogue_part.strip())
                
                # Procesar link
                whatsapp_text = whatsapp_part.strip()
                encoded_text = urllib.parse.quote(whatsapp_text)
                whatsapp_url = f"https://wa.me/5493401648118?text={encoded_text}"
                
                whatsapp_button = f"""
---
✅ **PEDIDO LISTO PARA ENVIAR**

[👉 **CONFIRMAR PEDIDO POR WHATSAPP AHORA**]({whatsapp_url})

*Al hacer clic, se abrirá tu WhatsApp con el detalle para el vendedor.*
"""
                st.markdown(whatsapp_button)
                
                # Guardar en historial con el link visible
                final_response_for_history = dialogue_part.strip() + "\n" + whatsapp_button
            else:
                st.markdown(final_response_text)
                final_response_for_history = final_response_text
                
        st.session_state.messages.append({"role": "assistant", "content": final_response_for_history})

    except Exception as e:
        st.error(f"Error de comunicación: {e}")
