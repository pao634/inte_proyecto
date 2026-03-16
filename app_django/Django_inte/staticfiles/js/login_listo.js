/* ================================= */
/* PARTICULAS FONDO */
/* ================================= */

const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');

let width = canvas.width = window.innerWidth;
let height = canvas.height = window.innerHeight;

window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
});

const mouse = { x: null, y: null };

window.addEventListener('mousemove', e => {
    mouse.x = e.x;
    mouse.y = e.y;
});

class Particle {
    constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.size = Math.random() * 2 + 1;
        this.speedX = (Math.random() - 0.5) * 0.8;
        this.speedY = (Math.random() - 0.5) * 0.8;
        this.color = 'rgba(255,255,255,0.6)';
    }

    update() {
        this.x += this.speedX;
        this.y += this.speedY;

        if (this.x < 0 || this.x > width) this.speedX *= -1;
        if (this.y < 0 || this.y > height) this.speedY *= -1;

        if (mouse.x !== null && mouse.y !== null) {
            const dx = this.x - mouse.x;
            const dy = this.y - mouse.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < 100) {
                this.x += dx / 25;
                this.y += dy / 25;
            }
        }
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
    }
}

const particlesArray = [];
const particleCount = 100;

function initParticles() {
    particlesArray.length = 0;
    for (let i = 0; i < particleCount; i++) {
        particlesArray.push(new Particle());
    }
}

function connectParticles() {
    for (let a = 0; a < particlesArray.length; a++) {
        for (let b = a; b < particlesArray.length; b++) {
            let dx = particlesArray[a].x - particlesArray[b].x;
            let dy = particlesArray[a].y - particlesArray[b].y;
            let distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < 120) {
                ctx.strokeStyle = `rgba(255,255,255,${0.3 - distance / 400})`;
                ctx.lineWidth = 0.5;
                ctx.beginPath();
                ctx.moveTo(particlesArray[a].x, particlesArray[a].y);
                ctx.lineTo(particlesArray[b].x, particlesArray[b].y);
                ctx.stroke();
            }
        }
    }
}

function animate() {
    ctx.clearRect(0, 0, width, height);
    particlesArray.forEach(p => {
        p.update();
        p.draw();
    });
    connectParticles();
    requestAnimationFrame(animate);
}

initParticles();
animate();


function togglePassword() {

    const input = document.querySelector('input[name="password"]');
    const icon = document.querySelector(".toggle-password i");

    if (input.type === "password") {

        input.type = "text";

        icon.classList.remove("bi-eye");
        icon.classList.add("bi-eye-slash");

    } else {

        input.type = "password";

        icon.classList.remove("bi-eye-slash");
        icon.classList.add("bi-eye");

    }
}


/* ================================= */
/* ERROR TEMPORAL 3 SEG */
/* ================================= */

window.addEventListener("DOMContentLoaded", () => {
    const errorMessage = document.querySelector(".error-message");

    if (errorMessage) {
        setTimeout(() => {
            errorMessage.style.opacity = "0";
            errorMessage.style.transform = "translateY(-10px)";
            setTimeout(() => errorMessage.remove(), 400);
        }, 3000);
    }
});


/* ================================= */
/* LOADER SUAVE + OCULTAR BOTON */
/* ================================= */

document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector("form");
    const loader = document.getElementById("loader");
    const loginCard = document.querySelector(".login-card");
    const btnInicio = document.querySelector(".btn_inicio_link");

    if (form && loader && loginCard) {

        form.addEventListener("submit", function (e) {

            e.preventDefault();

            /* ANIMACIÓN BOTÓN REGRESAR */
            if(btnInicio){
                btnInicio.style.transition = "all 0.4s ease";
                btnInicio.style.opacity = "0";
                btnInicio.style.transform = "translateX(-30px)";
            }

            /* ANIMACIÓN LOGIN CARD */
            loginCard.style.transition = "all 0.4s ease";
            loginCard.style.opacity = "0";
            loginCard.style.transform = "scale(0.95)";

            setTimeout(() => {

                loginCard.style.display = "none";

                if(btnInicio){
                    btnInicio.style.display = "none";
                }

                loader.classList.add("active");

            }, 400);

            /* ENVÍO DEL FORM */
            setTimeout(() => {
                form.submit();
            }, 2000);

        });

    }

});