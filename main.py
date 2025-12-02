<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<style>
    /* ... (CSS para ocultar 527780 y Contacto, y estilizar widgets) ... */
    :root { --pb-blue: #0f2c59; --pb-orange: #ff6b00; --pb-green: #25D366; --shadow: 0 5px 20px rgba(0,0,0,0.2); }
    
    .pb-left-dock { position: fixed; bottom: 20px; left: 20px; z-index: 999990; display: flex; flex-direction: column-reverse; align-items: flex-start; gap: 10px; }
    .pb-status-pill { background: var(--pb-blue); color: white; padding: 6px 20px 6px 6px; border-radius: 50px; display: flex; align-items: center; gap: 10px; cursor: pointer; box-shadow: var(--shadow); border: 2px solid white; transition: transform 0.2s; }
    .pb-contact-menu { background: white; width: 320px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 1px solid #eee; position: absolute; bottom: 65px; left: 0; opacity: 0; visibility: hidden; transition: all 0.3s; overflow: hidden; }
    .pb-contact-menu.active { opacity: 1; visibility: visible; transform: translateY(0) scale(1); }
    .pb-menu-head { background: var(--pb-blue); color: white; padding: 15px; position: relative; }
    .pb-map-btn { display: block; background: rgba(255,255,255,0.15); color: #ffffff !important; text-decoration: none; padding: 8px; border-radius: 6px; font-size: 12px; text-align: center; margin-top: 5px; font-weight: 600; }
    .pb-menu-list { max-height: 350px; overflow-y: auto; padding: 0; }
    
    .pb-right-dock { position: fixed; bottom: 25px; right: 25px; z-index: 999999; } /* <--- LUCHO VISIBLE */
    .pb-lucho-fab { width: 65px; height: 65px; background: var(--pb-orange); color: white; border-radius: 50%; border: 3px solid white; box-shadow: 0 4px 20px rgba(255, 107, 0, 0.5); display: flex; align-items: center; justify-content: center; font-size: 28px; cursor: pointer; animation: pb-pulse 4s infinite; }
    
    .pb-modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 44, 89, 0.9); z-index: 1000000; display: none; justify-content: center; align-items: center; padding: 15px; }
    .pb-modal-overlay.open { display: flex; }
    .pb-box { background: white; width: 100%; max-width: 1000px; height: 90vh; border-radius: 12px; position: relative; overflow: hidden; }
    /* ... (Resto de CSS y media queries) ... */
</style>

<div class="pb-left-dock">
    <div class="pb-contact-menu" id="pbMenu">
        <div class="pb-menu-head">
            <h4><i class="fa-solid fa-headset"></i> Centro de Atención</h4>
            <a href="https://goo.gl/maps/tu-link-aqui" target="_blank" class="pb-map-btn"><i class="fa-solid fa-location-dot"></i> Ver Ubicación en Mapa</a>
            <button class="pb-menu-close" onclick="toggleMenu()">×</button>
        </div>
        <div class="pb-menu-list">
            <div class="pb-group-title">Consultas Generales</div>
            <div class="pb-row"><span class="pb-name">Jorgelina (Reclamos)</span><div class="pb-actions"><a href="https://wa.me/5493406400354" target="_blank" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a><a href="tel:3406400354" class="pb-act-btn is-call"><i class="fa-solid fa-phone"></i></a></div></div>
            <div class="pb-group-title">Ventas</div>
            <div class="pb-row"><span class="pb-name">Martín</span><div class="pb-actions"><a href="https://wa.me/5493401527780" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-row"><span class="pb-name">Miguel</span><div class="pb-actions"><a href="https://wa.me/5493401436717" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-row"><span class="pb-name">Cristian</span><div class="pb-actions"><a href="https://wa.me/5493401503488" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-row"><span class="pb-name">Nahuel</span><div class="pb-actions"><a href="https://wa.me/5493401408436" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-group-title">Operaciones</div>
            <div class="pb-row"><span class="pb-name">Administración</span><div class="pb-actions"><a href="https://wa.me/5493406400354" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-row"><span class="pb-name">Proveedores</span><div class="pb-actions"><a href="https://wa.me/5493401407263" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
            <div class="pb-row"><span class="pb-name">Logística</span><div class="pb-actions"><a href="https://wa.me/5493401523416" class="pb-act-btn is-wa"><i class="fa-brands fa-whatsapp"></i></a></div></div>
        </div>
    </div>
    <div class="pb-status-pill" onclick="toggleMenu()" id="pbStatusPill">
        <div class="pb-icon-circle"><i class="fa-solid fa-headset"></i></div>
        <div class="pb-status-info"><span class="pb-status-lbl">El Trébol</span><span class="pb-status-val"><span class="pb-dot"></span> <span id="pbStatusTxt">...</span></span></div>
    </div>
</div>

<div class="pb-right-dock">
    <div class="pb-lucho-fab" onclick="toggleCotizador()"><i class="fa-solid fa-calculator"></i></div>
</div>

<div class="pb-overlay" id="pbModal">
    <div class="pb-box">
        <button class="pb-close" onclick="toggleCotizador()">✕</button>
        <iframe 
            src="https://lucho-ventas-gbbb4nft8mo34jfyrpyumw.streamlit.app/?embed=true" 
            style="width: 100%; height: 100%; border: none;"
            title="Lucho Cotizador"
            sandbox="allow-forms allow-scripts allow-same-origin allow-popups allow-top-navigation">
        </iframe>
    </div>
</div>

<script>
    function toggleMenu() { document.getElementById('pbMenu').classList.toggle('active'); }
    function toggleCotizador() { document.getElementById('pbModal').classList.toggle('open'); }
    function toggleWorkModal() { document.getElementById('pbWorkModal').classList.toggle('open'); }

    // ... (checkHours, initMenuWatcher, cleanFooter, submitWork functions) ...
</script>
