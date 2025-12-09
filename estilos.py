# estilos.py
import streamlit as st
import streamlit.components.v1 as components 

def cargar_estilos(color_barra, porcentaje_barra, color_timer, reloj_python, display_badge, subtext_badge, display_precio, display_iva, seg_restantes, generar_link_wa, total_final, oferta_viva):
    
    header_html = f"""
    <style>
    /* LIMPIEZA */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    .block-container {{ padding-top: 120px !important; padding-bottom: 120px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 

    /* CHAT MINIMAL */
    [data-testid="stBottomBlock"] {{ background: rgba(255,255,255,0.8) !important; backdrop-filter: blur(5px); }}
    .stChatInputContainer {{ border: 1px solid #000 !important; border-radius: 0px !important; box-shadow: none !important; }}

    /* HEADER */
    .fixed-header {{ 
        position: fixed; top: 0; left: 0; width: 100%; 
        background: #fff; z-index: 99990; 
        height: 100px; 
        display: flex; flex-direction: column; justify-content: center;
        border-bottom: 1px solid #000;
    }}
    
    .container-min {{ padding: 0 20px; display: flex; justify-content: space-between; align-items: baseline; }}
    
    .big-price {{ font-size: 2.2rem; font-weight: 900; color: #000; line-height: 1; letter-spacing: -1.5px; }}
    .meta-info {{ text-align: right; }}
    
    .timer-min {{ font-weight: 900; font-size: 1.2rem; color: #000; }}
    .status-dot {{ height: 10px; width: 10px; background-color: {color_timer}; border-radius: 50%; display: inline-block; margin-right: 5px; }}

    /* BARRA DE VIDA (Estilo videojuego minimalista) */
    .life-bar {{ height: 5px; background: #eee; width: 100%; position: absolute; bottom: 0; }}
    .life-fill {{ height: 100%; background: #000; width: {porcentaje_barra}%; transition: width 0.2s; }}

    </style>
    
    <div class="fixed-header">
        <div class="container-min">
            <div>
                <span style="font-size:0.8rem; font-weight:700;">TOTAL ESTIMADO</span><br>
                <div class="big-price">{display_precio}</div>
            </div>
            <div class="meta-info">
                <div class="timer-min"><span class="status-dot"></span>{reloj_python}</div>
                <div style="font-size:0.7rem; font-weight:bold; text-decoration: underline;">{subtext_badge}</div>
            </div>
        </div>
        <div class="life-bar"><div class="life-fill"></div></div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # BOTON PAGAR (Negro solido, muy Apple)
    if len(st.session_state.cart) > 0 and oferta_viva:
        st.markdown(f"""
        <div style="position:fixed; bottom:80px; right:20px; left:20px; z-index:200000;">
            <a href="{generar_link_wa(total_final)}" target="_blank" style="
                display:block; background: #000; color: #fff; 
                padding: 18px; width: 100%; text-align:center;
                font-weight: 600; text-decoration: none; font-size: 1rem;
                border-radius: 8px; transition: transform 0.1s;">
                Pagar Ahora ➔
            </a>
        </div>
        """, unsafe_allow_html=True)

def auto_scroll():
    components.html("""<script>setInterval(function(){var b=window.parent.document.querySelector(".main");if(b)b.scrollTop=b.scrollHeight;},800);</script>""", height=0)
