document.addEventListener("DOMContentLoaded", function () {

    const modalEditar = document.getElementById("modalEditar");
    const modalEliminar = document.getElementById("modalEliminar");
    const modalCrear = document.getElementById("modalCrear");

    const csrfInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    /* =========================
       ABRIR MODAL EDITAR
    ========================== */
    document.querySelectorAll(".btn-editar").forEach(btn => {
        btn.addEventListener("click", function () {

            document.getElementById("editId").value = this.dataset.id;
            document.getElementById("editTitulo").value = this.dataset.titulo;

            let fecha = this.dataset.fecha;
            if (fecha && !fecha.includes("T")) {
                fecha = fecha.replace(" ", "T");
            }

            document.getElementById("editFecha").value = fecha;

            if (modalEditar) modalEditar.style.display = "flex";
        });
    });

    /* =========================
       ABRIR MODAL ELIMINAR
    ========================== */
    document.querySelectorAll(".btn-eliminar").forEach(btn => {
        btn.addEventListener("click", function () {
            document.getElementById("deleteId").value = this.dataset.id;
            if (modalEliminar) modalEliminar.style.display = "flex";
        });
    });

    /* =========================
       CREAR
    ========================== */
    const formCrear = document.getElementById("formCrear");

    if (formCrear) {
        formCrear.addEventListener("submit", function (e) {
            e.preventDefault();

            if (!csrfToken) {
                mostrarMensaje("Token CSRF no encontrado.", "error");
                return;
            }

            const formData = new FormData(formCrear);

            fetch(URL_CREAR, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    mostrarMensaje("Convocatoria creada correctamente.", "exito");
                    cerrarModalCrear();

                    setTimeout(() => location.reload(), 2500);
                } else {
                    mostrarMensaje(data.error || "Error al crear.", "error");
                }
            })
            .catch(() => mostrarMensaje("Error del servidor.", "error"));
        });
    }

    /* =========================
       EDITAR
    ========================== */
    const formEditar = document.getElementById("formEditar");

    if (formEditar) {
        formEditar.addEventListener("submit", function (e) {
            e.preventDefault();

            if (!csrfToken) {
                mostrarMensaje("Token CSRF no encontrado.", "error");
                return;
            }

            const formData = new FormData(formEditar);

            fetch(URL_EDITAR, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    mostrarMensaje("Convocatoria editada correctamente.", "exito");
                    cerrarModalEditar();

                    setTimeout(() => location.reload(), 2500);
                } else {
                    mostrarMensaje(data.error || "Error al editar.", "error");
                }
            })
            .catch(() => mostrarMensaje("Error del servidor.", "error"));
        });
    }

    /* =========================
       ELIMINAR
    ========================== */
    const btnEliminar = document.getElementById("confirmarEliminar");

    if (btnEliminar) {
        btnEliminar.addEventListener("click", function () {

            if (!csrfToken) {
                mostrarMensaje("Token CSRF no encontrado.", "error");
                return;
            }

            const id = document.getElementById("deleteId").value;

            fetch(URL_ELIMINAR, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrfToken
                },
                body: new URLSearchParams({ id: id })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    mostrarMensaje("Convocatoria eliminada correctamente.", "exito");
                    cerrarModalEliminar();

                    setTimeout(() => location.reload(), 2500);
                } else {
                    mostrarMensaje(data.error || "Error al eliminar.", "error");
                }
            })
            .catch(() => mostrarMensaje("Error del servidor.", "error"));
        });
    }

    /* =========================
       CERRAR MODALES
    ========================== */
    window.cerrarModalEditar = () => {
        if (modalEditar) modalEditar.style.display = "none";
    };

    window.cerrarModalEliminar = () => {
        if (modalEliminar) modalEliminar.style.display = "none";
    };

    window.cerrarModalCrear = () => {
        if (modalCrear) modalCrear.style.display = "none";
        if (formCrear) formCrear.reset();
    };

    window.abrirModalCrear = () => {
        if (modalCrear) modalCrear.style.display = "flex";
    };

});


/* =========================
   MENSAJE PROFESIONAL
========================= */
function mostrarMensaje(texto, tipo = "exito") {

    const mensaje = document.getElementById("mensajeAccion");
    if (!mensaje) return;

    const icono = mensaje.querySelector(".mensaje-icono");
    const textoSpan = mensaje.querySelector(".mensaje-texto");

    textoSpan.textContent = texto;

    if (tipo === "error") {
        mensaje.className = "mensaje-accion error";
        icono.innerHTML = '<i class="bi bi-x-circle-fill"></i>';
    } else {
        mensaje.className = "mensaje-accion exito";
        icono.innerHTML = '<i class="bi bi-check-circle-fill"></i>';
    }

    mensaje.style.display = "flex";

    requestAnimationFrame(() => {
        mensaje.style.opacity = "1";
        mensaje.style.transform = "translateY(0)";
    });

    setTimeout(() => {
        mensaje.style.opacity = "0";
        mensaje.style.transform = "translateY(-10px)";
        setTimeout(() => {
            mensaje.style.display = "none";
        }, 400);
    }, 3000);
}