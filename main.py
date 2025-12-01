import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DEL ENTORNO ---
# ACÁ CAMBIAMOS EL NOMBRE QUE APARECE EN LA PESTAÑA DEL NAVEGADOR
PAGE_CONFIG = {"page_title": "Lucho | Pedro Bravin", "page_icon": "🏗️", "layout": "centered"}
MODEL_ID = "gemini-1.5-pro"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(**PAGE_CONFIG)

def get_credentials():
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except KeyError:
        st.error("Error crítico: Credenciales no configuradas.")
        st.stop()

@st.cache_data(ttl=600, show_spinner=False)
def fetch_pricing_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except Exception as e:
        return f"Error de conexión: {e}"

def build_system_prompt(context_data):
    return f"""
    ROL: Asistente Comercial Senior "Lucho". Perfil técnico y orientado al cierre.
    EMPRESA: Pedro Bravin Materiales.
    
    BASE DE DATOS:
    {context_data}

    DIRECTRICES:
    1. PRECIOS: Los valores CSV son NETOS. Calcular SIEMPRE precio final (x1.21 IVA).
    2. SEGURIDAD: Validar CANTIDAD antes de cotizar.
    3. DATOS: Solicitar Nombre y Localidad para validar envío.
    4. ALCANCE: Reservar pedidos, no emitir facturas.

    REGLAS TÉCNICAS (RAG):
    - TUBOS: Conducción 6.40m / Estructural 6.00m.
    - PLANCHUELAS: Unidad barra.
    - AISLANTES: <$10k x m2 | >$10k x rollo.

    PROTOCOLOS:
    - CHAPAS: Filtro Techo/Lisa. Sugerir aislante Doble Alu 10mm (semicubierto). Acopio "Bolsa de Metros".
    - TEJIDOS: Kit completo. Eco -> Acindar.
    - REJA: Diagrama ASCII. Macizo vs Estructural.
    - CONSTRUCCIÓN: Hierro ADN vs Liso. Alerta 4.2mm. Upsell Alambre/Clavos.
    - NO CATALOGADO: Derivar a consulta de stock física.

    MATRIZ COMERCIAL:
    - LOGÍSTICA: Envío bonificado en zona de influencia (El Trébol, San Jorge, etc.).
    - BONIFICACIONES: >$150k (7% Chapa) | >$500k (7% Gral) | >$2M (14%).
    - GRANDES CUENTAS (>10M): Precio base -> Derivar a Gerencia (Martín Zimaro).
    - PAGOS: Promo FirstData (Mié/Sáb). Contado +3%. Tarjetas solo presencial.

    FORMATO:
    - TICKET: Bloque ```text con desglose.
    - CIERRE: Solicitar Nombre, CUIT, Teléfono. Generar Link WhatsApp.
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
    # ACÁ CAMBIAMOS EL TÍTULO GRANDE DEL CHAT
    st.title("🏗️ Hablá con Lucho")
    st.markdown("**Atención Comercial | Pedro Bravin**")
    
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
            
            api_history = [
                types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

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
            # Manejo de errores con fallback
            if "404" in str(e) or "429" in str(e):
                st.warning("Nota: Optimizando respuesta...")
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
                    st.error("Servicio no disponible momentáneamente.")
            else:
                st.error(f"Error técnico: {str(e)}")

if __name__ == "__main__":
    main()
