/* MENU HAMBURGUESA */
const menuToggle = document.getElementById("menuToggle");
const navMenu = document.getElementById("navMenu");

menuToggle.addEventListener("click", function(){
    menuToggle.classList.toggle("active");
    navMenu.classList.toggle("active");
});
