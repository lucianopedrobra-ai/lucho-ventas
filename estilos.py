# estilos.py
import streamlit as st
import streamlit.components.v1 as components 

def cargar_estilos(color_barra, porcentaje_barra, color_timer, reloj_python, display_badge, subtext_badge, display_precio, display_iva, seg_restantes, generar_link_wa, total_final, oferta_viva):
    
    header_html = f"""
    <style>
    /* LIMPIEZA */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    
    /* LAYOUT OPTIMIZADO PARA MÓVIL */
    .block-container {{ padding-top: 130px !important; padding-bottom: 120px !important; }}
    [data-testid="stSidebar"] {{ display: none; }} 
    
    /* INPUT CHAT SLIM */
    [data-testid="stBottomBlock"], [data-testid="stChatInput"] {{ 
        position: fixed; bottom: 0; left: 0; width: 100%; 
        background: white; padding: 5px 10px !important; 
        z-index: 99999; border-top: 1px solid #eee; 
    }}
    .stChatInputContainer textarea {{ min-height: 38px !important; height: 38px !important; padding: 8px !important; }}

    /* HEADER */
    .fixed-header {{ position: fixed; top: 0; left: 0; width: 100%; background: #fff; z-index: 99990; border-bottom: 4px solid {color_barra}; height: 95px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.15); }}
    
    /* ANIMACIONES */
    @keyframes heartbeat {{ 0% {{ transform: scale(1); }} 15% {{ transform: scale(1.05); }} 30% {{ transform: scale(1); }} 45% {{ transform: scale(1.05); }} 60% {{ transform: scale(1); }} }}
    @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
    @keyframes slideBg {{ 0% {{ background-position: 0% 50%; }} 100% {{ background-position: 100% 50%; }} }}

    .price-tag {{ font-weight: 900; color: #111; font-size: 1.5rem; animation: heartbeat 2s infinite; }}
    .badge {{ background: linear-gradient(90deg, {color_barra}, #111); color: white; padding: 3px 10px; border-radius: 4px; font-weight: 900; font-size: 0.75rem; text-transform: uppercase; }}
    
    /* BARRA PROGRESO */
    .progress-container {{ width: 100%; height: 8px; background: #eee; position: absolute; bottom: 0; }}
    .progress-bar {{ 
        height: 100%; width: {porcentaje_barra}%; 
        background: linear-gradient(90deg, {color_barra}, #ffeb3b); 
        transition: width 0.5s ease-out; 
        background-size: 200% 200%;
        animation: slideBg 2s linear infinite;
    }}

    .top-strip {{ background: #000; color: #fff; padding: 4px 10px; display: flex; justify-content: space-between; font-size: 0.7rem; align-items: center; font-weight: bold; letter-spacing: 0.5px; }}
    .cart-summary {{ padding: 5px 15px; display: flex; justify-content: space-between; align-items: center; height: 60px; }}
    .timer-box {{ color: {color_timer}; background: #fff; padding: 1px 6px; border-radius: 3px; font-weight: 900; border: 1px solid {color_timer}; }}
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {{ position: fixed; top: 95px; left: 0; width: 100%; background: #ffffff; z-index: 99980; padding-top: 2px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .stTabs [data-baseweb="tab"] {{ flex: 1; text-align: center; padding: 6px; font-weight: bold; font-size: 0.75rem; }}
    
    /* BOTÓN FLOTANTE ESTILO WHATSAPP (EL +) */
    div[data-testid="stPopover"] {{
        position: fixed; bottom: 65px; left: 10px; z-index: 200000;
        width: auto;
    }}
    div[data-testid="stPopover"] button {{
        border-radius: 50%; width: 45px; height: 45px;
        background-color: #25D366; color: white; border: 2px solid white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        display: flex; align-items: center; justify-content: center; font-size: 20px;
        animation: pulse-green-btn 2s infinite;
    }}
    @keyframes pulse-green-btn {{ 0% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }} 70% {{ box-shadow: 0 0 0 10px rgba(37, 211, 102, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }} }}
    </style>
    
    <div class="fixed-header">
        <div class="top-strip">
            <div style="display:flex; align-items:center; gap:5px;">⏳ EXPIRA: <span id="countdown_display" class="timer-box">{reloj_python}</span></div>
            <div style="color:#FFD700; font-style:italic;"> PEDRO BRAVIN S.A.</div>
        </div>
        <div class="cart-summary">
            <div>
                <span class="badge">{display_badge}</span>
                <div style="font-size:0.7rem; color:{color_barra}; font-weight:900; margin-top:3px; animation: heartbeat 1s infinite;">{subtext_badge}</div>
            </div>
            <div class="price-tag">{display_precio}<span style="font-size:0.8rem; font-weight:400; color:#666; margin-left:2px;">{display_iva}</span></div>
        </div>
        <div class="progress-container"><div class="progress-bar"></div></div>
    </div>
    <script>
    (function() {{
        if (window.miIntervalo) clearInterval(window.miIntervalo); var duration = {seg_restantes}; var display = document.getElementById("countdown_display");
        function updateTimer() {{
            var m = parseInt(duration / 60, 10); var s = parseInt(duration % 60, 10); m = m < 10 ? "0" + m : m; s = s < 10 ? "0" + s : s;
            if (display) display.textContent = m + ":" + s;
            if (--duration < 0) {{ duration = 0; if (window.miIntervalo) clearInterval(window.miIntervalo); }}
        }}
        if (duration > 0) {{ updateTimer(); window.miIntervalo = setInterval(updateTimer, 1000); }}
    }})();
    </script>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # BOTON PAGAR AHORA
    if len(st.session_state.cart) > 0 and oferta_viva:
        st.markdown(f"""
        <div style="position:fixed; bottom:75px; right:10px; left:10px; z-index:200000; display:flex; justify-content:center;">
            <a href="{generar_link_wa(total_final)}" target="_blank" style="
                background: linear-gradient(90deg, #ff0000, #d50000); color: white; 
                padding: 15px 30px; border-radius: 50px; width: 100%; text-align:center;
                font-weight: 900; text-decoration: none; box-shadow: 0 5px 25px rgba(255,0,0,0.6);
                border: 3px solid #fff; font-size: 1.2rem; animation: shake 4s infinite; text-transform: uppercase;">
                🔥 PAGAR AHORA: ${total_final:,.0f} ➔
            </a>
        </div>
        <style>@keyframes shake {{ 0%, 100% {{transform: translateX(0);}} 10%, 30%, 50%, 70%, 90% {{transform: translateX(-2px);}} 20%, 40%, 60%, 80% {{transform: translateX(2px);}} }}</style>
        """, unsafe_allow_html=True)

def auto_scroll():
    components.html("""
        <script>
            function scrollDown() {
                var body = window.parent.document.querySelector(".main");
                if (body) {
                    body.scrollTop = body.scrollHeight;
                }
            }
            setInterval(scrollDown, 800);
        </script>
    """, height=0)
