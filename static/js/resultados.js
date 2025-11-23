// JS moved from templates/resultados.html
// Uses window.RESULTADOS_CONFIG.index_url for server-side URLs injected by the template

// Quick startup log to verify the file is loaded in the browser
console.log('resultados.js loaded');
if (typeof window.RESULTADOS_CONFIG === 'undefined') {
    console.warn('window.RESULTADOS_CONFIG is not defined (template may not have injected it)');
    window.RESULTADOS_CONFIG = {};
}

// Variables globales para la página de resultados
let currentResults = [];
let filteredResults = [];
let currentView = 'grid';
let processingStartTime = performance.now();

// Inicialización de la página
document.addEventListener('DOMContentLoaded', function() {
    // Obtener parámetros de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchType = urlParams.get('type');
    const searchQuery = urlParams.get('q');
    
    if (searchQuery) {
        // performSearch puede estar disponible globalmente; llamamos a la función local
        try { performSearch(searchType, searchQuery); } catch (e) { console.warn('performSearch no disponible', e); }
    } else {
        showEmptyState();
    }
    
    // Configurar scroll listener para botón "volver arriba"
    window.addEventListener('scroll', handleScroll);
});

// Función principal de búsqueda
async function performSearch(type, query) {
    showLoadingState();
    
    try {
        let response;
        
        switch (type) {
            case 'similarity':
                response = await fetch(`/similares/${encodeURIComponent(query)}`);
                break;
            case 'favorites':
                response = await fetch('/recomendaciones/favoritos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ favoritos_tmdb_ids: JSON.parse(query) })
                });
                break;
            case 'logic':
                response = await fetch('/buscar/logica', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: query
                });
                break;
            default:
                throw new Error('Tipo de búsqueda no válido');
        }
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data, type);
        } else {
            showErrorState(data.error || 'Error en la búsqueda');
        }
        
    } catch (error) {
        console.error('Error en búsqueda:', error);
        showErrorState('Error de conexión');
    }
    
    // Calcular tiempo de procesamiento
    const processingTime = ((performance.now() - processingStartTime) / 1000).toFixed(2);
    const el = document.getElementById('processing-time');
    if (el) el.textContent = processingTime + 's';
}

// Mostrar resultados
function displayResults(data, searchType) {
    console.log('displayResults called, raw data:', data);
    currentResults = data.similares || data.recomendaciones || data;
    try { window.currentResults = currentResults; } catch (e) {}
    filteredResults = [...currentResults];
    try { window.filteredResults = filteredResults; } catch (e) {}
    
    // Mostrar información de búsqueda
    showSearchInfo(searchType);
    
    // Mostrar película base si existe
    if (data.pelicula_buscada) {
        showBaseMovie(data.pelicula_buscada);
    }
    
    // Renderizar resultados
    renderResults();
    
    // Actualizar estadísticas
    updateStats();
    
    // Ocultar estado de carga
    hideLoadingState();
}

// Mostrar información del algoritmo utilizado
function showSearchInfo(type) {
    const section = document.getElementById('search-info-section');
    const description = document.getElementById('algorithm-description');
    
    const algorithms = {
        'similarity': {
            name: 'Búsqueda por Similitud',
            description: 'Encuentra películas parecidas analizando directores, géneros y actores en común.'
        },
        'favorites': {
            name: 'Recomendaciones Personalizadas con IA',
            description: 'Utiliza inteligencia artificial para sugerir películas basadas en tus gustos y favoritos.'
        },
        'logic': {
            name: 'Búsqueda Avanzada',
            description: 'Combina múltiples criterios para encontrar exactamente el tipo de película que buscas.'
        }
    };
    
    const algo = algorithms[type] || algorithms['similarity'];
    
    if (description) {
        description.innerHTML = `
            <strong>${algo.name}:</strong> ${algo.description}
            <br><small class="text-muted mt-1 d-block">
                <i class="fas fa-clock me-1"></i>Procesado en tiempo real usando algoritmos de matemáticas discretas
            </small>
        `;
    }
    
    if (section) section.style.display = 'block';
}

// Mostrar película base
function showBaseMovie(movie) {
    const section = document.getElementById('base-movie-section');
    const content = document.getElementById('base-movie-content');
    if (!content) return;
    
    content.innerHTML = `
        <div class="row align-items-center">
            <div class="col-md-2">
                <img src="${movie.poster_url}" class="img-fluid rounded shadow" 
                     alt="${movie.nombre}" style="max-height: 200px;">
            </div>
            <div class="col-md-10">
                <h3 class="text-gradient mb-3">${movie.nombre}</h3>
                <p class="text-light mb-3">${movie.overview || 'Sin descripción disponible'}</p>
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-gradient" 
                            onclick="agregarAFavoritos('${movie.id || movie.tmdb_id || ''}', '${movie.nombre}', '${movie.poster_url}')">
                        <i class="fas fa-heart me-2"></i>Agregar a Favoritos
                    </button>
                    <button class="btn btn-gradient" onclick="verDetalles('${movie.id || movie.tmdb_id || ''}')">
                        <i class="fas fa-info-circle me-2"></i>Ver Detalles
                    </button>
                </div>
            </div>
        </div>
    `;
    
    section.style.display = 'block';
}

// Renderizar resultados según la vista actual
function renderResults() {
    const container = document.getElementById('results-container');
    if (!container) return;
    
    if (filteredResults.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-filter fa-3x text-muted mb-3"></i>
                <h4 class="text-gradient">No hay películas que coincidan con los filtros</h4>
                <p class="text-muted">Ajusta los criterios de filtrado</p>
                <button class="btn btn-outline-gradient" onclick="limpiarFiltros()">
                    <i class="fas fa-redo me-2"></i>Limpiar Filtros
                </button>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    filteredResults.forEach((movie, index) => {
        const titulo = movie.nombre || movie.titulo;
        const poster = movie.poster_url;
        const similitud = movie.similitud;
        const tmdbId = movie.tmdb_id || movie.id || '';
        
        if (currentView === 'grid') {
            html += renderGridCard(movie, index);
        } else if (currentView === 'list') {
            html += renderListCard(movie, index);
        } else {
            html += renderCompactCard(movie, index);
        }
    });
    
    container.innerHTML = html;

    // Enlazar botones de favorito (data-driven) para evitar errores de argumentos
    attachFavoriteButtons();

    // Aplicar animaciones de entrada
    container.querySelectorAll('.movie-card').forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });
}

// Renderizar tarjeta en vista de grilla
function renderGridCard(movie, index) {
    const titulo = movie.nombre || movie.titulo;
    const poster = movie.poster_url;
    const similitud = movie.similitud;
    const tmdbId = movie.tmdb_id || movie.id || '';
    
    return `
        <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
            <div class="movie-card h-100">
                <div class="position-relative">
                    <img src="${poster}" class="movie-poster" alt="${titulo}"
                         onerror="this.src='https://via.placeholder.com/300x450/6c5ce7/ffffff?text=Sin+Imagen'">
                    ${similitud ? `
                        <div class="position-absolute top-0 end-0 m-2">
                            <span class="similarity-score">
                                ${similitud.toFixed(2)}
                            </span>
                        </div>
                    ` : ''}
                </div>
                <div class="movie-info p-3">
                    <h6 class="text-white mb-2 fw-bold">${titulo}</h6>
                    <div class="d-flex gap-2">
                        <button class="btn btn-outline-light btn-sm flex-grow-1 fav-btn" 
                            type="button"
                            data-tmdb="${tmdbId}"
                            data-title="${escapeHtml(titulo)}"
                            data-poster="${poster}">
                            <i class="fas fa-heart"></i>
                        </button>
                        <button class="btn btn-gradient btn-sm" 
                                onclick="verDetalles('${tmdbId}')">
                            <i class="fas fa-info"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Renderizar tarjeta en vista de lista
function renderListCard(movie, index) {
    const titulo = movie.nombre || movie.titulo;
    const poster = movie.poster_url;
    const similitud = movie.similitud;
    const tmdbId = movie.tmdb_id || movie.id || '';
    
    return `
        <div class="col-12 mb-3">
            <div class="card bg-dark border-secondary movie-card">
                <div class="row g-0">
                    <div class="col-md-2">
                        <img src="${poster}" class="img-fluid rounded-start" 
                             style="height: 150px; object-fit: cover;" alt="${titulo}">
                    </div>
                    <div class="col-md-10">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h5 class="text-gradient">${titulo}</h5>
                                    ${similitud ? `
                                        <span class="similarity-score me-2">
                                            Similitud: ${similitud.toFixed(2)}
                                        </span>
                                    ` : ''}
                                </div>
                                <div class="d-flex gap-2">
                                    <button class="btn btn-outline-light btn-sm fav-btn" type="button"
                                            data-tmdb="${tmdbId}"
                                            data-title="${escapeHtml(titulo)}"
                                            data-poster="${poster}">
                                        <i class="fas fa-heart me-1"></i>Favorito
                                    </button>
                                    <button class="btn btn-gradient btn-sm" 
                                            onclick="verDetalles('${tmdbId}')">
                                        <i class="fas fa-info me-1"></i>Detalles
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Renderizar tarjeta en vista compacta
function renderCompactCard(movie, index) {
    const titulo = movie.nombre || movie.titulo;
    const similitud = movie.similitud;
    const tmdbId = movie.id || movie.tmdb_id || '';
    
    return `
        <div class="col-md-6 col-lg-4 mb-2">
            <div class="d-flex align-items-center p-2 bg-dark rounded border movie-card">
                <div class="flex-grow-1">
                    <strong class="text-white">${titulo}</strong>
                    ${similitud ? `<small class="text-muted ms-2">${similitud.toFixed(2)}</small>` : ''}
                </div>
                <div class="d-flex gap-1">
                    <button class="btn btn-outline-light btn-sm fav-btn" type="button"
                            data-tmdb="${tmdbId}"
                            data-title="${escapeHtml(titulo)}"
                            data-poster="">
                        <i class="fas fa-heart"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Funciones de filtros y ordenamiento
function aplicarFiltroSimilitud(valor) {
    const el = document.getElementById('similarity-value');
    if (el) el.textContent = valor;
    
    filteredResults = currentResults.filter(movie => 
        !movie.similitud || movie.similitud >= parseFloat(valor)
    );
    
    renderResults();
    updateStats();
}

function ordenarResultados(criterio) {
    switch (criterio) {
        case 'similitud':
            filteredResults.sort((a, b) => (b.similitud || 0) - (a.similitud || 0));
            break;
        case 'titulo':
            filteredResults.sort((a, b) => 
                (a.nombre || a.titulo).localeCompare(b.nombre || b.titulo)
            );
            break;
        case 'fecha':
            // Si hubiera fecha, ordenar por ella
            break;
    }
    
    renderResults();
}

function cambiarVisualizacion(vista) {
    currentView = vista;
    renderResults();
}

function limpiarFiltros() {
    const el = document.getElementById('similarity-filter');
    if (el) el.value = 0;
    const valEl = document.getElementById('similarity-value');
    if (valEl) valEl.textContent = '0';
    filteredResults = [...currentResults];
    renderResults();
    updateStats();
}

// Funciones de estado
function showLoadingState() {
    const ls = document.getElementById('loading-state'); if (ls) ls.style.display = 'block';
    const es = document.getElementById('empty-state'); if (es) es.classList.add('d-none');
}

function hideLoadingState() { const ls = document.getElementById('loading-state'); if (ls) ls.style.display = 'none'; }

function showEmptyState() { hideLoadingState(); const es = document.getElementById('empty-state'); if (es) es.classList.remove('d-none'); }

function showErrorState(mensaje) {
    hideLoadingState();
    const container = document.getElementById('results-container');
    if (container) container.innerHTML = `
        <div class="col-12 text-center py-5">
            <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
            <h4 class="text-gradient">Error en la búsqueda</h4>
            <p class="text-muted">${mensaje}</p>
            <button class="btn btn-gradient" onclick="nuevaBusqueda()">
                <i class="fas fa-redo me-2"></i>Intentar de nuevo
            </button>
        </div>
    `;
}

// Actualizar estadísticas
function updateStats() {
    const totalEl = document.getElementById('total-results');
    if (totalEl) totalEl.textContent = filteredResults.length;
    
    if (filteredResults.length > 0) {
        const similarities = filteredResults
            .filter(movie => movie.similitud)
            .map(movie => movie.similitud);
        
        const avgEl = document.getElementById('avg-similarity');
        if (similarities.length > 0) {
            const avg = similarities.reduce((a, b) => a + b, 0) / similarities.length;
            if (avgEl) avgEl.textContent = avg.toFixed(2);
        } else if (avgEl) {
            avgEl.textContent = 'N/A';
        }
    }
}

// Funciones de utilidad
function toggleFilters() {
    const filters = document.getElementById('quick-filters');
    const icon = document.querySelector('[onclick="toggleFilters()"] i');
    
    if (filters.classList.contains('show')) {
        filters.classList.remove('show');
        icon.className = 'fas fa-chevron-down';
    } else {
        filters.classList.add('show');
        icon.className = 'fas fa-chevron-up';
    }
}

function handleScroll() {
    const backToTop = document.getElementById('back-to-top');
    if (window.pageYOffset > 300) {
        if (backToTop) backToTop.style.display = 'block';
    } else {
        if (backToTop) backToTop.style.display = 'none';
    }
}

function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }

function nuevaBusqueda() {
    const indexUrl = (window.RESULTADOS_CONFIG && window.RESULTADOS_CONFIG.index_url) || '/';
    window.location.href = indexUrl;
}

function exportarResultados() {
    const data = {
        timestamp: new Date().toISOString(),
        total_results: filteredResults.length,
        results: filteredResults
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `cinegraph_resultados_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
}

// Función placeholder para ver detalles
function verDetalles(tmdbId) {
    console.log('Ver detalles de:', tmdbId);
    let movie = null;
    try {
        movie = (currentResults || []).find(m => String(m.id) === String(tmdbId) || String(m.tmdb_id) === String(tmdbId));
    } catch (e) { /* ignore */ }
    
    window.__modalMovie = movie || { id: tmdbId };
    const content = document.getElementById('movie-details-content');
    if (movie) {
        content.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <img src="${movie.poster_url || ''}" class="img-fluid rounded" alt="${movie.nombre || movie.titulo || ''}">
                </div>
                <div class="col-md-8">
                    <h4 class="text-gradient">${movie.nombre || movie.titulo || ''}</h4>
                    <p class="text-light">${movie.overview || movie.description || 'Sin descripción disponible'}</p>
                </div>
            </div>
        `;
    } else {
        if (content) content.innerHTML = `<p class="text-light">Detalles de la película (ID: ${tmdbId})</p>`;
    }

    try {
        const modalEl = document.getElementById('movieDetailsModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } catch (e) {
        console.warn('No se pudo abrir modal (bootstrap ausente o error):', e);
    }
}

// Llamador desde el modal: usa la película actualmente mostrada en el modal
function agregarAFavoritosFromModal() {
    const m = window.__modalMovie;
    if (!m || !m.id) {
        console.warn('agregarAFavoritosFromModal: no hay pelicula en window.__modalMovie', m);
        return;
    }
    const id = m.id || m.tmdb_id;
    const title = m.nombre || m.titulo || m.title || '';
    const poster = m.poster_url || m.poster || '';
    agregarAFavoritos(id, title, poster);
}

// Escapa comillas y caracteres especiales en títulos para atributos
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Añade listeners a botones con clase .fav-btn (llaman a agregarAFavoritos con datos del dataset)
function attachFavoriteButtons() {
    document.querySelectorAll('.fav-btn').forEach(btn => {
        if (btn.__favHandlerAttached) return;
        btn.addEventListener('click', function(e) {
            const b = e.currentTarget;
            let id = b.dataset.tmdb;
            let title = b.dataset.title;
            let poster = b.dataset.poster;

            if (!id) {
                try {
                    const card = b.closest('.movie-card') || b.closest('.card') || b.parentElement;
                    if (card) {
                        const titleEl = card.querySelector('h6') || card.querySelector('h5') || card.querySelector('strong') || card.querySelector('.movie-title');
                        const titleText = titleEl ? titleEl.textContent.trim() : null;
                        if (titleText && (!title || title === '')) title = titleText;
                        if (window.currentResults && Array.isArray(window.currentResults)) {
                            const found = window.currentResults.find(m => (m.nombre && m.nombre === title) || (m.titulo && m.titulo === title));
                            if (found) {
                                id = found.tmdb_id || found.id || '';
                                poster = poster || found.poster_url || '';
                            }
                        }
                    }
                } catch (e) { console.warn('Fallback lookup failed', e); }
            }

            try { window.__lastAgregarFavoritosCall = { raw: id, titulo: title, posterUrl: poster, source: 'fav-btn', ts: Date.now() }; } catch(e){}
            agregarAFavoritos(id, title, poster);
        });
        btn.__favHandlerAttached = true;
    });
}

// Exponer funciones para depuración y acceso global
try {
    window.performSearch = window.performSearch || performSearch;
    window.displayResults = window.displayResults || displayResults;
    window.renderResults = window.renderResults || renderResults;
    window.attachFavoriteButtons = window.attachFavoriteButtons || attachFavoriteButtons;
} catch (e) { console.warn('No se pudieron exponer funciones globales:', e); }
