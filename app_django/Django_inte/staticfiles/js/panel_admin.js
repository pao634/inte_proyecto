const avatarMenu = document.getElementById("avatarMenu");

avatarMenu.addEventListener("click", () => {
    avatarMenu.classList.toggle("active");
});

window.addEventListener("click", function(e){
    if(!avatarMenu.contains(e.target)){
        avatarMenu.classList.remove("active");
    }
});
// ===== AUTO CERRAR MENSAJES =====
document.addEventListener("DOMContentLoaded", function(){

    const alertas = document.querySelectorAll(".alerta");

    alertas.forEach((alerta) => {

        setTimeout(() => {
            alerta.style.transition = "opacity 0.4s ease, transform 0.3s ease";
            alerta.style.opacity = "0";
            alerta.style.transform = "translateX(20px)";

            setTimeout(() => {
                alerta.remove();
            }, 400);

        }, 3000); // 3 segundos

    });

});