import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- CONFIGURACIÓN ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

def configure_genai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception:
        st.error("🚨 Error: Falta la API KEY en los Secrets.")
        st.stop()

@st.cache_data(ttl=600)
def fetch_pricing_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        if len(df.columns) > 6:
             df_opt = df.iloc[:, [2, 3, 4, 6]].copy()
             df_opt.columns = ['CODIGO', 'DESCRIPCION', 'UNIDAD', 'PRECIO_LISTA']
             return df_opt.to_string(index=False)
        return df.to_string(index=False)
    except Exception as e:
        return f"Error leyendo CSV: {e}"

def get_system_instruction(context_data):
    return f"""
    ROL: Asistente Comercial Senior "Lucho".
    BASE DE DATOS: {context_data}
    
    REGLAS:
    1. IVA: Precios CSV son NETOS. MULTIPLICA SIEMPRE POR 1.21.
    2. SEGURIDAD: Valida CANTIDAD antes de cotizar.
    3. DATOS: Pide Nombre y Localidad antes del precio.
    4. LÍMITE: Solo reservas pedidos.

    PROTOCOLOS:
    - TUBOS: 6.40m (Conducción) / 6.00m (Estructura).
    - CHAPAS: Techo/Lisa. Aislante consultivo. Acopio.
    - TEJIDOS: Kit Completo. Eco -> Acindar.
    - REJA: Macizo vs Estructural. ASCII.
    - CONSTRUCCIÓN: Hierro ADN vs Liso. Upsell.

    MATRIZ COMERCIAL:
    - ENVÍO GRATIS: Zona El Trébol, San Jorge, Sastre, etc.
    - DESCUENTOS: >150k (7% Chapa) | >500k (7% Gral) | >2M (14%).
    - MEGA (>10M): Precio Base -> Derivar a Martín Zimaro (3401 52-7780).
    - FINANCIACIÓN: Promo FirstData (Mié/Sáb). Contado +3%.

    CIERRE:
    1. Pedir: Nombre, CUIT, Teléfono.
    2. Link WhatsApp con resumen.
    """

def get_working_model():
    """Prueba modelos en orden de prioridad hasta encontrar uno que funcione."""
    modelos_a_probar = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    for modelo in modelos_a_probar:
        try:
            # Intentamos crear una instancia simple para ver si el nombre es válido
            test_model = genai.GenerativeModel(modelo)
            return test_model
        except:
            continue
    return None

def main():
    st.title("🏗️ Hablá con Lucho")
    st.markdown("**Atención Comercial | Pedro Bravin**")
    
    configure_genai()
    pricing_data = fetch_pricing_data()
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy? ¿Techado, rejas, pintura o construcción?"}
        ]

    for msg in st.session_state.messages:
        avatar = "👷‍♂️" if msg["role"] == "model" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribí tu consulta..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # INTENTO DE CONEXIÓN CON FALLBACK AUTOMÁTICO
            sys_prompt = get_system_instruction(pricing_data)
            
            # Historial compatible
            chat_history = []
            for m in st.session_state.messages:
                if m["role"] != "system":
                    role = "user" if m["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [m["content"]]})

            # Probamos modelos en cascada
            modelos = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
            response_text = None
            last_error = ""

            for modelo_nombre in modelos:
                try:
                    model = genai.GenerativeModel(model_name=modelo_nombre, system_instruction=sys_prompt)
                    chat = model.start_chat(history=chat_history)
                    response = chat.send_message(prompt)
                    response_text = response.text
                    break # Si funcionó, salimos del bucle
                except Exception as e:
                    last_error = str(e)
                    continue # Si falló, probamos el siguiente

            if response_text:
                with st.chat_message("model", avatar="👷‍♂️"):
                    st.markdown(response_text)
                st.session_state.messages.append({"role": "model", "content": response_text})
            else:
                st.error(f"❌ No se pudo conectar con ningún modelo de Google. Error: {last_error}")
                st.info("Verifica tu API Key y el acceso a modelos en Google AI Studio.")

        except Exception as e:
            st.error(f"❌ Error inesperado: {str(e)}")

if __name__ == "__main__":
    main()
