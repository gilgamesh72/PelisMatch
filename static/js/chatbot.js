class ChatbotFSM {
    constructor() {
        this.isOpen = false;
        this.conversacionId = null;
        this.mensajes = [];
        this.initializeWidget();
    }

    // Inicializar el widget del chatbot
    initializeWidget() {
        // Crear HTML del widget si no existe
        if (!document.getElementById('chatbot-widget')) {
            const widgetHTML = `
                <div id="chatbot-widget" class="chatbot-widget">
                    <button class="chatbot-toggle" onclick="chatbot.toggle()" title="Asistente IA">
                        <i class="fas fa-robot"></i>
                    </button>
                    
                    <div class="chatbot-panel" id="chatbot-panel">
                        <div class="chatbot-header">
                            <i class="fas fa-robot me-2"></i>Asistente PelisMatch
                            <button class="btn btn-sm btn-outline-light ms-auto" onclick="chatbot.reiniciar()" title="Reiniciar">
                                <i class="fas fa-refresh"></i>
                            </button>
                        </div>
                        
                        <div class="chatbot-messages" id="chatbot-messages">
                            <div class="message bot">
                                ¡Hola! 👋 Soy el asistente de PelisMatch. Te ayudaré a encontrar la película perfecta según tus gustos. ¿Comenzamos?
                            </div>
                        </div>
                        
                        <div class="chatbot-input">
                            <div class="input-group">
                                <input type="text" class="form-control" id="chatbot-input" 
                                       placeholder="Escribe tu mensaje..." 
                                       onkeypress="if(event.key==='Enter') chatbot.enviarMensaje()">
                                <button class="btn btn-gradient" onclick="chatbot.enviarMensaje()">
                                    <i class="fas fa-paper-plane"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', widgetHTML);
        }

        this.panel = document.getElementById('chatbot-panel');
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.inputField = document.getElementById('chatbot-input');
    }

    // Alternar visibilidad del panel
    toggle() {
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            this.panel.style.display = 'flex';
            this.inputField.focus();
            
            // Animación de entrada
            this.panel.style.opacity = '0';
            this.panel.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                this.panel.style.transition = 'all 0.3s ease';
                this.panel.style.opacity = '1';
                this.panel.style.transform = 'translateY(0)';
            }, 10);
        } else {
            this.panel.style.opacity = '0';
            this.panel.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                this.panel.style.display = 'none';
            }, 300);
        }
    }

    // Enviar mensaje al chatbot
    async enviarMensaje() {
        const mensaje = this.inputField.value.trim();
        if (!mensaje) return;

        // Agregar mensaje del usuario
        this.agregarMensaje(mensaje, 'user');
        this.inputField.value = '';

        // Mostrar indicador de escritura
        const typingId = this.mostrarEscribiendo();

        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: mensaje
                })
            });

            const data = await response.json();

            // Remover indicador de escritura
            this.removerEscribiendo(typingId);

            if (response.ok) {
                // Agregar respuesta del bot
                this.agregarMensaje(data.respuesta, 'bot');

                // Si hay recomendaciones finales, mostrarlas
                if (data.recomendaciones && data.recomendaciones.length > 0) {
                    this.mostrarRecomendacionesFinales(data.recomendaciones, data.criterios_usados);
                }
            } else {
                this.agregarMensaje('❌ Hubo un error. Intenta de nuevo.', 'bot');
            }
        } catch (error) {
            this.removerEscribiendo(typingId);
            this.agregarMensaje('❌ Error de conexión. Verifica tu internet.', 'bot');
            console.error('Error en chatbot:', error);
        }
    }

    // Agregar mensaje al chat
    agregarMensaje(texto, tipo) {
        const mensajeDiv = document.createElement('div');
        mensajeDiv.className = `message ${tipo}`;
        
        if (tipo === 'bot') {
            // Agregar emoji y formateo para mensajes del bot
            texto = this.formatearMensajeBot(texto);
        }
        
        mensajeDiv.innerHTML = texto;
        
        this.messagesContainer.appendChild(mensajeDiv);
        this.scrollToBottom();
        
        // Animación de entrada
        mensajeDiv.style.opacity = '0';
        mensajeDiv.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            mensajeDiv.style.transition = 'all 0.3s ease';
            mensajeDiv.style.opacity = '1';
            mensajeDiv.style.transform = 'translateY(0)';
        }, 10);
    }

    // Formatear mensaje del bot con emojis y estilo
    formatearMensajeBot(texto) {
        // Detectar palabras clave y agregar emojis
        const keywords = {
            'accion': '⚡',
            'acción': '⚡',
            'comedia': '😂',
            'drama': '🎭',
            'terror': '👻',
            'romance': '💕',
            'ciencia ficcion': '🚀',
            'fantasia': '🧙‍♀️',
            'aventura': '🗺️',
            'clasico': '🎞️',
            'clásico': '🎞️',
            'reciente': '✨',
            'moderno': '🆕'
        };
        
        let textoFormateado = texto;
        
        Object.keys(keywords).forEach(keyword => {
            const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
            textoFormateado = textoFormateado.replace(regex, `${keywords[keyword]} ${keyword}`);
        });
        
        return textoFormateado;
    }

    // Mostrar indicador de escritura
    mostrarEscribiendo() {
        const typingId = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.id = typingId;
        typingDiv.className = 'message bot';
        typingDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="loading me-2"></div>
                <span class="text-muted small">El asistente está pensando...</span>
            </div>
        `;
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
        
        return typingId;
    }

    // Remover indicador de escritura
    removerEscribiendo(typingId) {
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }
    }

    // Mostrar recomendaciones finales del chatbot
    mostrarRecomendacionesFinales(recomendaciones, criterios) {
        const recomendacionesHTML = `
            <div class="mt-3 p-3" style="background: rgba(116, 185, 255, 0.1); border-radius: 8px; border-left: 3px solid var(--accent-blue);">
                <h6 class="text-gradient mb-2">
                    <i class="fas fa-magic me-2"></i>Recomendaciones Finales
                </h6>
                <div class="mb-2">
                    ${recomendaciones.map(pelicula => 
                        `<span class="badge bg-gradient me-1 mb-1 clickable-badge" onclick="chatbot.cerrarYBuscar('${pelicula}')" style="cursor: pointer;" title="Clic para buscar">${pelicula}</span>`
                    ).join('')}
                </div>
            </div>
        `;
        
        this.messagesContainer.insertAdjacentHTML('beforeend', recomendacionesHTML);
        this.scrollToBottom();
    }

    // Cerrar chatbot y buscar película
    cerrarYBuscar(nombrePelicula) {
        // Cerrar chatbot
        if (this.isOpen) {
            this.toggle();
        }
        
        // Llenar el campo de búsqueda si existe
        const campoBusqueda = document.getElementById('nombre-pelicula');
        if (campoBusqueda) {
            campoBusqueda.value = nombrePelicula;
            campoBusqueda.focus();
            
            // Trigger de búsqueda automática si la función existe
            if (typeof buscarSimilares === 'function') {
                const form = document.getElementById('form-busqueda-simple');
                if (form) {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        }
        
        this.mostrarNotificacion(`🔍 Buscando "${nombrePelicula}"...`, 'info');
    }

    // Reiniciar conversación
    reiniciar() {
        if (confirm('¿Quieres reiniciar la conversación?')) {
            // Limpiar mensajes excepto el saludo inicial
            this.messagesContainer.innerHTML = `
                <div class="message bot">
                    ¡Hola! 👋 Soy el asistente de PelisMatch. Te ayudaré a encontrar la película perfecta según tus gustos. ¿Comenzamos?
                </div>
            `;
            
            // Reset del backend (enviar mensaje especial)
            fetch('/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'reset' })
            }).catch(console.error);
            
            this.conversacionId = null;
            this.mostrarNotificacion('🔄 Conversación reiniciada', 'info');
        }
    }

    // Scroll automático hacia abajo
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    // Mostrar notificación (reutiliza la función de favoritos)
    mostrarNotificacion(mensaje, tipo) {
        if (typeof mostrarNotificacion === 'function') {
            mostrarNotificacion(mensaje, tipo);
        } else {
            console.log(`Notificación [${tipo}]: ${mensaje}`);
        }
    }
}

// Inicializar chatbot cuando se carga la página
let chatbot;

document.addEventListener('DOMContentLoaded', function() {
    chatbot = new ChatbotFSM();
    
    // Exponer globalmente para uso en HTML
    window.chatbot = chatbot;
});

// Función para iniciar chatbot desde botones externos
function iniciarChatbot() {
    if (chatbot && !chatbot.isOpen) {
        chatbot.toggle();
    }
}

// Exponer función global
window.iniciarChatbot = iniciarChatbot;