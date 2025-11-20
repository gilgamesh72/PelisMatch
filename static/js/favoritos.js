// ================================================
// SISTEMA DE FAVORITOS - CINEGRAPH
// Por Katherine & Diana
// ================================================

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
    // Verificar si ya está en favoritos
    const yaExiste = favoritos.find(fav => fav.tmdb_id === tmdbId);
    
    if (yaExiste) {
        mostrarNotificacion('⚠️ Esta película ya está en tus favoritos', 'warning');
        return;
    }
    
    const nuevoFavorito = {
        tmdb_id: tmdbId,
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

// Función para generar recomendaciones por favoritos (IA)
async function recomendarPorFavoritos() {
    if (favoritos.length === 0) {
        mostrarNotificacion('⚠️ Necesitas agregar películas a favoritos primero', 'warning');
        return;
    }
    
    const tmdbIds = favoritos.map(fav => fav.tmdb_id);
    const btn = document.querySelector('#btn-recomendar-favoritos') || document.querySelector('#btn-ia-main');
    
    if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<div class="loading"></div> Procesando IA...';
        btn.disabled = true;
        
        try {
            const response = await fetch('/recomendaciones/favoritos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    favoritos_tmdb_ids: tmdbIds
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Cerrar modal de favoritos si está abierto
                const modalFavoritos = bootstrap.Modal.getInstance(document.getElementById('favoritosModal'));
                if (modalFavoritos) {
                    modalFavoritos.hide();
                }
                
                // Mostrar resultados
                if (typeof mostrarResultados === 'function') {
                    mostrarResultados(data, 'inteligencia artificial (basado en favoritos)');
                } else {
                    console.log('Recomendaciones IA:', data);
                    mostrarNotificacion('✨ Recomendaciones generadas con IA', 'success');
                }
            } else {
                mostrarNotificacion(`❌ Error: ${data.error}`, 'danger');
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

// Función para exportar favoritos (bonus)
function exportarFavoritos() {
    if (favoritos.length === 0) {
        mostrarNotificacion('⚠️ No hay favoritos para exportar', 'warning');
        return;
    }
    
    const dataStr = JSON.stringify(favoritos, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `cinegraph_favoritos_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
    mostrarNotificacion('📥 Favoritos exportados exitosamente', 'success');
}

// Función para importar favoritos (bonus)
function importarFavoritos() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const importedFavoritos = JSON.parse(e.target.result);
                
                if (Array.isArray(importedFavoritos)) {
                    // Validar estructura básica
                    const validFavoritos = importedFavoritos.filter(fav => 
                        fav.tmdb_id && fav.titulo && fav.poster_url
                    );
                    
                    if (validFavoritos.length > 0) {
                        favoritos = validFavoritos;
                        localStorage.setItem('cinegraph_favoritos', JSON.stringify(favoritos));
                        actualizarContadorFavoritos();
                        mostrarNotificacion(`📤 ${validFavoritos.length} favoritos importados`, 'success');
                    } else {
                        mostrarNotificacion('❌ El archivo no contiene favoritos válidos', 'danger');
                    }
                } else {
                    mostrarNotificacion('❌ Formato de archivo incorrecto', 'danger');
                }
            } catch (error) {
                mostrarNotificacion('❌ Error al leer el archivo', 'danger');
            }
        };
        reader.readAsText(file);
    };
    
    input.click();
}

// Exponer funciones globales
window.agregarAFavoritos = agregarAFavoritos;
window.removerDeFavoritos = removerDeFavoritos;
window.mostrarFavoritos = mostrarFavoritos;
window.recomendarPorFavoritos = recomendarPorFavoritos;
window.limpiarFavoritos = limpiarFavoritos;
window.exportarFavoritos = exportarFavoritos;
window.importarFavoritos = importarFavoritos;