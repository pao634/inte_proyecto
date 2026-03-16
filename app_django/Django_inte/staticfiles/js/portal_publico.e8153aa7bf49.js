let index = 0;
const slides = document.querySelectorAll(".slide");

function update() {
    slides.forEach((s) => s.classList.remove("active"));
    slides[index].classList.add("active");
}

document.querySelector(".next").onclick = () => {
    index = (index + 1) % slides.length;
    update();
};

document.querySelector(".prev").onclick = () => {
    index = (index - 1 + slides.length) % slides.length;
    update();
};

setInterval(() => {
    index = (index + 1) % slides.length;
    update();
}, 4000);
