# estilos.py
import streamlit as st
import streamlit.components.v1 as components 

def cargar_estilos(color_barra, porcentaje_barra, color_timer, reloj_python, display_badge, subtext_badge, display_precio, display_iva, seg_restantes, generar_link_wa, total_final, oferta_viva):
    
    header_html = f"""
    <style>
    /* MODO OSCURO FORZADO */
    .stApp {{ background-color: #121212 !important; }}
    p, h1, h2, h3, div, span {{ color: #e0e0e0; }}
    
    /* LIMPIEZA */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    .block-container {{ padding-top: 100px !important; padding-bottom: 130px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 

    /* CHAT INDUSTRIAL */
    [data-testid="stChatInput"] {{ background: #1e1e1e !important; border-top: 1px solid #333; }}
    .stChatInputContainer {{ border: 1px solid #444 !important; background: #2c2c2c !important; border-radius: 4px !important; }}
    .stChatInputContainer textarea {{ color: white !important; }}

    /* HEADER INDUSTRIAL */
    .fixed-header {{ 
        position: fixed; top: 0; left: 0; width: 100%; 
        background: #1e1e1e; 
        z-index: 99990; 
        height: 90px; 
        border-bottom: 2px solid #FFD700; /* Amarillo Pedro Bravin */
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }}
    
    .data-row {{ display: flex; justify-content: space-between; padding: 10px 15px; align-items: center; }}
    
    .price-industrial {{ font-family: 'Courier New', monospace; font-size: 1.6rem; color: #FFD700; font-weight: bold; text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }}
    
    .timer-digital {{ 
        font-family: 'Courier New', monospace; 
        background: #000; color: {color_timer}; 
        padding: 5px 10px; border: 1px solid #333; 
        font-size: 1.2rem; letter-spacing: 2px;
    }}

    /* BARRA PROGRESO */
    .progress-bar-ind {{ height: 4px; background: #333; width: 100%; position: absolute; bottom: 0; }}
    .fill-ind {{ height: 100%; background: repeating-linear-gradient(45deg, #FFD700, #FFD700 10px, #b8860b 10px, #b8860b 20px); width: {porcentaje_barra}%; }}

    /* BOTÓN (+) */
    div[data-testid="stPopover"] button {{
        background-color: #FFD700; color: black; border-radius: 0px; font-weight: bold;
    }}
    </style>
    
    <div class="fixed-header">
        <div class="data-row">
            <div>
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase;">COTIZADOR V3.0</div>
                <div class="price-industrial">{display_precio}</div>
            </div>
            <div style="text-align:right;">
                <div class="timer-digital">{reloj_python}</div>
                <div style="font-size:0.7rem; color:#aaa; margin-top:2px;">{subtext_badge}</div>
            </div>
        </div>
        <div class="progress-bar-ind"><div class="fill-ind"></div></div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # BOTON PAGAR (Amarillo y Negro, alto contraste)
    if len(st.session_state.cart) > 0 and oferta_viva:
        st.markdown(f"""
        <div style="position:fixed; bottom:70px; right:10px; left:10px; z-index:200000;">
            <a href="{generar_link_wa(total_final)}" target="_blank" style="
                display: block; background: #FFD700; color: #000; 
                padding: 15px; width: 100%; text-align:center;
                font-weight: 900; text-decoration: none; 
                border: 2px solid #fff; text-transform: uppercase;
                box-shadow: 0 0 15px rgba(255, 215, 0, 0.4);">
                ⚡ CONFIRMAR: ${total_final:,.0f}
            </a>
        </div>
        """, unsafe_allow_html=True)

def auto_scroll():
    components.html("""<script>setInterval(function(){var b=window.parent.document.querySelector(".main");if(b)b.scrollTop=b.scrollHeight;},800);</script>""", height=0)
            return "Hubo un error de conexión, intenta de nuevo."
    return "Error: Chat off."
