const avatarMenu = document.getElementById("avatarMenu");
const navMenu = document.getElementById("navMenu");
const menuToggle = document.getElementById("menuToggle");

/* =========================
   AVATAR MENU
========================= */

avatarMenu.addEventListener("click", function(e){
    e.stopPropagation();
    this.classList.toggle("active");
});

document.addEventListener("click", function(){
    avatarMenu.classList.remove("active");
});


/* =========================
   MENU HAMBURGUESA
========================= */

menuToggle.addEventListener("click", function(e){

    e.stopPropagation();

    /* animación hamburguesa -> X */
    this.classList.toggle("active");

    /* mostrar menu */
    navMenu.classList.toggle("active");

});


/* =========================
   CERRAR MENU AL DAR CLICK FUERA
========================= */

document.addEventListener("click", function(e){

    if(!navMenu.contains(e.target) && !menuToggle.contains(e.target)){
        
        navMenu.classList.remove("active");
        menuToggle.classList.remove("active");

    }

});
