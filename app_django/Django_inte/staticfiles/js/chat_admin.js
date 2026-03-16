(function () {
    const app = document.getElementById("chatAdminApp");
    if (!app) return;

    const listEl = document.getElementById("conversationList");
    const chatEl = document.getElementById("chatMessages");
    const withNameEl = document.getElementById("chatWithName");
    const withLeaderEl = document.getElementById("chatWithLeader");
    const form = document.getElementById("chatAdminForm");
    const input = document.getElementById("chatAdminInput");
    const fileInput = document.getElementById("chatAdminFile");
    const previewEl = document.getElementById("chatAdminPreview");
    const emojiBtn = document.getElementById("emojiAdminBtn");
    const emojiPicker = document.getElementById("emojiAdminPicker");

    const convoUrl = app.dataset.conversationsUrl;
    const msgUrlTemplate = app.dataset.messagesUrlTemplate;
    const sendUrlTemplate = app.dataset.sendUrlTemplate;
    const editUrlTemplate = app.dataset.editUrlTemplate;
    const deleteUrlTemplate = app.dataset.deleteUrlTemplate;

    let currentProjectId = app.dataset.initialUser || "";
    let currentProjectName = "";
    let currentLeaderName = "";
    let lastSerialized = "";

    function buildUrl(template, id) {
        return template.replace("USER_ID", id).replace("MSG_ID", id);
    }

    function escapeHtml(text) {
        return String(text)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function bindConversationButtons() {
        listEl.querySelectorAll(".conversation-item").forEach((btn) => {
            btn.onclick = () => {
                currentProjectId = btn.dataset.projectId;
                currentProjectName = btn.dataset.userName || "Proyecto";
                currentLeaderName = btn.dataset.leader || "Sin líder";
                lastSerialized = "";
                chatEl.innerHTML = '<p class="chat-placeholder">Cargando mensajes...</p>';
                updateConversationSelection();
                loadMessages();
            };
        });
    }

    function updateConversationSelection() {
        listEl.querySelectorAll(".conversation-item").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.projectId === currentProjectId);
        });
        withNameEl.textContent = currentProjectName || "Selecciona un proyecto";
        if (withLeaderEl) {
            withLeaderEl.querySelector("span").textContent = currentLeaderName || "-";
        }
    }

    function renderAttachment(m) {
        if (!m.adjunto) return "";
        if ((m.adjunto_tipo || "").startsWith("image/")) {
            return `<a href="${escapeHtml(m.adjunto_url)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHtml(m.adjunto_url)}" alt="${escapeHtml(m.adjunto_nombre)}" class="chat-image"></a>`;
        }
        return `<a href="${escapeHtml(m.adjunto_url)}" target="_blank" rel="noopener noreferrer" class="chat-file-link">📎 ${escapeHtml(m.adjunto_nombre || "Archivo adjunto")}</a>`;
    }

    function clearAttachPreview() {
        previewEl.innerHTML = "";
        previewEl.hidden = true;
    }

    function renderAttachPreview(file) {
        if (!file) {
            clearAttachPreview();
            return;
        }

        let previewHtml = `<div class="chat-attach-card">`;
        if (file.type.startsWith("image/")) {
            const objectUrl = URL.createObjectURL(file);
            previewHtml += `<img src="${objectUrl}" class="chat-attach-thumb" alt="Vista previa">`;
        } else {
            previewHtml += `<div class="chat-attach-meta">📄 ${escapeHtml(file.name)}</div>`;
        }
        previewHtml += `
            <div class="chat-attach-meta">${escapeHtml(file.name)}</div>
            <button type="button" class="chat-attach-remove" id="chatAdminRemoveAttach">Quitar archivo</button>
        </div>`;

        previewEl.innerHTML = previewHtml;
        previewEl.hidden = false;

        const removeBtn = document.getElementById("chatAdminRemoveAttach");
        if (removeBtn) {
            removeBtn.onclick = () => {
                fileInput.value = "";
                clearAttachPreview();
            };
        }
    }

    function renderMessages(messages) {
        if (!messages.length) {
            chatEl.innerHTML = '<p class="chat-placeholder">Sin mensajes por ahora.</p>';
            return;
        }

        const serialized = JSON.stringify(messages.map((m) => [m.id, m.mensaje, m.hora, m.editado, m.adjunto_nombre]));
        if (serialized === lastSerialized) return;
        lastSerialized = serialized;

        chatEl.innerHTML = messages.map((m) => `
            <article class="chat-bubble ${m.es_mio ? "mine" : "theirs"}">
                <div>${escapeHtml(m.mensaje || "")}</div>
                ${renderAttachment(m)}
                <small class="chat-meta">
                    ${escapeHtml(m.emisor_nombre)} · ${escapeHtml(m.hora || "")} ${m.editado ? "· editado" : ""}
                </small>
                ${m.puede_editar || m.puede_eliminar ? `
                <div class="chat-message-tools">
                    ${m.puede_editar ? `<button type="button" class="msg-edit" data-id="${escapeHtml(m.id)}" data-text="${escapeHtml(m.mensaje || "")}">Editar</button>` : ""}
                    ${m.puede_eliminar ? `<button type="button" class="msg-delete" data-id="${escapeHtml(m.id)}">Eliminar</button>` : ""}
                </div>` : ""}
            </article>
        `).join("");

        chatEl.querySelectorAll(".msg-edit").forEach((btn) => {
            btn.onclick = () => openEditModal(btn.dataset.id, btn.dataset.text || "");
        });

        chatEl.querySelectorAll(".msg-delete").forEach((btn) => {
            btn.onclick = () => openDeleteModal(btn.dataset.id);
        });

        chatEl.scrollTop = chatEl.scrollHeight;
    }

    /* --- Premium Modal Logic Admin --- */
    let currentMsgId = null;
    const modalEdit = document.getElementById("modalEditAdmin");
    const editInput = document.getElementById("editAdminInput");
    const modalDelete = document.getElementById("modalDeleteAdmin");

    window.openEditModal = function(id, text) {
        currentMsgId = id;
        editInput.value = text;
        modalEdit.classList.add("active");
        editInput.focus();
    };

    window.closeEditModal = function() {
        modalEdit.classList.remove("active");
        currentMsgId = null;
    };

    window.saveEditMessage = async function() {
        const nuevo = editInput.value.trim();
        if (!nuevo || !currentMsgId) return;
        
        try {
            const res = await fetch(buildUrl(editUrlTemplate, currentMsgId), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mensaje: nuevo })
            });
            if (res.ok) {
                closeEditModal();
                loadMessages();
            }
        } catch (err) {
            console.error("Edit error:", err);
        }
    };

    window.openDeleteModal = function(id) {
        currentMsgId = id;
        modalDelete.classList.add("active");
    };

    window.closeDeleteModal = function() {
        modalDelete.classList.remove("active");
        currentMsgId = null;
    };

    // Close on overlay click
    [modalEdit, modalDelete].forEach(m => {
        m.addEventListener("click", (e) => {
            if (e.target === m) {
                closeEditModal();
                closeDeleteModal();
            }
        });
    });

    window.confirmDeleteMessage = async function() {
        if (!currentMsgId) return;
        try {
            const res = await fetch(buildUrl(deleteUrlTemplate, currentMsgId), { method: "POST" });
            if (res.ok) {
                closeDeleteModal();
                loadMessages();
            }
        } catch (err) {
            console.error("Delete error:", err);
        }
    };

    async function loadMessages() {
        if (!currentProjectId) return;
        const res = await fetch(buildUrl(msgUrlTemplate, currentProjectId));
        if (!res.ok) return;
        const data = await res.json();
        renderMessages(data.mensajes || []);
    }

    async function loadConversations(keepCurrent) {
        const res = await fetch(convoUrl);
        if (!res.ok) return;
        const data = await res.json();
        const conversaciones = data.conversaciones || [];

        listEl.innerHTML = conversaciones.length ? conversaciones.map((c) => `
            <button type="button" class="conversation-item" 
                data-project-id="${escapeHtml(c.id)}" 
                data-user-name="${escapeHtml(c.proyecto_nombre)}"
                data-leader="${escapeHtml(c.lider)}"
            >
                <div class="conversation-main">
                    <span class="conversation-name">${escapeHtml(c.proyecto_nombre)}</span>
                    <span class="conversation-mail">Líder: ${escapeHtml(c.lider || "Sin líder")}</span>
                </div>
                <div class="conversation-preview">
                    <span>${escapeHtml(c.ultimo_mensaje || "Sin mensajes")}</span>
                    <small>${escapeHtml(c.hora_ultimo_mensaje || "")}</small>
                </div>
            </button>
        `).join("") : '<p class="conversation-empty">No hay proyectos activos.</p>';

        bindConversationButtons();
        if (!conversaciones.length) {
            currentProjectId = "";
            currentProjectName = "";
            updateConversationSelection();
            return;
        }

        if (!keepCurrent || !conversaciones.some((c) => c.id === currentProjectId)) {
            currentProjectId = conversaciones[0].id;
            currentProjectName = conversaciones[0].proyecto_nombre;
            currentLeaderName = conversaciones[0].lider;
        } else {
            const actual = conversaciones.find((c) => c.id === currentProjectId);
            currentProjectName = actual ? actual.proyecto_nombre : currentProjectName;
            currentLeaderName = actual ? actual.lider : currentLeaderName;
        }
        updateConversationSelection();
    }

    emojiBtn.addEventListener("click", () => {
        emojiPicker.hidden = !emojiPicker.hidden;
    });

    emojiPicker.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
            input.value += btn.textContent;
            input.focus();
        });
    });

    document.addEventListener("click", (event) => {
        if (!emojiPicker.hidden && !emojiPicker.contains(event.target) && event.target !== emojiBtn) {
            emojiPicker.hidden = true;
        }
    });

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        renderAttachPreview(file);
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const mensaje = input.value.trim();
        const archivo = fileInput.files[0];
        
        if (!currentProjectId) {
            window.Toast.show("No hay un proyecto seleccionado.", "danger");
            return;
        }
        if (!mensaje && !archivo) return;

        const payload = new FormData();
        payload.append("mensaje", mensaje);
        if (archivo) payload.append("archivo", archivo);

        try {
            const url = buildUrl(sendUrlTemplate, currentProjectId);
            console.log("Sending to:", url, "ProjectId:", currentProjectId);
            const res = await fetch(url, {
                method: "POST",
                body: payload
            });
            if (!res.ok) {
                const errorText = await res.text();
                console.error("Chat send error:", res.status, errorText);
                window.Toast.show("Error al enviar mensaje.", "danger");
                return;
            }

            input.value = "";
            fileInput.value = "";
            clearAttachPreview();
            emojiPicker.hidden = true;
            await loadMessages();
            await loadConversations(true);
        } catch (err) {
            console.error("Chat send exception:", err);
            window.Toast.show("Error de conexión al enviar mensaje.", "danger");
        }
    });

    (async function init() {
        await loadConversations(Boolean(currentProjectId));
        await loadMessages();
        setInterval(loadMessages, 2200);
        setInterval(() => loadConversations(true), 7000);
    })();
})();
