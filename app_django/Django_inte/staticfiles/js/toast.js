(function(){
  const container = document.getElementById("toastContainer");
  if (!container) return;

  function showToast(message, type="info", timeout=3500){
    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    toast.role = "status";
    
    let icon = "bi-info-circle";
    if (type === "success") icon = "bi-check-circle-fill";
    if (type === "danger") icon = "bi-exclamation-triangle-fill";
    if (type === "warning") icon = "bi-exclamation-circle-fill";

    toast.innerHTML = `<i class="bi ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    
    requestAnimationFrame(()=> toast.classList.add("show"));
    setTimeout(()=> {
      toast.classList.remove("show");
      setTimeout(()=> toast.remove(), 400);
    }, timeout);
  }

  window.Toast = { show: showToast };
})();
