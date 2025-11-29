const form = document.getElementById('loginForm');

const username = document.getElementById('username');
const password = document.getElementById('password');


// Comenzar en el primer campo
document.addEventListener('DOMContentLoaded', function () {
    username.focus();
});


form.addEventListener('submit', function (event) {
    event.preventDefault(); // Prevenir el envío del formulario

    let valid = true;
    // Validar campo de usuario
    if (username.value.trim() === '') {
        showClientMessage('El campo de usuario no puede estar vacío.','warning');
        username.focus();
        valid = false;
        return;
    // validar que no tenga caracteres especiales
    } else if (!/^[a-zA-Z0-9]+$/.test(username.value)) {
        showClientMessage('El campo de usuario no puede contener caracteres especiales.','warning');
        username.focus();
        valid = false;
        return;
    }
    // Validar contraseña no esté vacía
    if (password.value.trim() === '') {
        showClientMessage('El campo de contraseña no puede estar vacío.','warning');
        password.focus();
        valid = false;
        return;
    }
    
    //redireccionar en caso de ser valido
    if (valid) {
        // Enviar el formulario al servidor para que use Django messages / autenticación
        const datos ={
            'username': username.value.trim(),
            'password': password.value.trim(),
        }

        // Obtener CSRF token desde cookie y enviarlo en la cabecera
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }
        const csrftoken = getCookie('csrftoken');

        $.ajax({
            url: '/usuarios/login/',
            type: 'POST',
            data: JSON.stringify(datos),
            contentType: 'application/json',
            beforeSend: function (xhr) {
                if (csrftoken) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                }
            },
            success: function (response) {
                // En caso de éxito, redirigir a main
                window.location.href = '/main';
            },
            error: function (xhr, status, error) {
                let res = null;
                try { res = JSON.parse(xhr.responseText); } catch(e){}
                const msg = res?.error || 'Error en la conexión al servidor.';
                showClientMessage(msg, 'danger');
            }
        });

    }
});


/**
 * Inserta un alert de Bootstrap en el contenedor `#client-messages`.
 * type: 'warning'|'danger'|'success'|'info' etc.
 */
function showClientMessage(message, type = 'warning') {
    const container = document.getElementById('client-messages');
    if (!container) {
        // fallback al alert del navegador si no existe el contenedor
        alert(message);
        return;
    }
    // limpiar mensajes previos
    container.innerHTML = '';

    const div = document.createElement('div');
    div.className = `alert alert-${type} alert-dismissible fade show`;
    div.setAttribute('role', 'alert');
    div.innerHTML = `${message}`;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-close';
    btn.setAttribute('data-bs-dismiss', 'alert');
    btn.setAttribute('aria-label', 'Close');

    div.appendChild(btn);
    container.appendChild(div);
}
