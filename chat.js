let ultimoId = 0;
let atencionId = null;

function initChat(id, ultimo) {
    atencionId = id;   // puede venir null si aún no hay atención
    ultimoId = ultimo;
    obtenerMensajes(); // primera carga inmediata
    setInterval(obtenerMensajes, 3000); // refresco cada 3s
}

function enviarMensaje() {
    const input = document.getElementById('input-mensaje');
    if (!input) {
        console.error('No se encontró #input-mensaje');
        alert('No se encontró el campo de texto.');
        return;
    }

    const texto = input.value.trim();
    if (!texto) return;

    // Enviar aunque atencionId sea null → el backend la crea
    fetch('/api/enviar-mensaje', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            atencion_id: atencionId || null,
            mensaje: texto
        })
    })
    .then(async (res) => {
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Error ${res.status}: ${errText}`);
        }
        return res.json();
    })
    .then((data) => {
        // Si el backend creó una nueva atención, actualizar atencionId
        if (data.atencion_id) {
            atencionId = data.atencion_id;
        }
        agregarMensaje(data);
        input.value = '';
    })
    .catch((e) => {
        console.error('Fallo al enviar:', e);
        alert('No se pudo enviar el mensaje. Revisa la consola.');
    });
}

function obtenerMensajes() {
    if (!atencionId) return; // si aún no hay atención, no pedir mensajes

    fetch(`/api/obtener-mensajes/${atencionId}?ultimo_id=${ultimoId}`)
        .then(async (res) => {
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Error ${res.status}: ${errText}`);
            }
            return res.json();
        })
        .then((data) => {
            data.forEach((m) => agregarMensaje(m));
        })
        .catch((e) => console.error('Fallo al obtener mensajes:', e));
}

function agregarMensaje(mensaje) {
    const cont = document.getElementById('mensajes');
    if (!cont) {
        console.error('No se encontró contenedor #mensajes');
        return;
    }

    const div = document.createElement('div');
    div.className = 'mensaje ' + (
        (soyEncargado && mensaje.es_encargado) || (!soyEncargado && !mensaje.es_encargado)
            ? 'enviado'
            : 'recibido'
    );
    div.setAttribute('data-id', mensaje.id);

    const contenido = document.createElement('div');
    contenido.className = 'mensaje-contenido';
    contenido.innerHTML = `<p>${escapeHTML(mensaje.mensaje)}</p><span class="hora">${mensaje.fecha}</span>`;

    div.appendChild(contenido);
    cont.appendChild(div);
    cont.scrollTop = cont.scrollHeight;

    ultimoId = mensaje.id;
}

// Simple HTML escape to evitar romper el markup
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}
