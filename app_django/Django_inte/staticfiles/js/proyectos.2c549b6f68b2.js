(() => {
  const lista = document.getElementById("listaProyectos");
  const total = document.getElementById("totalProyectos");
  const filtroEstado = document.getElementById("filtroEstado");
  const filtroTexto = document.getElementById("filtroTexto");
  const btnRecargar = document.getElementById("btnRecargar");
  const btnBaja = document.getElementById("btnBaja");
  const btnEliminar = document.getElementById("btnEliminar");
  const detalle = {
    nombre: document.getElementById("detalleNombre"),
    estado: document.getElementById("detalleEstado"),
    emprendedor: document.getElementById("detalleEmprendedor"),
    correo: document.getElementById("detalleCorreo"),
    fecha: document.getElementById("detalleFecha"),
    equipo: document.getElementById("detalleEquipo"),
    descripcion: document.getElementById("detalleDescripcion"),
    motivo: document.getElementById("detalleMotivo"),
  };

  const btnFinalizar = document.getElementById("btnFinalizar");

  // Modal finalizar
  const modalFinalizar = document.getElementById("modalFinalizar");
  const formFinalizar = document.getElementById("formFinalizar");
  const btnCerrarFinalizar = modalFinalizar ? modalFinalizar.querySelectorAll("[data-action='close-finalizar']") : [];
  const finalizarStatus = document.getElementById("finalizarStatus");
  const btnConfirmarFinalizar = document.getElementById("btnConfirmarFinalizar");

  // Modal baja
  const modal = document.getElementById("modalBaja");
  const btnCerrarModal = modal.querySelectorAll("[data-action='close']");
  const confirmarBaja = document.getElementById("confirmarBaja");
  const estadoNuevo = document.getElementById("estadoNuevo");
  const motivoBaja = document.getElementById("motivoBaja");

  // Modal eliminar
  const modalEliminar = document.getElementById("modalEliminar");
  const btnCerrarEliminar = modalEliminar.querySelectorAll("[data-action='close-delete']");
  const confirmarEliminar = document.getElementById("confirmarEliminar");
  const inputConfirmEliminar = document.getElementById("inputConfirmEliminar");
  const elimNombreProyecto = document.getElementById("elimNombreProyecto");

  // Modal éxito
  const modalExito = document.getElementById("modalExito");
  const btnCerrarExito = document.getElementById("btnCerrarExito");
  const exitoMensaje = document.getElementById("exitoMensaje");

  const stateChip = (estado) => {
    const map = { Activo: "ok", Finalizado: "warn", Inactivo: "bad" };
    const cls = map[estado] || "";
    return `<span class="chip ${cls}">${estado || "—"}</span>`;
  };

  let proyectos = [];
  let seleccionado = null;

  async function cargarProyectos() {
    lista.innerHTML = "<div class='skeleton-list'><div class='skeleton-row'></div><div class='skeleton-row'></div><div class='skeleton-row'></div></div>";
    try {
      const res = await fetch("/admin/proyectos/api/");
      const data = await res.json();
      proyectos = (data.proyectos || []).sort((a, b) =>
        (a.nombre_proyecto || "").localeCompare(b.nombre_proyecto || "", "es", { sensitivity: "base" })
      );
      renderLista();
    } catch (e) {
      lista.innerHTML = "<div class='muted'>No se pudo cargar la lista.</div>";
      Toast?.show?.("No se pudo cargar proyectos", "warn");
      console.error(e);
    }
  }

  function renderLista() {
    const filtro = filtroEstado.value;
    const texto = (filtroTexto.value || "").toLowerCase().trim();
    const filtrados = proyectos.filter((p) => {
      const matchEstado = filtro === "todos" || p.estado === filtro;
      const hayTexto = !texto || (p.nombre_proyecto || "").toLowerCase().includes(texto) || (p.usuario?.nombre || "").toLowerCase().includes(texto);
      return matchEstado && hayTexto;
    });
    total.textContent = `${filtrados.length} proyecto${filtrados.length === 1 ? "" : "s"}`;

    if (!filtrados.length) {
      lista.innerHTML = "<div class='muted'>No hay proyectos con ese estado.</div>";
      return;
    }

    lista.innerHTML = filtrados
      .map(
        (p) => `
      <article class="project-row ${p.id === seleccionado ? "active" : ""}" data-id="${p.id}">
        <div class="project-meta">
          <h4>${p.nombre_proyecto}</h4>
          <div class="muted">${p.usuario?.nombre || "Emprendedor"}</div>
          <div class="muted">Actualizado ${p.ultima_actualizacion || "—"}</div>
          <div class="team-badge-small"><i class="bi bi-people"></i> ${p.integrantes?.length || 0} integrantes</div>
        </div>
        ${stateChip(p.estado)}
      </article>`
      )
      .join("");
  }

  function seleccionar(id) {
    seleccionado = id;
    renderLista();
    const proyecto = proyectos.find((p) => p.id === id);
    if (!proyecto) return;

    detalle.nombre.textContent = proyecto.nombre_proyecto;
    detalle.estado.innerHTML = `${stateChip(proyecto.estado)} <span class="muted">${proyecto.ultima_actualizacion || ""}</span>`;
    detalle.emprendedor.textContent = proyecto.usuario?.nombre || "—";
    detalle.correo.textContent = proyecto.usuario?.correo || "—";
    detalle.fecha.textContent = proyecto.ultima_actualizacion || "—";
    
    const integrantes = proyecto.integrantes || [];
    if (integrantes.length > 0) {
        let tabla = `<div class='team-table'>
            <table>
                <thead>
                    <tr><th>Nombre</th><th>Carrera</th><th>Correo</th></tr>
                </thead>
                <tbody>
                    ${integrantes.map(i => `<tr>
                        <td>${i.nombre || i.nombre_completo || "—"}</td>
                        <td>${i.carrera || "—"}</td>
                        <td>${i.correo || "—"}</td>
                    </tr>`).join("")}
                </tbody>
            </table>
        </div>`;
        detalle.equipo.innerHTML = tabla;
    } else {
        detalle.equipo.textContent = proyecto.resumen?.equipo || "Líder individual";
    }

    detalle.descripcion.textContent = proyecto.resumen?.descripcion || "Sin descripción";
    detalle.motivo.textContent = proyecto.motivo_baja || "Sin registro";

    btnBaja.disabled = false;
    btnFinalizar.disabled = (proyecto.estado || "").toLowerCase() === "finalizado";
    btnEliminar.disabled = false;
  }

  // ========== Modal BAJA ==========
  function abrirModal() {
    if (!seleccionado) return;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
  }

  function cerrarModal() {
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    motivoBaja.value = "";
  }

  async function guardarBaja() {
    if (!seleccionado) return;
    confirmarBaja.disabled = true;
    try {
      const res = await fetch(`/admin/proyectos/api/${seleccionado}/estado/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estado: estadoNuevo.value,
          motivo: motivoBaja.value.trim(),
        }),
      });
      if (!res.ok) throw new Error("Error al actualizar estado");
      const data = await res.json();
      proyectos = proyectos.map((p) => (p.id === data.proyecto.id ? data.proyecto : p));
      renderLista();
      seleccionar(data.proyecto.id);
      cerrarModal();
    } catch (e) {
      window.Toast?.show?.("No se pudo guardar el cambio.", "danger");
      console.error(e);
    } finally {
      confirmarBaja.disabled = false;
    }
  }

  // ========== Modal FINALIZAR ==========
  function abrirModalFinalizar() {
    if (!seleccionado) return;
    modalFinalizar.classList.add("show");
    modalFinalizar.setAttribute("aria-hidden", "false");
  }

  function cerrarModalFinalizar() {
    modalFinalizar.classList.remove("show");
    modalFinalizar.setAttribute("aria-hidden", "true");
    formFinalizar.reset();
    finalizarStatus.style.display = "none";
    btnConfirmarFinalizar.disabled = false;
  }

  async function ejecutarFinalizar(e) {
    e.preventDefault();
    if (!seleccionado) return;

    const formData = new FormData(formFinalizar);
    btnConfirmarFinalizar.disabled = true;
    finalizarStatus.style.display = "block";

    try {
      const res = await fetch(`/admin/proyectos/api/${seleccionado}/finalizar/`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Error al finalizar");

      Toast?.show?.("Proyecto finalizado y certificados enviados", "ok");
      
      // Recargar para ver el cambio de estado
      await cargarProyectos();
      seleccionar(seleccionado);
      cerrarModalFinalizar();
    } catch (e) {
      window.Toast?.show?.("Error al finalizar el proyecto.", "danger");
      console.error(e);
      btnConfirmarFinalizar.disabled = false;
      finalizarStatus.style.display = "none";
    }
  }

  // ========== Modal ELIMINAR ==========
  function abrirModalEliminar() {
    if (!seleccionado) return;
    const proyecto = proyectos.find(p => p.id === seleccionado);
    elimNombreProyecto.textContent = proyecto?.nombre_proyecto || "este proyecto";
    inputConfirmEliminar.value = "";
    confirmarEliminar.disabled = true;
    modalEliminar.classList.add("show");
    modalEliminar.setAttribute("aria-hidden", "false");
  }

  function cerrarModalEliminar() {
    modalEliminar.classList.remove("show");
    modalEliminar.setAttribute("aria-hidden", "true");
    inputConfirmEliminar.value = "";
    confirmarEliminar.disabled = true;
  }

  inputConfirmEliminar.addEventListener("input", () => {
    confirmarEliminar.disabled = inputConfirmEliminar.value.trim().toUpperCase() !== "ELIMINAR";
  });

  async function ejecutarEliminar() {
    if (!seleccionado) return;
    confirmarEliminar.disabled = true;
    confirmarEliminar.textContent = "Eliminando...";
    try {
      const res = await fetch(`/admin/proyectos/api/${seleccionado}/eliminar/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Error al eliminar");
      const data = await res.json();
      
      cerrarModalEliminar();
      
      // Mostrar modal de éxito
      exitoMensaje.textContent = `Se eliminaron ${data.usuarios_eliminados || 0} cuenta(s) de usuario y todos los datos asociados al proyecto.`;
      modalExito.classList.add("show");
      modalExito.setAttribute("aria-hidden", "false");
      
      proyectos = proyectos.filter(p => p.id !== seleccionado);
      seleccionado = null;
      renderLista();
      
      // Limpiar detalle
      detalle.nombre.textContent = "Selecciona un proyecto";
      detalle.estado.innerHTML = '<span class="chip">—</span> <span class="muted">Sin selección</span>';
      detalle.emprendedor.textContent = "—";
      detalle.correo.textContent = "—";
      detalle.fecha.textContent = "—";
      detalle.equipo.textContent = "—";
      detalle.descripcion.textContent = "Selecciona un proyecto para ver su resumen.";
      detalle.motivo.textContent = "Sin registro";
      btnBaja.disabled = true;
      btnEliminar.disabled = true;
      
    } catch (e) {
      window.Toast?.show?.("No se pudo eliminar el proyecto.", "danger");
      console.error(e);
    } finally {
      confirmarEliminar.disabled = false;
      confirmarEliminar.textContent = "Eliminar definitivamente";
    }
  }

  function cerrarModalExito() {
    modalExito.classList.remove("show");
    modalExito.setAttribute("aria-hidden", "true");
  }

  // ========== Eventos ==========
  lista.addEventListener("click", (e) => {
    const row = e.target.closest(".project-row");
    if (row) seleccionar(row.dataset.id);
  });

  filtroEstado.addEventListener("change", renderLista);
  filtroTexto.addEventListener("input", renderLista);
  btnRecargar.addEventListener("click", cargarProyectos);
  btnBaja.addEventListener("click", abrirModal);
  btnFinalizar.addEventListener("click", abrirModalFinalizar);
  btnEliminar.addEventListener("click", abrirModalEliminar);
  confirmarBaja.addEventListener("click", guardarBaja);
  formFinalizar.addEventListener("submit", ejecutarFinalizar);
  confirmarEliminar.addEventListener("click", ejecutarEliminar);
  btnCerrarExito.addEventListener("click", cerrarModalExito);
  btnCerrarModal.forEach((b) => b.addEventListener("click", cerrarModal));
  btnCerrarFinalizar.forEach((b) => b.addEventListener("click", cerrarModalFinalizar));
  btnCerrarEliminar.forEach((b) => b.addEventListener("click", cerrarModalEliminar));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) cerrarModal();
  });
  modalEliminar.addEventListener("click", (e) => {
    if (e.target === modalEliminar) cerrarModalEliminar();
  });
  modalExito.addEventListener("click", (e) => {
    if (e.target === modalExito) cerrarModalExito();
  });

  cargarProyectos();
})();
