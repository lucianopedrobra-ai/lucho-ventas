import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- CONFIGURACIÓN ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"
# USAMOS EL NOMBRE TÉCNICO CORRECTO DEL MODELO MÁS POTENTE ACTUAL
MODEL_ID = "gemini-1.5-pro" 
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

def configure_interface():
    st.title("🏗️ Hablá con Lucho")
    st.markdown("**Atención Comercial | Pedro Bravin**")

def get_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8', on_bad_lines='skip')
        return df.to_string(index=False)
    except:
        return "Error al cargar precios."

def get_system_instruction(context_data):
    return f"""
    ROL: Asistente Comercial Senior "Lucho". Experto técnico y conciso.
    BASE DE DATOS: {context_data}
    
    DIRECTRICES:
    1. PRECIOS: Los valores CSV son NETOS. Calcular SIEMPRE precio final (x1.21 IVA).
    2. SEGURIDAD: Validar CANTIDAD antes de cotizar.
    3. DATOS: Solicitar Nombre y Localidad para validar envío.
    4. ALCANCE: Reservar pedidos, no emitir facturas.

    REGLAS TÉCNICAS:
    - TUBOS: Conducción 6.40m / Estructural 6.00m.
    - PLANCHUELAS: Unidad barra.
    - AISLANTES: <$10k x m2 | >$10k x rollo.

    PROTOCOLOS DE VENTA:
    - CHAPAS: Filtro Techo/Lisa. Sugerir aislante Doble Alu 10mm (semicubierto). Acopio "Bolsa de Metros".
    - TEJIDOS: Kit completo. Eco -> Acindar.
    - REJA: Diagrama ASCII visual. Cotizar Macizo vs Estructural.
    - CONSTRUCCIÓN: Hierro ADN vs Liso. Alerta 4.2mm. Upsell Alambre/Clavos.
    - NO CATALOGADO: Derivar a consulta de stock física.

    MATRIZ COMERCIAL:
    - LOGÍSTICA: Envío bonificado en zona de influencia (El Trébol, San Jorge, etc.).
    - BONIFICACIONES: >$150k (7% Chapa) | >$500k (7% Gral) | >$2M (14%).
    - GRANDES CUENTAS (>10M): Presentar precio base y derivar a Gerencia (Martín Zimaro).
    - PAGOS: Promo FirstData (Mié/Sáb). Contado +3% extra.

    FORMATO:
    - TICKET: Bloque ```text con desglose.
    - CIERRE: Solicitar Nombre, CUIT, Teléfono. Generar Link WhatsApp.
    """

def main():
    configure_interface()
    
    # 1. Autenticación (Manejo de Errores)
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception:
        st.error("🚨 Error: Falta la API KEY en los Secrets de Streamlit.")
        st.stop()

    # 2. Carga de Datos
    csv_context = get_data()

    # 3. Historial
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "model", "content": "Hola, buenas. Soy Lucho. ¿Qué proyecto tenés hoy? ¿Techado, rejas, pintura o construcción?"}
        ]

    for msg in st.session_state.messages:
        avatar = "👷‍♂️" if msg["role"] == "model" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # 4. Chat
    if prompt := st.chat_input("Escribí tu consulta..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Configuración del Modelo PRO
            model = genai.GenerativeModel(
                model_name=MODEL_ID,
                system_instruction=get_system_instruction(csv_context)
            )
            
            # Adaptación del historial para la librería clásica
            chat_history = []
            for m in st.session_state.messages:
                if m["role"] != "system":
                    role = "user" if m["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [m["content"]]})

            chat = model.start_chat(history=chat_history)
            response = chat.send_message(prompt)
            
            with st.chat_message("model", avatar="👷‍♂️"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})

        except Exception as e:
            # Diagnóstico claro
            error_msg = str(e)
            if "404" in error_msg:
                st.error(f"⚠️ Error de Modelo: Google no encuentra '{MODEL_ID}'. Intentando fallback...")
                # Fallback automático a Flash
                try:
                    fallback_model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=get_system_instruction(csv_context))
                    chat = fallback_model.start_chat(history=chat_history)
                    response = chat.send_message(prompt)
                    with st.chat_message("model", avatar="👷‍♂️"):
                        st.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                except:
                    st.error("No se pudo conectar con ningún modelo.")
            elif "429" in error_msg:
                st.warning("⏳ Tráfico alto. Por favor esperá 10 segundos y reintentá.")
            else:
                st.error(f"❌ Error técnico: {error_msg}")

if __name__ == "__main__":
    main()
