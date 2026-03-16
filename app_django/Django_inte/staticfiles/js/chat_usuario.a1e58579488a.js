(function () {
    const app = document.getElementById("chatUsuarioApp");
    if (!app) return;

    const messagesEl = document.getElementById("chatUsuarioMessages");
    const form = document.getElementById("chatUsuarioForm");
    const input = document.getElementById("chatUsuarioInput");
    const fileInput = document.getElementById("chatUsuarioFile");
    const previewEl = document.getElementById("chatUsuarioPreview");
    const emojiBtn = document.getElementById("emojiUsuarioBtn");
    const emojiPicker = document.getElementById("emojiUsuarioPicker");
    const projectTitleEl = document.getElementById("currentProjectTitle");

    const messagesUrl = app.dataset.messagesUrl;
    const sendUrl = app.dataset.sendUrl;
    const editUrlTemplate = app.dataset.editUrlTemplate;
    const deleteUrlTemplate = app.dataset.deleteUrlTemplate;
    
    let currentProjectId = app.dataset.currentProjectId;
    let lastSerialized = "";

    function buildUrl(template, id) {
        return template.replace("MSG_ID", id);
    }

    function escapeHtml(text) {
        return String(text)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function renderAttachment(m) {
        if (!m.adjunto) return "";
        if ((m.adjunto_tipo || "").startsWith("image/")) {
            return `<a href="${escapeHtml(m.adjunto_url)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHtml(m.adjunto_url)}" alt="${escapeHtml(m.adjunto_nombre)}" style="max-width:100%; border-radius:12px; margin-top:10px; display:block;"></a>`;
        }
        return `<a href="${escapeHtml(m.adjunto_url)}" target="_blank" rel="noopener noreferrer" style="display:block; margin-top:10px; color:inherit; text-decoration:underline;">📎 ${escapeHtml(m.adjunto_nombre || "Archivo adjunto")}</a>`;
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
        let previewHtml = `<div style="padding:15px; background:hsla(0,0%,100%,0.8); border-top:1px solid #ddd; display:flex; align-items:center; gap:15px;">`;
        if (file.type.startsWith("image/")) {
            const objectUrl = URL.createObjectURL(file);
            previewHtml += `<img src="${objectUrl}" style="width:40px; height:40px; border-radius:8px; object-fit:cover;">`;
        } else {
            previewHtml += `<span>📄 ${escapeHtml(file.name)}</span>`;
        }
        previewHtml += `<button type="button" id="chatUsuarioRemoveAttach" style="margin-left:auto; border:none; background:#eee; padding:5px 10px; border-radius:6px; cursor:pointer;">Quitar</button></div>`;

        previewEl.innerHTML = previewHtml;
        previewEl.hidden = false;

        document.getElementById("chatUsuarioRemoveAttach").onclick = () => {
            fileInput.value = "";
            clearAttachPreview();
        };
    }

    function renderMessages(messages) {
        if (!messages.length) {
            messagesEl.innerHTML = '<p style="text-align:center; opacity:0.5; margin-top:20px;">Sin mensajes por ahora.</p>';
            return;
        }
        const serialized = JSON.stringify(messages.map((m) => [m.id, m.mensaje, m.hora, m.editado, m.adjunto_nombre]));
        if (serialized === lastSerialized) return;
        lastSerialized = serialized;

        messagesEl.innerHTML = messages.map((m) => `
            <article class="chat-user-bubble ${m.es_mio ? "mine" : "theirs"}">
                <span class="chat-user-sender">${escapeHtml(m.emisor_nombre)}</span>
                <div>${escapeHtml(m.mensaje || "")}</div>
                ${renderAttachment(m)}
                <small class="chat-user-meta">
                    ${escapeHtml(m.hora || "")} ${m.editado ? "· editado" : ""}
                </small>
                ${m.puede_editar || m.puede_eliminar ? `
                <div class="chat-user-actions">
                    ${m.puede_editar ? `<button type="button" class="user-edit" data-id="${escapeHtml(m.id)}" data-text="${escapeHtml(m.mensaje || "")}">Editar</button>` : ""}
                    ${m.puede_eliminar ? `<button type="button" class="user-delete" data-id="${escapeHtml(m.id)}">Eliminar</button>` : ""}
                </div>` : ""}
            </article>
        `).join("");

        messagesEl.querySelectorAll(".user-edit").forEach((btn) => {
            btn.onclick = () => openEditModal(btn.dataset.id, btn.dataset.text || "");
        });
        messagesEl.querySelectorAll(".user-delete").forEach((btn) => {
            btn.onclick = () => openDeleteModal(btn.dataset.id);
        });
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function loadMessages() {
        if (!currentProjectId) return;
        const res = await fetch(`${messagesUrl}?proyecto_id=${currentProjectId}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        renderMessages(data.mensajes || []);
    }

    /* --- Modals logic (Sync with admin) --- */
    let currentMsgId = null;
    const modalEdit = document.getElementById("modalEditUsuario");
    const editInput = document.getElementById("editUsuarioInput");
    const modalDelete = document.getElementById("modalDeleteUsuario");

    window.openEditModal = function(id, text) {
        currentMsgId = id;
        editInput.value = text;
        modalEdit.hidden = false;
        modalEdit.classList.add("active");
        editInput.focus();
    };
    window.closeEditModal = function() {
        modalEdit.hidden = true;
        modalEdit.classList.remove("active");
        currentMsgId = null;
    };
    window.saveEditMessage = async function() {
        const nuevo = editInput.value.trim();
        if (!nuevo || !currentMsgId) return;
        const res = await fetch(buildUrl(editUrlTemplate, currentMsgId), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mensaje: nuevo })
        });
        if (res.ok) { closeEditModal(); loadMessages(); }
    };

    window.openDeleteModal = function(id) {
        currentMsgId = id;
        modalDelete.hidden = false;
        modalDelete.classList.add("active");
    };
    window.closeDeleteModal = function() {
        modalDelete.hidden = true;
        modalDelete.classList.remove("active");
        currentMsgId = null;
    };
    window.confirmDeleteMessage = async function() {
        if (!currentMsgId) return;
        const res = await fetch(buildUrl(deleteUrlTemplate, currentMsgId), { method: "POST" });
        if (res.ok) { closeDeleteModal(); loadMessages(); }
    };

    [modalEdit, modalDelete].forEach(m => {
        m.addEventListener("click", (e) => { if (e.target === m) { closeEditModal(); closeDeleteModal(); } });
    });

    emojiBtn.onclick = () => emojiPicker.hidden = !emojiPicker.hidden;
    emojiPicker.querySelectorAll("button").forEach(b => {
        b.onclick = () => { input.value += b.textContent; input.focus(); };
    });
    fileInput.onchange = () => renderAttachPreview(fileInput.files[0]);

    form.onsubmit = async (e) => {
        e.preventDefault();
        const msg = input.value.trim();
        const file = fileInput.files[0];
        if (!msg && !file) return;

        const payload = new FormData();
        payload.append("mensaje", msg);
        if (currentProjectId) payload.append("proyecto_id", currentProjectId);
        if (file) payload.append("archivo", file);

        const res = await fetch(sendUrl, { method: "POST", body: payload });
        if (res.ok) {
            input.value = ""; fileInput.value = ""; clearAttachPreview();
            emojiPicker.hidden = true; loadMessages();
        }
    };

    document.addEventListener("click", (e) => {
        if (!emojiPicker.hidden && !emojiPicker.contains(e.target) && e.target !== emojiBtn) emojiPicker.hidden = true;
    });

    loadMessages();
    setInterval(loadMessages, 3000);
})();
