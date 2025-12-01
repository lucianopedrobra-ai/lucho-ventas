import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# --- CONFIGURACIÓN ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"

# CAMBIO FINAL: Usamos 'flash' directo. Es el más rápido y estable.
MODEL_ID = "gemini-1.5-flash" 

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
            # Configuración del Modelo
            sys_prompt = get_system_instruction(pricing_data)
            model = genai.GenerativeModel(
                model_name=MODEL_ID,
                system_instruction=sys_prompt
            )
            
            # Historial
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
            st.error(f"❌ Error Técnico: {str(e)}")
            if "429" in str(e):
                st.warning("⏳ Tráfico alto. Por favor esperá unos segundos.")

if __name__ == "__main__":
    main()
