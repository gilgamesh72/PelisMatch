// ================================================
// FUNCIONES PRINCIPALES - CINEGRAPH
// Por Katherine & Diana
// ================================================

// Variables globales para el estado de la aplicación
window.currentResults = null;
window.searchHistory = [];

// Inicialización de la aplicación
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎬 PelisMatch iniciado - by Diana & Katherine');
    
    // Verificar si hay parámetros de búsqueda en la URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchTerm = urlParams.get('search');
    
    if (searchTerm) {
        // Auto-llenar el campo de búsqueda si viene de otra página
        const campoBusqueda = document.getElementById('nombre-pelicula');
        if (campoBusqueda) {
            campoBusqueda.value = decodeURIComponent(searchTerm);
            // Trigger búsqueda automática después de un pequeño delay
            setTimeout(() => {
                const form = document.getElementById('form-busqueda-simple');
                if (form) {
                    form.dispatchEvent(new Event('submit'));
                }
            }, 500);
        }
    }
    
    // Inicializar animaciones
    initializeAnimations();
    
    // Configurar service worker si está disponible
    if ('serviceWorker' in navigator) {
        registerServiceWorker();
    }
});

// Función para inicializar animaciones
function initializeAnimations() {
    // Intersection Observer para animaciones on-scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                entry.target.style.animationDelay = `${Math.random() * 0.3}s`;
            }
        });
    }, observerOptions);
    
    // Observar elementos que necesitan animación
    document.querySelectorAll('.feature-card, .movie-card').forEach(el => {
        observer.observe(el);
    });
}

// Función para registrar Service Worker (PWA)
async function registerServiceWorker() {
    try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('ServiceWorker registrado:', registration);
    } catch (error) {
        console.log('ServiceWorker falló:', error);
    }
}

// Función utilitaria para hacer requests con retry
async function fetchWithRetry(url, options = {}, maxRetries = 3) {
    let lastError;
    
    for (let i = 0; i <= maxRetries; i++) {
        try {
            const response = await fetch(url, {
                timeout: 10000, // 10 segundos timeout
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response;
        } catch (error) {
            lastError = error;
            console.warn(`Intento ${i + 1} falló:`, error.message);
            
            if (i < maxRetries) {
                // Esperar antes del siguiente intento (exponential backoff)
                const delay = Math.pow(2, i) * 1000;
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw lastError;
}

// Función mejorada para manejo de errores
function handleApiError(error, context = '') {
    console.error(`Error en ${context}:`, error);
    
    let mensaje = '❌ Ocurrió un error inesperado';
    
    if (error.message.includes('timeout')) {
        mensaje = '⏱️ Tiempo de espera agotado. Verifica tu conexión a internet';
    } else if (error.message.includes('404')) {
        mensaje = '🔍 No se encontraron resultados para tu búsqueda';
    } else if (error.message.includes('500')) {
        mensaje = '🔧 Error interno del servidor. Inténtalo más tarde';
    } else if (error.message.includes('network')) {
        mensaje = '📡 Error de conectividad. Verifica tu internet';
    }
    
    if (typeof mostrarNotificacion === 'function') {
        mostrarNotificacion(mensaje, 'danger');
    }
    
    return mensaje;
}

// Función para logging con niveles
function log(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    
    switch (level) {
        case 'error':
            console.error(prefix, message, data);
            break;
        case 'warn':
            console.warn(prefix, message, data);
            break;
        case 'info':
            console.info(prefix, message, data);
            break;
        default:
            console.log(prefix, message, data);
    }
}

// Función para guardar historial de búsquedas
function saveSearchHistory(query, results) {
    const searchEntry = {
        query: query,
        timestamp: Date.now(),
        resultsCount: Array.isArray(results) ? results.length : 0,
        type: 'search'
    };
    
    searchHistory.unshift(searchEntry);
    
    // Mantener solo los últimos 20 búsquedas
    if (searchHistory.length > 20) {
        searchHistory = searchHistory.slice(0, 20);
    }
    
    // Guardar en localStorage
    try {
        localStorage.setItem('cinegraph_search_history', JSON.stringify(searchHistory));
    } catch (error) {
        log('warn', 'No se pudo guardar el historial', error);
    }
}

// Función para cargar historial de búsquedas
function loadSearchHistory() {
    try {
        const saved = localStorage.getItem('cinegraph_search_history');
        if (saved) {
            searchHistory = JSON.parse(saved);
        }
    } catch (error) {
        log('warn', 'No se pudo cargar el historial', error);
        searchHistory = [];
    }
}

// Función para mostrar sugerencias de búsqueda
function showSearchSuggestions(inputElement) {
    loadSearchHistory();
    
    if (searchHistory.length === 0) return;
    
    // Crear dropdown de sugerencias
    let dropdown = document.getElementById('search-suggestions');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'search-suggestions';
        dropdown.className = 'dropdown-menu show position-absolute w-100';
        dropdown.style.cssText = 'z-index: 1050; top: 100%; max-height: 200px; overflow-y: auto;';
        inputElement.parentElement.style.position = 'relative';
        inputElement.parentElement.appendChild(dropdown);
    }
    
    // Generar items del dropdown
    dropdown.innerHTML = searchHistory.slice(0, 5).map(entry => `
        <button class="dropdown-item d-flex justify-content-between align-items-center" 
                onclick="useSuggestion('${entry.query}')">
            <span>${entry.query}</span>
            <small class="text-muted">${new Date(entry.timestamp).toLocaleDateString()}</small>
        </button>
    `).join('');
    
    // Agregar opción para limpiar historial
    dropdown.innerHTML += `
        <div class="dropdown-divider"></div>
        <button class="dropdown-item text-muted small" onclick="clearSearchHistory()">
            <i class="fas fa-trash me-2"></i>Limpiar historial
        </button>
    `;
}

// Función para usar una sugerencia
function useSuggestion(query) {
    const input = document.getElementById('nombre-pelicula');
    if (input) {
        input.value = query;
        input.focus();
    }
    
    // Ocultar dropdown
    const dropdown = document.getElementById('search-suggestions');
    if (dropdown) {
        dropdown.remove();
    }
}

// Función para limpiar historial
function clearSearchHistory() {
    searchHistory = [];
    localStorage.removeItem('cinegraph_search_history');
    
    const dropdown = document.getElementById('search-suggestions');
    if (dropdown) {
        dropdown.remove();
    }
    
    if (typeof mostrarNotificacion === 'function') {
        mostrarNotificacion('🧹 Historial de búsqueda limpiado', 'info');
    }
}

// Función para detectar dispositivo móvil
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Función para compartir resultados (Web Share API)
async function compartirResultados() {
    if (!window.currentResults) {
        mostrarNotificacion('⚠️ No hay resultados para compartir', 'warning');
        return;
    }
    
    const shareData = {
        title: 'CineGraph - Recomendaciones',
        text: `Mira estas recomendaciones de películas que encontré en CineGraph`,
        url: window.location.href
    };
    
    try {
        if (navigator.share && isMobileDevice()) {
            await navigator.share(shareData);
        } else {
            // Fallback: copiar al clipboard
            await navigator.clipboard.writeText(
                `${shareData.text}\n${shareData.url}`
            );
            mostrarNotificacion('📋 Enlace copiado al portapapeles', 'success');
        }
    } catch (error) {
        log('error', 'Error compartiendo', error);
        mostrarNotificacion('❌ Error al compartir', 'danger');
    }
}

// Función para toggle de tema oscuro/claro (bonus feature)
function toggleTheme() {
    const body = document.body;
    const isDark = body.classList.contains('theme-dark');
    
    if (isDark) {
        body.classList.remove('theme-dark');
        body.classList.add('theme-light');
        localStorage.setItem('cinegraph_theme', 'light');
    } else {
        body.classList.remove('theme-light');
        body.classList.add('theme-dark');
        localStorage.setItem('cinegraph_theme', 'dark');
    }
}

// Función para inicializar tema
function initializeTheme() {
    const savedTheme = localStorage.getItem('cinegraph_theme') || 'dark';
    document.body.classList.add(`theme-${savedTheme}`);
}

// Performance monitoring
function measurePerformance(name, fn) {
    return async function(...args) {
        const start = performance.now();
        try {
            const result = await fn.apply(this, args);
            const end = performance.now();
            log('info', `Performance [${name}]: ${end - start}ms`);
            return result;
        } catch (error) {
            const end = performance.now();
            log('error', `Performance [${name}] ERROR: ${end - start}ms`, error);
            throw error;
        }
    };
}

// Función para detectar si está online/offline
function initializeConnectivityCheck() {
    function updateOnlineStatus() {
        const isOnline = navigator.onLine;
        const indicator = document.getElementById('connectivity-indicator') || createConnectivityIndicator();
        
        if (isOnline) {
            indicator.className = 'connectivity-indicator online';
            indicator.innerHTML = '<i class="fas fa-wifi"></i>';
            indicator.title = 'Conectado';
        } else {
            indicator.className = 'connectivity-indicator offline';
            indicator.innerHTML = '<i class="fas fa-wifi-slash"></i>';
            indicator.title = 'Sin conexión';
            mostrarNotificacion('📡 Sin conexión a internet', 'warning');
        }
    }
    
    function createConnectivityIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'connectivity-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 9999;
            padding: 8px;
            border-radius: 50%;
            transition: all 0.3s ease;
        `;
        document.body.appendChild(indicator);
        return indicator;
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus(); // Check initial status
}

// Inicialización completa
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    loadSearchHistory();
    initializeConnectivityCheck();
    
    // Setup event listeners para sugerencias de búsqueda
    const searchInput = document.getElementById('nombre-pelicula');
    if (searchInput) {
        searchInput.addEventListener('focus', () => showSearchSuggestions(searchInput));
        searchInput.addEventListener('blur', () => {
            // Delay para permitir clicks en sugerencias
            setTimeout(() => {
                const dropdown = document.getElementById('search-suggestions');
                if (dropdown) dropdown.remove();
            }, 200);
        });
    }
});

// Exponer funciones globales útiles
window.CineGraph = {
    log,
    fetchWithRetry,
    handleApiError,
    compartirResultados,
    toggleTheme,
    measurePerformance,
    version: '1.0.0'
};

// CSS adicional para conectividad y tema
const additionalStyles = `
<style>
.connectivity-indicator {
    font-size: 12px;
    color: white;
}

.connectivity-indicator.online {
    background: var(--success);
}

.connectivity-indicator.offline {
    background: var(--danger);
    animation: pulse 2s infinite;
}

.theme-light {
    --dark-bg: #f8f9fa;
    --darker-bg: #e9ecef;
    --light-text: #212529;
    --muted-text: #6c757d;
}

.theme-light .navbar,
.theme-light .feature-card,
.theme-light .movie-card {
    background: rgba(0, 0, 0, 0.05) !important;
    color: var(--light-text) !important;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', additionalStyles);