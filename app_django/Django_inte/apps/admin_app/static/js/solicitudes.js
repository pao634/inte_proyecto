const tabla = document.getElementById('tablaSolicitudes');
const solicitudesPorId = new Map();
let openDropdown = null;
let solicitudActual = null;
let todasSolicitudes = [];

/* ================================
   CARGAR SOLICITUDES
================================ */

document.addEventListener("DOMContentLoaded", function () {
    cargarSolicitudes();
    const filtroEstado = document.getElementById("filtroEstadoSolicitudes");
    const filtroTexto = document.getElementById("filtroTextoSolicitudes");
    if(filtroEstado) filtroEstado.addEventListener("change", renderSolicitudes);
    if(filtroTexto) filtroTexto.addEventListener("input", renderSolicitudes);
});

function cargarSolicitudes() {
    if (!tabla) return;
    tabla.innerHTML = "<tr><td colspan='5'><div class='skeleton-table'><div class='skeleton-row'></div><div class='skeleton-row'></div><div class='skeleton-row'></div></div></td></tr>";
    fetch("/admin/obtener_solicitudes/")
        .then(response => response.json())
        .then(data => {
            todasSolicitudes = data || [];
            solicitudesPorId.clear();
            todasSolicitudes.forEach(s => {
                const idStr = String(s._id || "");
                if (idStr) solicitudesPorId.set(idStr, s);
            });
            renderSolicitudes();
        })
        .catch(error => {
            console.error("Error cargando solicitudes:", error);
            tabla.innerHTML = "<tr><td colspan='5'>No se pudieron cargar las solicitudes</td></tr>";
        });
}

function renderSolicitudes(){
    if (!tabla) return;
    tabla.innerHTML = "";
    const estadoSel = (document.getElementById("filtroEstadoSolicitudes")?.value || "todos").toLowerCase();
    const texto = (document.getElementById("filtroTextoSolicitudes")?.value || "").toLowerCase().trim();

    const filtradas = todasSolicitudes.filter(s => {
        const est = (s.estado || "EN PROCESO").toLowerCase();
        const matchEstado = estadoSel === "todos" || est.includes(estadoSel.toLowerCase());
        const matchTexto = !texto || (s.nombre_completo || "").toLowerCase().includes(texto) || (s.nombre_proyecto || "").toLowerCase().includes(texto);
        return matchEstado && matchTexto;
    });

    filtradas.forEach(s => agregarFila(s));
}

function agregarFila(s) {
    const estado = s.estado || "Pendiente";
    let claseColor = "estado-proceso"; 
    const estLower = estado.toLowerCase();
    
    if (estLower.includes("acept")) claseColor = "estado-aceptado";
    else if (estLower.includes("rechaz")) claseColor = "estado-rechazado";

    const fila = document.createElement('tr');
    const solicitudId = s._id;

    fila.innerHTML = `
        <td data-label="Nombre">${s.nombre_completo || ''}</td>
        <td data-label="Proyecto">${s.nombre_proyecto || ''}</td>
        <td data-label="Fecha">${s.fecha_creacion || ''}</td>
        <td data-label="Estado"><span class="status ${claseColor}">${estado}</span></td>
        <td class="acciones">
            <button class="btn-ver-solicitud" data-solicitud-id="${solicitudId}">
                <i class="bi bi-eye"></i> Ver
            </button>
        </td>
    `;

    const btnVer = fila.querySelector(".btn-ver-solicitud");
    btnVer.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        const id = this.dataset.solicitudId;
        const solicitud = solicitudesPorId.get(String(id));
        if (solicitud) {
            abrirModalDetalleCompleto(solicitud);
        }
    });

    tabla.appendChild(fila);
}

/* ================================
   MODAL DETALLE COMPLETO
================================ */

function abrirModalDetalleCompleto(s) {
    solicitudActual = s._id;

    // Campos básicos
    const fields = [
        "modalNombre", "modalCorreo", "modalEdad", "modalCarrera", "modalNivel", 
        "modalMatricula", "modalAsesor", "modalTutor", "modalTelefono", "modalDireccion", 
        "modalIntegrantes", "modalProyecto", "modalDescripcion", "modalUbicacion", 
        "modalInicio", "modalClientes", "modalProblema", "modalProducto", "modalInnovacion", 
        "modalValor", "modalIdea", "modalSat", "modalPersonasTrabajan", 
        "modalMiembrosIncubacion", "modalProgramasPrevios", "modalDescripcionLider", 
        "modalRol", "modalHabilidades", "modalLogro"
    ];

    const dataMap = {
        "modalNombre": s.nombre_completo, "modalCorreo": s.correo, "modalEdad": s.edad,
        "modalCarrera": s.carrera, "modalNivel": s.nivel, "modalMatricula": s.matricula,
        "modalAsesor": s.asesor_academico, "modalTutor": s.tutor, "modalTelefono": s.telefono,
        "modalDireccion": s.direccion, "modalIntegrantes": s.integrantes_equipo,
        "modalProyecto": s.nombre_proyecto, "modalDescripcion": s.descripcion_negocio,
        "modalUbicacion": s.ubicacion_emprendimiento, "modalInicio": s.inicio_emprendimiento,
        "modalClientes": s.clientes_clave, "modalProblema": s.problema_resuelve,
        "modalProducto": s.producto_servicio, "modalInnovacion": s.innovacion,
        "modalValor": s.valor_cliente, "modalIdea": s.idea_7_palabras, "modalSat": s.alta_sat,
        "modalPersonasTrabajan": s.personas_trabajan, "modalMiembrosIncubacion": s.miembros_incubacion,
        "modalProgramasPrevios": s.programas_previos, "modalDescripcionLider": s.descripcion_lider,
        "modalRol": s.rol_lider, "modalHabilidades": s.habilidades, "modalLogro": s.logro_asombroso
    };

    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.textContent = dataMap[f] || '';
    });

    const estado = s.estado || "Pendiente";
    const estadoEl = document.getElementById("modalEstado");
    const fechaEl = document.getElementById("modalFecha");

    if (estadoEl) {
        estadoEl.textContent = estado;
        estadoEl.classList.remove("estado-aceptado", "estado-rechazado", "estado-proceso");
        const estLow = estado.toLowerCase();
        if (estLow.includes("acept")) estadoEl.classList.add("estado-aceptado");
        else if (estLow.includes("rechaz")) estadoEl.classList.add("estado-rechazado");
        else estadoEl.classList.add("estado-proceso");
    }
    if (fechaEl) fechaEl.textContent = s.fecha_creacion || '';

    // Integrantes
    const seccionIntegrantes = document.getElementById("seccionIntegrantes");
    const bodyIntegrantes = document.getElementById("modalIntegrantesBody");
    
    if (s.integrantes && s.integrantes.length > 0) {
        if (seccionIntegrantes) seccionIntegrantes.style.display = "block";
        if (bodyIntegrantes) {
            bodyIntegrantes.innerHTML = s.integrantes.map(m => `
                <tr>
                    <td>${m.nombre || '-'}</td>
                    <td>${m.matricula || '-'}</td>
                    <td>${m.correo || '-'}</td>
                    <td>${m.telefono || '-'}</td>
                    <td>${m.carrera || '-'}</td>
                    <td>${m.nivel || '-'}</td>
                    <td>${m.cuatri || '-'}</td>
                </tr>
            `).join('');
        }
    } else {
        if (seccionIntegrantes) seccionIntegrantes.style.display = "none";
        if (bodyIntegrantes) bodyIntegrantes.innerHTML = "";
    }

    mostrarModal('modalDetalle');
}

/* ================================
   ACTUALIZAR ESTADO
================================ */

function actualizarEstado(id, nuevoEstado, password = null, motivo = null) {
    if (!id) {
        window.Toast.show("ID de solicitud no encontrado.", "danger");
        return;
    }
    const payload = { estado: nuevoEstado };
    if (password) payload.password = password;
    if (motivo) payload.motivo = motivo;

    fetch(`/admin/actualizar_estado/${id}/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            cerrarModal('modalDetalle');
            cerrarModal('modalRechazar');
            cerrarModal('modalCredenciales');
            
            const passInput = document.getElementById("nuevaPassword");
            const passError = document.getElementById("errorPassword");
            if (passInput) passInput.value = "";
            if (passError) passError.textContent = "";

            cargarSolicitudes();
            const ok = Number(data.mail_ok || 0);
            const fail = Number(data.mail_fail || 0);
            if (!data.mail_enviado) {
                window.Toast.show(`Estado actualizado, pero falló el envío de correos (ok: ${ok}, fail: ${fail}).`, "warning");
            } else if (fail > 0) {
                window.Toast.show(`Estado actualizado. Correos enviados: ${ok}. Fallidos: ${fail}.`, "warning");
            } else if (ok > 0) {
                window.Toast.show(`Estado actualizado. Correos enviados: ${ok}.`, "success");
            }
        } else if (data.error) {
            window.Toast.show("Error: " + data.error, "danger");
        }
    })
    .catch(err => {
        console.error("Error en actualizarEstado:", err);
        window.Toast.show("Error de conexión al actualizar la solicitud.", "danger");
    });
}

function aceptarDesdeDetalle() {
    cerrarModal('modalDetalle');
    setTimeout(() => {
        mostrarModal('modalCredenciales');
    }, 150);
}

function rechazarDesdeDetalle() {
    cerrarModal('modalDetalle');
    setTimeout(() => {
        mostrarModal('modalRechazar');
        const motInput = document.getElementById("motivoRechazo");
        const motError = document.getElementById("errorMotivo");
        if (motInput) {
            motInput.value = "";
            motInput.classList.remove("input-error");
        }
        if (motError) motError.style.display = "none";
    }, 150);
}

function confirmarRechazo() {
    const motivoEl = document.getElementById("motivoRechazo");
    const errorEl = document.getElementById("errorMotivo");
    const motivo = (motivoEl?.value || "").trim();

    if (!motivo) {
        if (errorEl) errorEl.style.display = "block";
        if (motivoEl) motivoEl.classList.add("input-error");
        return;
    }

    if (motivoEl) motivoEl.classList.remove("input-error");
    if (errorEl) errorEl.style.display = "none";
    actualizarEstado(solicitudActual, "Rechazado", null, motivo);
}

function generarPassword() {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@#$%&*!?";
    let pass = "";
    for (let i = 0; i < 12; i++) {
        pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const passInput = document.getElementById("nuevaPassword");
    const passError = document.getElementById("errorPassword");
    if (passInput) {
        passInput.value = pass;
        passInput.classList.remove("input-error");
    }
    if (passError) passError.textContent = "";
}

function guardarCredenciales() {
    const inputPassword = document.getElementById("nuevaPassword");
    const errorPassword = document.getElementById("errorPassword");
    const password = (inputPassword?.value || "").trim();

    if (password.length < 8) {
        if (errorPassword) errorPassword.textContent = "La contraseña debe tener al menos 8 caracteres.";
        if (inputPassword) inputPassword.classList.add("input-error");
        return;
    }

    if (inputPassword) inputPassword.classList.remove("input-error");
    if (errorPassword) errorPassword.textContent = "";
    actualizarEstado(solicitudActual, "Aceptado", password);
}

/* ================================
   CONTROL MODALES
================================ */

function mostrarModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        document.body.classList.add('modal-open');
        modal.style.display = 'flex';
    }
}

function cerrarModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.display = 'none';
    }

    const hayModalAbierto = Array.from(document.querySelectorAll('.solicitud-modal'))
        .some(m => m.style.display === 'flex');

    if (!hayModalAbierto) {
        document.body.classList.remove('modal-open');
    }
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// Exportar funciones al objeto window para acceso desde HTML onclick
window.abrirModalDetalleCompleto = abrirModalDetalleCompleto;
window.aceptarDesdeDetalle = aceptarDesdeDetalle;
window.rechazarDesdeDetalle = rechazarDesdeDetalle;
window.confirmarRechazo = confirmarRechazo;
window.generarPassword = generarPassword;
window.guardarCredenciales = guardarCredenciales;
window.mostrarModal = mostrarModal;
window.cerrarModal = cerrarModal;
window.actualizarEstado = actualizarEstado;
