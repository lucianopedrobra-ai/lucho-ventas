import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucho | Pedro Bravin", page_icon="🏗️", layout="centered")

# 1. AUTENTICACIÓN
try:
    # Intenta obtener la API key de los secretos de Streamlit
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    # Si la clave no se encuentra, muestra un error y detiene la ejecución
    st.error("🚨 Error: Falta la API Key 'GOOGLE_API_KEY' en los Secrets de Streamlit.")
    st.stop()
except Exception as e:
    # Maneja otros errores de configuración
    st.error(f"🚨 Error de configuración de Gemini: {e}")
    st.stop()

# 2. CARGA DE DATOS
# URL para la hoja de cálculo de Google Sheet en formato CSV
# ¡CORREGIDA! Ahora usando el enlace más reciente proporcionado por el usuario.
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

@st.cache_data(ttl=600)
def load_data():
    """Carga los datos desde la URL de la hoja de cálculo y los convierte a string."""
    try:
        # Intenta leer el CSV
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        # Convierte el DataFrame a una cadena de texto sin el índice para usar como contexto
        return df.to_string(index=False)
    except Exception as e:
        # Manejo de errores de carga de datos
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg:
            st.error(
                f"🚨 Error 404 (Not Found) al cargar datos: El link en SHEET_URL es incorrecto o la hoja de cálculo NO está publicada 'al público' como archivo CSV. "
                f"Vaya a 'Archivo > Compartir > Publicar en la web', seleccione el formato '.csv' y reemplace el link en la variable SHEET_URL."
            )
        else:
            st.error(f"Error inesperado leyendo la lista de productos: {e}")
        return "Error leyendo lista."

csv_context = load_data()

# 3. EL CEREBRO (PROMPT V72 - Actualizado con ROL detallado)
sys_prompt = f"""
ROL Y PERSONA: Eres Lucho, Ejecutivo Comercial Senior. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO. Tu objetivo es cotizar rápido y derivar al humano.
UBICACIÓN DE RETIRO: El Trébol, Santa Fe. (Asume que el punto de retiro es central en esta localidad).
BASE DE DATOS DE PRECIOS: {csv_context}

REGLAS DE INTERACCIÓN:
1. Saludo: Inicia con "Hola, buenas tardes."
2. Proactividad: Pregunta "¿Qué proyecto tenés? ¿Techado, rejas, pintura o construcción?"
3. CANDADO DE DATOS (PRE-COTIZACIÓN): Antes de dar el precio final, pregunta: "Para confirmarte si tenés Envío Gratis, decime: ¿Tu Nombre y de qué Localidad sos?"
4. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden".

DICCIONARIO TÉCNICO Y MATEMÁTICA (RAG):
* IVA: Precios en la BASE DE DATOS son NETOS. MULTIPLICA SIEMPRE POR 1.21.
* AISLANTES: <$10k (x M2) | >$10k (x Rollo).
* TUBOS: Epoxi/Galva/Schedule (x 6.40m) | Estructural (x 6.00m).
* PLANCHUELAS: Precio por UNIDAD (Barra).

PROTOCOLO DE VENTA POR RUBRO:
* TEJIDOS: No uses "Kit". Cotiza item por item: 1. Tejido, 2. Alambre Tensión, 3. Planchuelas, 4. Accesorios.
* CHAPAS: Filtro Techo vs Lisa. Aislación consultiva. Acopio "Bolsa de Metros". Estructura.
* REJA/CONSTRUCCIÓN: Cotiza material. Muestra diagrama ASCII si es reja.
* NO LISTADOS: Si no está en BASE DE DATOS, fuerza handoff: "Consulto stock en depósito".

PROTOCOLO DE CROSS-SELL (SUGERENCIA DE ÍTEMS):
* Preguntas RÁPIDAS al cerrar: "¿Electrodos o alambre?", "¿Discos?", "Para proteger, te sugiero [Fondo/Aerosol]. ¿Lo agrego?"

MATRIZ DE NEGOCIACIÓN, FINANCIACIÓN Y LOGÍSTICA:
* ENVÍO SIN CARGO (ZONA): El Trébol, María Susana, Piamonte, Landeta, San Jorge, Sastre, C. Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
* DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% General) | >$2M (14%).
* MEGA-VOLUMEN (> $10M): Muestra Ticket BASE. Deriva a Martín Zimaro (3401 52-7780).
* FINANCIACIÓN: Transferencia/MP. Local: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado: "+3% EXTRA".

FORMATO Y CIERRE:
* TICKET (DESGLOSE REAL): Usa bloques de código ```text. Lista cada producto por separado con su CÓDIGO y PRECIO UNITARIO real (del CSV). Nunca agrupes.
* FASE DE VALIDACIÓN: "¿Cómo lo ves [Nombre]? ¿Cerramos así o ajustamos algo?"
* PROTOCOLO DE CIERRE (COMBO FINAL):
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
# Agregamos una imagen representativa para Lucho
# NOTA: Reemplace esta URL con la URL pública de la imagen de Lucho.
# ¡CORRECCIÓN CLAVE AQUÍ! Se eliminó la sintaxis Markdown.
LUCHO_IMAGE_URL = "[https://placehold.co/120x120/4B0082/ffffff?text=Lucho+Exec](https://placehold.co/120x120/4B0082/ffffff?text=Lucho+Exec)" 
st.image(LUCHO_IMAGE_URL, width=120) 
st.markdown("**Atención Comercial | Pedro Bravin**")

# Inicializa el historial de mensajes
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy?"}]

# Muestra los mensajes anteriores en el chat
for msg in st.session_state.messages:
    # Mapea el rol de la API a la función de mensaje de Streamlit
    role = "assistant" if msg["role"] == "model" else msg["role"]
    st.chat_message(role).write(msg["content"])

# Captura la entrada del usuario
if prompt := st.chat_input():
    # Muestra el mensaje del usuario
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # Usamos el identificador del modelo gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025', system_instruction=sys_prompt)
        
        # Prepara el historial para la API
        history = [
            {"role": "model" if m["role"] == "assistant" else m["role"], "parts": [{"text": m["content"]}]}
            for m in st.session_state.messages if m["role"] != "system"
        ]
        
        # Inicia el chat con el historial
        chat = model.start_chat(history=history)
        
        # Envía el mensaje y espera la respuesta
        response = chat.send_message(prompt)
        
        # Muestra la respuesta y la guarda en el estado de sesión
        st.chat_message("assistant").write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        # Manejo de errores
        st.error(f"❌ Error en la llamada a la API de Gemini: {e}")
        if "404" in str(e) or "not found" in str(e).lower():
            # Consejo para el usuario en caso de error 404
            st.info("💡 Consejo: El nombre del modelo puede ser incorrecto o su clave API no tiene acceso. Intente usar un alias diferente o crear una nueva clave.")
