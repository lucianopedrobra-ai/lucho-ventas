# estilos.py
import streamlit as st
import streamlit.components.v1 as components 

def cargar_estilos(color_barra, porcentaje_barra, color_timer, reloj_python, display_badge, subtext_badge, display_precio, display_iva, seg_restantes, generar_link_wa, total_final, oferta_viva):
    
    # Colores más "MP" (Azules y Celestes salvo urgencia extrema)
    if oferta_viva:
        btn_bg = "linear-gradient(90deg, #009EE3, #0072CE)" # Azul MP
        shadow_color = "rgba(0, 158, 227, 0.4)"
    else:
        btn_bg = "#ccc"
        shadow_color = "rgba(0,0,0,0.1)"

    header_html = f"""
    <style>
    /* LIMPIEZA GENERAL */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    .block-container {{ padding-top: 110px !important; padding-bottom: 140px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 

    /* CHAT FLOTANTE "CÁPSULA" (ESTILO MP/WHATSAPP) */
    [data-testid="stBottomBlock"], [data-testid="stChatInput"] {{ 
        background: transparent !important; 
        padding-bottom: 10px !important;
    }}
    .stChatInputContainer {{
        border-radius: 25px !important;
        border: 1px solid #ddd !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important;
        background: white !important;
        margin-bottom: 10px;
        width: 95% !important;
        margin-left: auto; margin-right: auto;
    }}
    .stChatInputContainer textarea {{ padding-top: 12px !important; }}

    /* HEADER LIMPIO */
    .fixed-header {{ 
        position: fixed; top: 0; left: 0; width: 100%; 
        background: rgba(255, 255, 255, 0.95); 
        backdrop-filter: blur(10px);
        z-index: 99990; 
        height: 85px; 
        border-bottom: 1px solid #f0f0f0;
    }}
    
    /* ORGANIZACIÓN HEADER */
    .header-grid {{ display: grid; grid-template-columns: 1fr auto; padding: 10px 20px; align-items: center; }}
    
    .brand-text {{ font-size: 0.75rem; color: #888; letter-spacing: 1px; font-weight: 600; text-transform: uppercase; }}
    
    /* PRECIO GRANDE Y LIMPIO */
    .price-big {{ font-size: 1.8rem; font-weight: 800; color: #333; letter-spacing: -1px; }}
    .iva-small {{ font-size: 0.8rem; color: #999; font-weight: 400; }}

    /* TIMER TIPO "ETIQUETA" */
    .timer-pill {{ 
        background: #f5f5f5; color: #333; 
        padding: 4px 12px; border-radius: 20px; 
        font-weight: 700; font-size: 0.85rem; 
        display: inline-flex; align-items: center; gap: 5px;
        border: 1px solid #eee;
    }}
    .timer-pill.urgent {{ background: #ffebee; color: #d32f2f; border-color: #ffcdd2; }}

    /* BARRA PROGRESO FINA */
    .progress-line {{ position: absolute; bottom: 0; left: 0; height: 3px; background: {color_barra}; width: {porcentaje_barra}%; transition: width 0.5s; }}

    /* BOTÓN FLOTANTE (+) */
    div[data-testid="stPopover"] button {{
        border-radius: 50%; width: 50px; height: 50px;
        background-color: #009EE3; color: white; border: none;
        box-shadow: 0 4px 12px rgba(0, 158, 227, 0.4);
    }}
    </style>
    
    <div class="fixed-header">
        <div class="header-grid">
            <div>
                <div class="brand-text">Pedro Bravin S.A.</div>
                <div class="price-big">{display_precio}<span class="iva-small">{display_iva}</span></div>
            </div>
            <div style="text-align:right;">
                <div class="{ 'timer-pill urgent' if seg_restantes < 60 else 'timer-pill' }">
                    ⏰ {reloj_python}
                </div>
                <div style="font-size:0.7rem; color:{color_barra}; font-weight:700; margin-top:5px;">
                    {subtext_badge}
                </div>
            </div>
        </div>
        <div class="progress-line"></div>
    </div>
    <script>
    (function() {{
        var duration = {seg_restantes};
        // Lógica simple de timer visual (sin actualizar DOM complejo para mantenerlo limpio)
    }})();
    </script>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # BOTON PAGAR (Estilo MP: Azul, Redondo, Sombra suave)
    if len(st.session_state.cart) > 0 and oferta_viva:
        st.markdown(f"""
        <div style="position:fixed; bottom:85px; right:15px; left:15px; z-index:200000; display:flex; justify-content:center;">
            <a href="{generar_link_wa(total_final)}" target="_blank" style="
                background: {btn_bg}; color: white; 
                padding: 16px; border-radius: 30px; width: 100%; text-align:center;
                font-weight: 600; text-decoration: none; 
                box-shadow: 0 8px 20px {shadow_color};
                font-size: 1.1rem; letter-spacing: 0.5px;">
                Pagar ${total_final:,.0f}
            </a>
        </div>
        """, unsafe_allow_html=True)

def auto_scroll():
    components.html("""<script>setInterval(function(){var b=window.parent.document.querySelector(".main");if(b)b.scrollTop=b.scrollHeight;},800);</script>""", height=0)
