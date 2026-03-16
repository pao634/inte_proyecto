document.addEventListener("DOMContentLoaded", function () {

    // ===== ASIGNAR COLOR AL CONTADOR SEGÚN TAG =====
    document.querySelectorAll(".conv-card").forEach(card => {
        const contador = card.querySelector(".contador");
        const tag = card.querySelector(".tag");

        if(tag.classList.contains("nueva")){
            contador.classList.add("contador-nueva");
        }
        else if(tag.classList.contains("progreso")){
            contador.classList.add("contador-progreso");
        }
        else if(tag.classList.contains("casi")){
            contador.classList.add("contador-casi");
        }
        else{
            contador.classList.add("contador-finalizada");
        }
    });

    // ===== CONTADOR =====
    function actualizarContadores() {
        document.querySelectorAll(".conv-card").forEach(card => {
            const contador = card.querySelector(".contador");
            let segundos = parseInt(card.dataset.tiempo);

            if (isNaN(segundos) || segundos <= 0) {
                contador.textContent = "⌛ Finalizada";
                card.dataset.tiempo = 0;
                return;
            }

            const d = Math.floor(segundos / 86400);
            const h = Math.floor((segundos % 86400) / 3600);
            const m = Math.floor((segundos % 3600) / 60);
            const s = segundos % 60;

            contador.textContent = `⌛ ${d}d ${h}h ${m}m ${s}s`;
            card.dataset.tiempo = Math.max(segundos - 1, 0);
        });
    }

    actualizarContadores();
    setInterval(actualizarContadores, 1000);

    // ===== DESCARGAR IMAGEN =====
    document.querySelectorAll(".btn-descargar").forEach(btn => {
        btn.addEventListener("click", function () {

            const card = this.closest(".conv-card");
            const img = card.querySelector(".conv-img");

            if (!img) {
                showAlert("Esta convocatoria no tiene imagen para descargar.", "warning");
                return;
            }

            const titulo = card.querySelector(".conv-title")
                .textContent
                .trim()
                .replace(/\s+/g,"_");

            const link = document.createElement("a");
            link.href = img.src;
            link.download = titulo + ".png";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    });

    // ===== VISOR =====
    const visor = document.getElementById("visorImagen");
    const imagenGrande = document.getElementById("imagenGrande");
    const cerrar = document.querySelector(".cerrar");
    const zoomMas = document.getElementById("zoomMas");
    const zoomMenos = document.getElementById("zoomMenos");

    let escala = 1;
    const ZOOM_MAX = 2;   // límite seguro para que no se corte
    const ZOOM_MIN = 1;   // tamaño base

    function actualizarTransform(){
        imagenGrande.style.transform = `translate(-50%, -50%) scale(${escala})`;
    }

    document.querySelectorAll(".btn-ver").forEach(btn => {
        btn.addEventListener("click", function () {

            const card = this.closest(".conv-card");
            const img = card.querySelector(".conv-img");

            if(!img){
                showAlert("Esta convocatoria no tiene imagen.", "warning");
                return;
            }

            imagenGrande.src = img.src;
            visor.classList.add("activo");
            document.body.classList.add("sin-scroll");

            escala = 1;
            actualizarTransform();
        });
    });

    cerrar.onclick = () => {
        visor.classList.remove("activo");
        document.body.classList.remove("sin-scroll");
    };

    zoomMas.onclick = () => {
        if (escala < ZOOM_MAX) {
            escala += 0.2;
            actualizarTransform();
        }
    };

    zoomMenos.onclick = () => {
        if (escala > ZOOM_MIN) {
            escala -= 0.2;
            actualizarTransform();
        }
    };

    // ===== CARRUSEL =====
    const track = document.querySelector(".conv-track");
    const prev = document.querySelector(".c-prev");
    const next = document.querySelector(".c-next");
    const step = 370;
    let auto;

    function moveNext(){
        if(track.children.length < 4) return; // no mover si menos de 4
        track.style.transition = "transform .35s";
        track.style.transform = `translateX(-${step}px)`;
        setTimeout(()=>{
            track.appendChild(track.firstElementChild);
            track.style.transition = "none";
            track.style.transform = "translateX(0)";
        },350);
    }

    function movePrev(){
        if(track.children.length < 4) return;
        track.insertBefore(track.lastElementChild, track.firstElementChild);
        track.style.transition = "none";
        track.style.transform = `translateX(-${step}px)`;
        requestAnimationFrame(()=>{
            track.style.transition = "transform .35s";
            track.style.transform = "translateX(0)";
        });
    }

    function actualizarCarrusel() {
        const cards = [...document.querySelectorAll(".conv-card")];

        if(cards.length < 4){
            // Menos de 4: centrado y estático
            track.classList.add("centered");
            prev.classList.add("hide");
            next.classList.add("hide");
            if(auto) clearInterval(auto); // detener animación automática
        } else {
            // 4 o más: habilitar animación
            track.classList.remove("centered");
            prev.classList.remove("hide");
            next.classList.remove("hide");

            if(!auto){
                auto = setInterval(moveNext, 3000);
                track.onmouseenter = () => clearInterval(auto);
                track.onmouseleave = () => auto = setInterval(moveNext, 3000);
            }
        }
    }

    actualizarCarrusel();

    if(next && prev){
        next.onclick = moveNext;
        prev.onclick = movePrev;
    }

    // Actualizamos carrusel cada segundo por si se elimina alguna tarjeta
    setInterval(actualizarCarrusel, 1000);

});
