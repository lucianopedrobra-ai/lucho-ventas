# funciones.py
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import re
import datetime
import urllib.parse
from bs4 import BeautifulSoup
import os
from config import *

# ==========================================
# MOTOR INVISIBLE (OPTIMIZADO)
# ==========================================
@st.cache_data(ttl=3600)
def obtener_dolar_bna():
    # 1. INTENTO VÍA API (Más rápido y estable)
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=3)
        if r.status_code == 200:
            data = r.json()
            # La API devuelve venta, lo usamos
            return float(data['venta'])
    except:
        pass

    # 2. INTENTO VÍA SCRAPING (Respaldo original)
    url = "https://www.bna.com.ar/Personas"
    backup = 1060.00
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            target = soup.find(string=re.compile("Dolar U.S.A"))
            if target:
                row = target.find_parent('tr')
                cols = row.find_all('td')
                if len(cols) >= 3:
                    return float(cols[2].get_text().replace(',', '.'))
        return backup
    except: return backup

@st.cache_data(ttl=600)
def load_data():
    try: 
        # Carga optimizada: Leemos todo como texto para evitar errores de formato
        return pd.read_csv(SHEET_URL, dtype=str).fillna("").to_csv(index=False)
    except: return ""

def enviar_a_google_form_background(cliente, monto, oportunidad):
    if URL_FORM_GOOGLE:
        try: requests.post(URL_FORM_GOOGLE, data={'entry.xxxxxx': str(cliente), 'entry.xxxxxx': str(monto), 'entry.xxxxxx': str(oportunidad)}, timeout=1)
        except: pass

def log_interaction(user_text, monto):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.log_data.append({"Fecha": ts, "Usuario": user_text[:50], "Monto": monto})

def parsear_ordenes_bot(texto):
    items_nuevos = []
    # Regex robusto para capturar las órdenes del bot
    for cant, prod, precio, tipo in re.findall(r'\[ADD:([\d\.]+):([^:]+):([\d\.]+):([^\]]+)\]', texto):
        try:
            item = {
                "cantidad": float(cant), 
                "producto": prod.strip(), 
                "precio_unit": float(precio), 
                "subtotal": float(cant)*float(precio), 
                "tipo": tipo.strip().upper()
            }
            st.session_state.cart.append(item)
            items_nuevos.append(item)
        except Exception as e:
            pass 
    return items_nuevos

def calcular_negocio():
    try:
        now = datetime.datetime.now()
        tiempo_restante = st.session_state.expiry_time - now
        segundos_restantes = int(tiempo_restante.total_seconds())
        activa = segundos_restantes > 0
        
        if activa:
            m, s = divmod(segundos_restantes, 60)
            reloj_init = f"{m:02d}:{s:02d}"
            color_reloj = "#2e7d32" 
            if m < 2: color_reloj = "#ff9800"
            if m < 1: color_reloj = "#ff0000"
        else:
            reloj_init = "00:00"
            color_reloj = "#b0bec5"

        bruto = sum(i['subtotal'] for i in st.session_state.cart)
        desc_base = 0; desc_extra = 0; nivel_texto = "LISTA"; color = "#546e7a"; meta = META_BASE
        
        tipos = [x['tipo'] for x in st.session_state.cart]
        tiene_chapa = any("CHAPA" in t for t in tipos)
        tiene_perfil = any("PERFIL" in t for t in tipos)
        tiene_acero = any(t in ["HIERRO", "MALLA", "CLAVOS", "ALAMBRE", "PERFIL", "CHAPA", "TUBO", "CAÑO"] for t in tipos)
        tiene_pintura = any("PINTURA" in t or "ACCESORIO" in t or "ELECTRODO" in t for t in tipos)

        if activa:
            if bruto > META_MAXIMA: desc_base = 15; nivel_texto = "PARTNER MAX"; color = "#6200ea"; meta = 0
            elif bruto > META_MEDIA: desc_base = 12; nivel_texto = "CONSTRUCTOR"; color = "#d32f2f"; meta = META_MAXIMA
            elif bruto > META_BASE: desc_base = 10; nivel_texto = "OBRA"; color = "#f57c00"; meta = META_MEDIA
            else: desc_base = 3; nivel_texto = "CONTADO"; color = "#2e7d32"; meta = META_BASE

            boosters = []
            if tiene_chapa and tiene_perfil: desc_extra += 3; boosters.append("KIT TECHO")
            elif tiene_acero and tiene_pintura: desc_extra += 2; boosters.append("PACK TERM.")
                
            desc_total = min(desc_base + desc_extra, 18)
            if desc_extra > 0: 
                nivel_texto = f"{nivel_texto} + {' '.join(boosters)}"
                if desc_total >= 15: color = "#6200ea" 
        else:
            desc_total = 0; nivel_texto = "EXPIRADO"; color = "#455a64"

        neto = bruto * (1 - (desc_total/100))
        ahorro_total = bruto - neto
        return bruto, neto, desc_total, color, nivel_texto, meta, segundos_restantes, activa, color_reloj, reloj_init, ahorro_total
    except:
        return 0, 0, 0, "#000", "ERROR", 0, 0, False, "#000", "00:00", 0

def generar_link_wa(total):
    try:
        txt = "HOLA, QUIERO CONGELAR PRECIO YA (Oferta Flash):\n" + "\n".join([f"▪ {i['cantidad']}x {i['producto']}" for i in st.session_state.cart])
        txt += f"\n💰 TOTAL FINAL: ${total:,.0f} + IVA"
        return f"https://wa.me/5493401527780?text={urllib.parse.quote(txt)}"
    except:
        return "https://wa.me/5493401527780"

# ==========================================
# IA LOGIC (CEREBRO OPTIMIZADO)
# ==========================================
def get_sys_prompt(csv_context, DOLAR_BNA):
    return f"""
    ROL: Miguel, vendedor experto de Pedro Bravin S.A.
    DB: {csv_context}
    ZONA GRATIS (PUNTOS LOGÍSTICOS): {CIUDADES_GRATIS}
    DOLAR BNA VENTA: {DOLAR_BNA}

    🛑 **REGLA DE ORO (SEGURIDAD DE PRECIOS):**
    1. TU ÚNICA FUENTE DE VERDAD ES LA "DB".
    2. Si un producto NO está en la DB, di: "No tengo stock de eso" o sugiere un sustituto que SÍ esté.
    3. JAMÁS INVENTES UN PRECIO.

    📏 **CATÁLOGO TÉCNICO (ESTRICTO):**
    - **12m:** Perfil C, IPN, UPN, ADN.
    - **6.40m:** Caños (Mecánico, Epoxi, Galvanizado, Schedule). **¡ATENCIÓN! La unidad de venta de estas barras es "METRO", NO "KG".**
    - **6m:** Tubos Estructurales, Hierros, Ángulos, Planchuelas.
    - **CHAPA T90:** Única medida 13m.
    - **CHAPA COLOR / CINCALUM:** Por metro.
    - **AISLANTES ISOVER ISOLANT:** Cotiza SIEMPRE por ROLLO CERRADO (Precio m² * m² del rollo).

    🚚 **LÓGICA DE FLETE:**
    1. **CASO 1: ZONA GRATIS.** Si la ciudad está en {CIUDADES_GRATIS} -> ENVÍO $0.
    2. **CASO 2: FUERA DE ZONA.** - Calcula KM ida y vuelta desde punto logístico más cercano.
       - Costo: `KM_TOTAL * 0.85 USD * {DOLAR_BNA} * 1.21`.
       - Agrega item: "[ADD:1:FLETE A [CIUDAD]:PRECIO:SERVICIO]".

    ⛔ **PROTOCOLO SNIPER:**
    1. **BREVEDAD:** Max 15 palabras. Directo.
    2. **CONFIRMACIÓN:** SOLO agrega `[ADD:...]` si el cliente confirma o pide explícitamente.
    3. **UPSELL:** "Te faltan $X para el descuento. ¿Agrego pintura?".

    SALIDA: [TEXTO VISIBLE] [ADD:CANTIDAD:PRODUCTO:PRECIO_UNITARIO_FINAL_PESOS:TIPO]
    """

def procesar_input(contenido, es_imagen=False):
    if "chat_session" in st.session_state:
        msg = contenido
        prefix = ""
        if es_imagen: msg = ["COTIZA ESTO RÁPIDO. DETECTA OPORTUNIDADES Y CONTEXTO DEL PRODUCTO (No confundir unidades).", contenido]
        prompt = f"{prefix}{msg}. (NOTA: Sé breve. Cotiza precios exactos de la DB)." if not es_imagen else msg
        try:
            return st.session_state.chat_session.send_message(prompt).text
        except Exception as e:
            return "Hubo un error de conexión, intenta de nuevo."
    return "Error: Chat off."
