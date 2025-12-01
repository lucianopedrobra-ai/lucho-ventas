import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import time

# --- CONSTANTES DE CONFIGURACIÓN ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"
# URL pública del CSV publicado en Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

def get_api_key():
    """Recupera la API Key de los secretos de Streamlit de forma segura."""
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except (FileNotFoundError, KeyError):
        st.error("Error de configuración: API Key no encontrada en secrets.")
        st.stop()

@st.cache_data(ttl=600)
def load_data():
    """Carga, limpia y optimiza la base de datos de precios."""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        
        # Optimización: Filtrar columnas irrelevantes para ahorrar tokens
        # Se asume estructura: [Rubro, Subrubro, CÓDIGO, DESCRIPCIÓN, UNIDAD, P.BASE, P.ALT, Moneda]
        # Índices clave: 2 (Código), 3 (Descripción), 4 (Unidad), 6 (Precio Alt/Venta)
        if len(df.columns) > 6:
            df_opt = df.iloc[:, [2, 3, 4, 6]].copy()
            df_opt.columns = ['CODIGO', 'DESCRIPCION', 'UNIDAD', 'PRECIO_LISTA']
            return df_opt.to_string(index=False)
        return df.to_string(index=False)
        
    except Exception as e:
        return f"Error al cargar datos: {str(e)}"

def get_system_prompt(context):
    """Genera las instrucciones del sistema con el contexto de datos actual."""
    return f"""
    ROL: Eres Lucho, Ejecutivo Comercial Senior. Tu perfil es técnico, experto y EXTREMADAMENTE CONCISO.
    OBJETIVO: Cotizar rápido, realizar venta consultiva (Upsell) y cerrar la operación derivando a WhatsApp.

    BASE DE DATOS ACTUALIZADA:
    {context}

    REGLAS OPERATIVAS:
    1. IVA: Los precios de lista son NETOS. Debes MULTIPLICAR POR 1.21 para dar el precio final.
    2. SEGURIDAD: Nunca des precios sin saber la CANTIDAD (evita errores de escala).
    3. SALUDO: Corto y profesional ("Hola, buenas.").
    4. DATOS DE CONTACTO: Antes del precio final, solicita Nombre y Localidad para validar envío.

    LOGICA TÉCNICA (RAG):
    - TUBOS: Conducción (Epoxi/Galva/Schedule) se venden por tira de 6.40m. Estructurales por tira de 6.00m.
    - PLANCHUELAS: Precio por unidad (barra).
    - AISLANTES: Si precio < $10k es x m2 (calcular por rollo). Si > $10k es x rollo cerrado.

    PROTOCOLOS DE VENTA:
    - CHAPAS: Filtra uso (Techo vs Lisa). Si es techo, sugiere aislante (Doble Alu 10mm para semicubierto). Ofrece acopio si no hay medidas.
    - TEJIDOS: Ofrece Kit Completo. Estrategia de menor (Eco) a mayor (Acindar).
    - CONSTRUCCIÓN: Hierro ADN vs Liso. Alerta sobre hierro 4.2mm (fuera de norma).
    - NO LISTADOS: Si el producto no figura en DB, deriva a consulta de stock física.

    MATRIZ COMERCIAL:
    - ENVÍO SIN CARGO: Zona El Trébol, San Jorge, Sastre, etc.
    - DESCUENTOS: >$150k (7% Chapa/Hierro) | >$500k (7% Gral) | >$2M (14%).
    - MEGA-CUENTAS (>10M): Muestra precio base y deriva a Gerencia (Martín Zimaro).
    - FINANCIACIÓN: Promo FirstData (Mié/Sáb 3 cuotas s/int). Contado +3% extra.

    CIERRE Y FORMATO:
    1. Pedir: Nombre, CUIT/DNI, Teléfono.
    2. Link WhatsApp: Generar link con mensaje pre-cargado.
       [✅ ENVIAR PEDIDO CONFIRMADO](LINK)
       "📍 Retiro: [LINK_MAPS]"
    """

def main():
    # Inicialización
    st.title("🏗️ Hablá con Lucho")
    st.markdown("**Atención Comercial | Acindar Pymes**")
    
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    csv_context = load_data()

    # Gestión de Sesión
    if "messages" not in st.session_state:
        st.session_state.messages = []
        welcome_msg = "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy? ¿Techado, rejas, pintura o construcción?"
        st.session_state.messages.append({"role": "model", "content": welcome_msg})

    # Renderizar Chat
    for message in st.session_state.messages:
        avatar = "👷‍♂️" if message["role"] == "model" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Lógica de Interacción
    if prompt := st.chat_input("Escribí acá..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Preparar historial
            historial_gemini = [
                types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

            # Configuración del Modelo (1.5 Flash para velocidad/costo)
            sys_instruct = get_system_prompt(csv_context)
            chat = client.chats.create(
                model="gemini-1.5-flash",
                config=types.GenerateContentConfig(system_instruction=sys_instruct),
                history=historial_gemini
            )
            
            response = chat.send_message(prompt)
            text_response = response.text

            with st.chat_message("model", avatar="👷‍♂️"):
                st.markdown(text_response)
            st.session_state.messages.append({"role": "model", "content": text_response})

        except Exception as e:
            error_msg = f"⚠️ Hubo un error de conexión momentáneo. Por favor intentá de nuevo. ({str(e)})"
            if "429" in str(e):
                error_msg = "🚧 Estamos recibiendo muchas consultas. Por favor, aguardá unos segundos y volvé a preguntar."
            st.error(error_msg)

if __name__ == "__main__":
    main()
