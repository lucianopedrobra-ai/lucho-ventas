import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DE CONSTANTES ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

def get_api_key():
    """Recupera la API Key de forma segura desde los secretos de Streamlit."""
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except (FileNotFoundError, KeyError):
        st.error("Error de Configuración: No se encontró la API KEY en los secretos.")
        st.stop()

@st.cache_data(ttl=600)
def load_pricing_data(url):
    """Carga y cachea la lista de precios desde Google Sheets."""
    try:
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        return df.to_string()
    except Exception as e:
        return f"Error al cargar base de datos: {str(e)}"

def initialize_chat():
    """Inicializa el historial del chat si no existe."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        initial_msg = "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés en mente hoy? ¿Techado, rejas, pintura o construcción?"
        st.session_state.messages.append({"role": "model", "content": initial_msg})

def main():
    # 1. Configuración Inicial
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    csv_context = load_pricing_data(SHEET_URL)
    
    initialize_chat()

    # 2. Definición del System Prompt (Lógica de Negocio V72.0)
    system_instruction = f"""
    ROL: Eres Lucho, Ejecutivo Comercial Senior. Experto en materiales. Tu tono es profesional, cercano y EXTREMADAMENTE CONCISO.
    OBJETIVO: Cotizar rápido, maximizar el ticket promedio y derivar la venta a WhatsApp.

    BASE DE DATOS (LISTA DE PRECIOS):
    {csv_context}

    REGLAS DE INTERACCIÓN:
    1. PROACTIVIDAD: Al inicio, identifica el proyecto (Techo, Reja, Pintura, Obra).
    2. CANDADO DE DATOS: Antes de dar un precio final, pregunta: "Para confirmarte si tenés **Envío Gratis**, decime: **¿Tu Nombre y de qué Localidad sos?**".
    3. LÍMITE ADMINISTRATIVO: Tú solo "reservas la orden", no facturas ni cobras.
    4. NO-STALL: Si el cliente no responde, repregunta para cerrar.

    LÓGICA TÉCNICA Y MATEMÁTICA (RAG):
    * IVA: Los precios del CSV son NETOS. MULTIPLICA SIEMPRE POR 1.21 para el precio final.
    * TUBOS: 
        - Epoxi/Galva/Schedule/Mecánico: Precio Metro x 6.40.
        - Estructurales: Precio Metro x 6.00.
    * PLANCHUELAS: El precio es por UNIDAD (Barra).
    * AISLANTES: Si precio < $10k es x M2. Si > $10k es x Rollo.

    PROTOCOLOS DE VENTA:
    * TEJIDOS (KIT): Cotiza Sistema (Rollos + Postes Tubo Estructural + Accesorios). Estrategia Menor a Mayor (Eco -> Acindar).
    * CHAPAS (PACK TECHO): Filtro Techo vs Lisa. Aislación Consultiva (Doble Alu 10mm para Semicubierto). Acopio "Bolsa de Metros".
    * REJA: Cotiza Macizo vs Estructural. Muestra diagrama ASCII simple.
    * CONSTRUCCIÓN: Hierro ADN vs Liso. Alerta si pide 4.2mm (Fuera de norma).
    * NO LISTADOS: Si no está en CSV, fuerza handoff: "Consulto stock en depósito".

    CROSS-SELL (PACK METALÚRGICO):
    Preguntas rápidas al cerrar: Soldadura (Electrodos/Alambre), Corte (Discos), Pintura (Fondo/Aerosol), Protección.

    MATRIZ DE NEGOCIACIÓN:
    * ZONA ENVÍO SIN CARGO: El Trébol, María Susana, Piamonte, Landeta, San Jorge, Sastre, C. Pellegrini, Cañada Rosquín, Casas, Las Bandurrias, San Martín de las Escobas, Traill, Centeno, Classon, Los Cardos, Las Rosas, Bouquet, Montes de Oca.
    * DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% General) | >$2M (14%).
    * MEGA-VOLUMEN (> $10M): Muestra Ticket BASE. Deriva a Martín Zimaro (3401 52-7780).
    * FINANCIACIÓN: Promo FirstData (Mié/Sáb 3 Sin Interés). Contado +3% Extra. Tarjetas solo presencial.

    FORMATO DE RESPUESTA:
    * TICKET: Usa bloques de código ```text para precios. Muestra P.Unitario y Código.
    * VALIDACIÓN: "¿Cómo lo ves [Nombre]? ¿Cerramos así o ajustamos algo?"
    * CIERRE:
        1. Pedir: Nombre, CUIT/DNI, Teléfono.
        2. Generar Link WhatsApp (Markdown).
        [✅ ENVIAR PEDIDO CONFIRMADO (WHATSAPP)](LINK)
        "O escribinos al: **3401-648118**"
        "📍 **Retiro:** [LINK_MAPS]"
    """

    # 3. Interfaz de Usuario
    st.title("🏗️ Hablá con Lucho")
    st.caption("Asesoramiento Comercial Online | Acindar Pymes")

    # Renderizar historial
    for message in st.session_state.messages:
        avatar = "👷‍♂️" if message["role"] == "model" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # 4. Lógica de Chat
    if prompt := st.chat_input("Escribí tu consulta..."):
        # Usuario
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Modelo
        try:
            # Preparar historial para la API
            gemini_history = [
                types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

            chat_session = client.chats.create(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(system_instruction=system_instruction),
                history=gemini_history
            )
            
            response = chat_session.send_message(prompt)
            text_response = response.text

            with st.chat_message("model", avatar="👷‍♂️"):
                st.markdown(text_response)
            st.session_state.messages.append({"role": "model", "content": text_response})

        except Exception as e:
            st.error(f"Ocurrió un error de conexión. Por favor intentá de nuevo. Detalles: {e}")

if __name__ == "__main__":
    main()
