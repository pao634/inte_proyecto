
let usuarioSeleccionado = null
let accionBloquear = true


function abrirModal(id, bloquear){

    usuarioSeleccionado = id
    accionBloquear = bloquear

    document.getElementById("modalConfirmacion").style.display = "flex"

    if(bloquear){
        document.getElementById("textoModal").innerText = "¿Deseas bloquear este usuario?"
    }else{
        document.getElementById("textoModal").innerText = "¿Deseas desbloquear este usuario?"
    }

}


function cerrarModal(){
    document.getElementById("modalConfirmacion").style.display = "none"
}


function confirmarCambio(){

    /* Django genera la ruta correcta */
    let url = "{% url 'cambiar_estado_usuario' 'TEMP_ID' %}".replace("TEMP_ID", usuarioSeleccionado)

    fetch(url, {

        method: "POST",

        headers:{
            "Content-Type":"application/json",
            "X-CSRFToken":"{{ csrf_token }}"
        }

    })

    .then(response => {

        if(!response.ok){
            throw new Error("Error en la petición")
        }

        return response.json()

    })

    .then(data => {

        if(data.success){

            const estado = document.getElementById("estado-" + usuarioSeleccionado)
            const accion = document.getElementById("accion-" + usuarioSeleccionado)

            if(data.activo){

                estado.innerHTML = `
                <span class="badge-activo">
                <i class="bi bi-check-circle"></i> Activo
                </span>
                `

                accion.innerHTML = `
                <button class="btn-bloquear" onclick="abrirModal('${usuarioSeleccionado}',true)">
                <i class="bi bi-lock"></i> Bloquear
                </button>
                `

            }else{

                estado.innerHTML = `
                <span class="badge-bloqueado">
                <i class="bi bi-lock"></i> Bloqueado
                </span>
                `

                accion.innerHTML = `
                <button class="btn-desbloquear" onclick="abrirModal('${usuarioSeleccionado}',false)">
                <i class="bi bi-unlock"></i> Desbloquear
                </button>
                `

            }

            cerrarModal()

        }else{
            window.Toast.show("No se pudo cambiar el estado del usuario", "danger")
        }

    })

    .catch(error => {
        console.error("Error:", error)
        window.Toast.show("Ocurrió un error al cambiar el estado", "danger")
    })

}
