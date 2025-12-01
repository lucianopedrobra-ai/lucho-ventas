import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DEL ENTORNO ---
PAGE_CONFIG = {"page_title": "Lucho | Asesor Comercial", "page_icon": "🏗️", "layout": "centered"}
MODEL_ID = "gemini-1.5-pro"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(**PAGE_CONFIG)

def get_credentials():
    """Recupera credenciales de forma segura."""
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except KeyError:
        st.error("Error crítico: Credenciales no configuradas en el entorno.")
        st.stop()

@st.cache_data(ttl=600, show_spinner=False)
def fetch_pricing_data():
    """Obtiene y procesa la lista de precios en tiempo real."""
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except Exception as e:
        return f"Error de conexión con base de datos: {e}"

def build_system_prompt(context_data):
    """Genera la lógica de negocio del agente."""
    return f"""
    ROL: Asistente Comercial Senior "Lucho". Perfil técnico, conciso y orientado al cierre.
    
    BASE DE DATOS (PRECIOS ACTUALIZADOS):
    {context_data}

    DIRECTRICES OPERATIVAS:
    1. PRECIOS: Los valores del CSV son NETOS. Calcular siempre precio final (x1.21 IVA).
    2. SEGURIDAD: Validar CANTIDAD antes de cotizar.
    3. DATOS: Solicitar Nombre y Localidad antes del precio final para validar logística.
    4. ALCANCE: Reservar pedidos, no emitir facturas fiscales.

    REGLAS DE PRODUCTO (RAG):
    - TUBOS: Cotizar tira completa (Conducción 6.40m / Estructural 6.00m).
    - PLANCHUELAS: Unidad barra.
    - AISLANTES: <$10k cotizar por m2 (calc. rollo) | >$10k cotizar por rollo.

    PROTOCOLOS DE VENTA:
    - CHAPAS: Filtrar uso (Techo/Lisa). Sugerir aislante Doble Alu 10mm en semicubiertos. Ofrecer acopio "Bolsa de Metros".
    - TEJIDOS: Ofrecer Kit completo (Postes Tubo + Accesorios). Estrategia Eco -> Acindar.
    - REJA: Diagrama ASCII visual. Cotizar Macizo vs Estructural.
    - CONSTRUCCIÓN: Hierro ADN. Alertar si pide 4.2mm (no estructural). Upsell: Alambre/Clavos.
    - NO CATALOGADO: Derivar a consulta de stock física.

    MATRIZ COMERCIAL:
    - LOGÍSTICA: Envío bonificado en zona de influencia (El Trébol, San Jorge, etc.).
    - BONIFICACIONES: >$150k (7% Chapa) | >$500k (7% Gral) | >$2M (14%).
    - GRANDES CUENTAS (>10M): Presentar precio base y derivar a Gerencia (Martín Zimaro).
    - PAGOS: Promo FirstData (Mié/Sáb). Contado +3% extra. Tarjetas solo presencial.

    FORMATO DE RESPUESTA:
    - TICKET: Bloque de código ```text con desglose, códigos SKU y P.Unit.
    - CIERRE: Solicitar Nombre, CUIT, Teléfono. Generar Link WhatsApp (Markdown).
    """

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy? ¿Techado, rejas, pintura o construcción?"}
        ]

def render_chat():
    for msg in st.session_state.messages:
        avatar = "👷‍♂️" if msg["role"] == "model" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

def main():
    st.title("🏗️ Hablá con Lucho")
    st.markdown("**Atención Comercial | Acindar Pymes**")
    
    api_key = get_credentials()
    client = genai.Client(api_key=api_key)
    pricing_data = fetch_pricing_data()
    
    init_session()
    render_chat()

    if prompt := st.chat_input("Escribí tu consulta..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            sys_instruct = build_system_prompt(pricing_data)
            
            # Construcción del historial para la API
            api_history = [
                types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

            # Inferencia
            chat_session = client.chats.create(
                model=MODEL_ID,
                config=types.GenerateContentConfig(system_instruction=sys_instruct),
                history=api_history
            )
            response = chat_session.send_message(prompt)
            
            with st.chat_message("model", avatar="👷‍♂️"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})

        except Exception as e:
            # Fallback silencioso a modelo Flash si Pro falla o manejo de error genérico
            if "404" in str(e) or "429" in str(e):
                st.warning("Nota: Optimizando respuesta con modelo de alta velocidad...")
                try:
                    chat_session = client.chats.create(
                        model="gemini-1.5-flash",
                        config=types.GenerateContentConfig(system_instruction=sys_instruct),
                        history=api_history
                    )
                    response = chat_session.send_message(prompt)
                    with st.chat_message("model", avatar="👷‍♂️"):
                        st.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                except:
                    st.error("Servicio momentáneamente no disponible. Por favor intente más tarde.")
            else:
                st.error(f"Error de conexión: {str(e)}")

if __name__ == "__main__":
    main()
