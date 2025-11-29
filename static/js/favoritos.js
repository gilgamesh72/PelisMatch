// Variables globales
let favoritos = JSON.parse(localStorage.getItem('cinegraph_favoritos') || '[]');

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    actualizarContadorFavoritos();
});

// Función para actualizar contador de favoritos
function actualizarContadorFavoritos() {
    const contador = favoritos.length;
    
    // Actualizar todos los contadores en la página
    const elementos = document.querySelectorAll('#favoritos-count, #favoritos-count-main');
    elementos.forEach(el => {
        if (el) el.textContent = contador;
    });
    
    // Habilitar/deshabilitar botón de IA
    const botonesIA = document.querySelectorAll('#btn-recomendar-favoritos, #btn-ia-main');
    botonesIA.forEach(btn => {
        if (btn) {
            btn.disabled = contador === 0;
            if (contador === 0) {
                btn.innerHTML = '<i class="fas fa-brain me-2"></i>Agrega favoritos primero';
            } else {
                btn.innerHTML = '<i class="fas fa-magic me-2"></i>Generar Recomendaciones IA';
            }
        }
    });
}

// Función para agregar película a favoritos
function agregarAFavoritos(tmdbId, titulo, posterUrl) {
    // Convertir a número para asegurar formato correcto
    const numericId = parseInt(tmdbId) ;
    
    // Verificar si ya está en favoritos
    const yaExiste = favoritos.find(fav => fav.tmdb_id === numericId);
    
    if (yaExiste) {
        mostrarNotificacion('⚠️ Esta película ya está en tus favoritos', 'warning');
        return;
    }
    
    const nuevoFavorito = {
        tmdb_id: numericId,
        titulo: titulo,
        poster_url: posterUrl,
        fecha_agregado: new Date().toISOString()
    };
    
    favoritos.push(nuevoFavorito);
    localStorage.setItem('cinegraph_favoritos', JSON.stringify(favoritos));
    
    actualizarContadorFavoritos();
    mostrarNotificacion(`💖 "${titulo}" agregada a favoritos`, 'success');
    
    console.log('Favorito agregado:', nuevoFavorito);
}

// Función para remover de favoritos
function removerDeFavoritos(tmdbId) {
    const index = favoritos.findIndex(fav => fav.tmdb_id === tmdbId);
    
    if (index !== -1) {
        const titulo = favoritos[index].titulo;
        favoritos.splice(index, 1);
        localStorage.setItem('cinegraph_favoritos', JSON.stringify(favoritos));
        
        actualizarContadorFavoritos();
        mostrarFavoritos(); // Refrescar la lista
        mostrarNotificacion(`🗑️ "${titulo}" removida de favoritos`, 'info');
    }
}

// Función para mostrar modal de favoritos
function mostrarFavoritos() {
    const lista = document.getElementById('favoritos-lista');
    const modal = new bootstrap.Modal(document.getElementById('favoritosModal'));
    
    if (favoritos.length === 0) {
        lista.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="fas fa-heart-broken fa-3x text-muted mb-3"></i>
                <p class="text-muted">No tienes películas favoritas aún.</p>
                <p class="small text-muted">Busca películas y agrégalas usando el botón <i class="fas fa-heart"></i></p>
            </div>
        `;
    } else {
        lista.innerHTML = favoritos.map(fav => `
            <div class="col-md-4 mb-3">
                <div class="card bg-secondary">
                    <img src="${fav.poster_url}" class="card-img-top movie-poster" alt="${fav.titulo}">
                    <div class="card-body p-2">
                        <h6 class="card-title text-white small mb-2">${fav.titulo}</h6>
                        <div class="d-flex justify-content-between">
                            <small class="text-muted">${new Date(fav.fecha_agregado).toLocaleDateString()}</small>
                            <button class="btn btn-outline-danger btn-sm" onclick="removerDeFavoritos(${fav.tmdb_id})" title="Remover">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    modal.show();
}

async function recomendarPorFavoritos() {
    if (favoritos.length === 0) {
        mostrarNotificacion('⚠️ Necesitas agregar películas a favoritos primero', 'warning');
        return;
    }

    // IDs numéricos (si existen) y títulos
    const tmdbIds = favoritos.map(fav => parseInt(fav.tmdb_id)).filter(id => !isNaN(id));
    const titulos = favoritos.map(fav => fav.titulo).filter(t => t && t.trim().length > 0);

    if (tmdbIds.length === 0 && titulos.length === 0) {
        mostrarNotificacion('⚠️ No hay datos válidos en favoritos', 'warning');
        return;
    }

    const btn = document.querySelector('#btn-recomendar-favoritos') || document.querySelector('#btn-ia-main');

    if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<div class="loading"></div> Procesando IA...';
        btn.disabled = true;

        try {
            console.log('Enviando a IA - IDs:', tmdbIds, 'Títulos:', titulos);

            const requestBody = {};
            if (tmdbIds.length) requestBody.favoritos_tmdb_ids = tmdbIds;
            if (titulos.length) requestBody.favoritos_titulos = titulos;

            console.log('Request body:', requestBody);

            const response = await fetch('/recomendaciones/favoritos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            console.log('Response status:', response.status);

            const data = await response.json();
            console.log('Response data:', data);

            if (response.ok) {
                const modalFavoritos = bootstrap.Modal.getInstance(document.getElementById('favoritosModal'));
                if (modalFavoritos) modalFavoritos.hide();

                if (typeof mostrarResultados === 'function') {
                    mostrarResultados(data, 'inteligencia artificial (favoritos)');
                } else {
                    console.log('Recomendaciones IA:', data);
                    mostrarNotificacion('✨ Recomendaciones generadas con IA', 'success');
                }
            } else {
                mostrarNotificacion(`❌ Error: ${data.error || 'Error desconocido'}`, 'danger');
            }
        } catch (error) {
            console.error('Error en recomendaciones IA:', error);
            mostrarNotificacion('❌ Error de conexión con la IA', 'danger');
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    }
}

// Función para limpiar todos los favoritos
function limpiarFavoritos() {
    if (confirm('¿Estás segura de que quieres eliminar todas las películas favoritas?')) {
        favoritos = [];
        localStorage.removeItem('cinegraph_favoritos');
        actualizarContadorFavoritos();
        mostrarFavoritos();
        mostrarNotificacion('🧹 Favoritos eliminados', 'info');
    }
}

// Sistema de notificaciones toast
function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear contenedor de toasts si no existe
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Crear toast
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div class="toast align-items-center text-bg-${tipo} border-0" role="alert" id="${toastId}">
            <div class="d-flex">
                <div class="toast-body">
                    ${mensaje}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', toastHTML);
    
    // Mostrar toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    
    toast.show();
    
    // Remover del DOM después de ocultarse
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Exponer funciones globales
window.agregarAFavoritos = agregarAFavoritos;
window.removerDeFavoritos = removerDeFavoritos;
window.mostrarFavoritos = mostrarFavoritos;
window.recomendarPorFavoritos = recomendarPorFavoritos;
window.limpiarFavoritos = limpiarFavoritos;