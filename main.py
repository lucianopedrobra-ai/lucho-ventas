import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURACIÓN ---
PAGE_TITLE = "Lucho | Asesor Comercial"
PAGE_ICON = "🏗️"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgHzHMiNP9jH7vBAkpYiIVCzUaFbNKLC8_R9ZpwIbgMc7suQMR7yActsCdkww1VxtgBHcXOv4EGvXj/pub?gid=1937732333&single=true&output=csv"

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

def get_credentials():
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
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

def build_system_prompt(context_data):
    return f"""
    ROL: Asistente Comercial Senior "Lucho". Perfil técnico y conciso.
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

    PROTOCOLOS:
    - CHAPAS: Filtro Techo/Lisa. Sugerir aislante Doble Alu 10mm (semicubierto). Acopio "Bolsa de Metros".
    - TEJIDOS: Kit completo. Eco -> Acindar.
    - REJA: Diagrama ASCII. Macizo vs Estructural.
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
    
    api_key = get_credentials()
    
    if not api_key:
        st.error("🚨 ERROR: Falta la API Key en los Secrets de Streamlit.")
        st.stop()

    client = genai.Client(api_key=api_key)
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
            sys_instruct = build_system_prompt(pricing_data)
            
            api_history = [
                types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

            # --- INTENTO 1: GEMINI 1.5 PRO (EL MEJOR) ---
            try:
                chat_session = client.chats.create(
                    model="gemini-1.5-pro",
                    config=types.GenerateContentConfig(system_instruction=sys_instruct),
                    history=api_history
                )
                response = chat_session.send_message(prompt)
            
            except Exception as e:
                # SI FALLA EL PRO, INTENTAMOS CON FLASH AUTOMÁTICAMENTE
                print(f"Fallo Pro: {e}. Intentando Flash.")
                chat_session = client.chats.create(
                    model="gemini-1.5-flash",
                    config=types.GenerateContentConfig(system_instruction=sys_instruct),
                    history=api_history
                )
                response = chat_session.send_message(prompt)

            with st.chat_message("model", avatar="👷‍♂️"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})

        except Exception as e:
            st.error(f"❌ Error Técnico: {str(e)}")
            st.info("Verifica que tu API Key tenga habilitada la facturación en Google Cloud Console.")

if __name__ == "__main__":
    main()
