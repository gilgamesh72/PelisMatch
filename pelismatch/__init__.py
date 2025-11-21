import os
from flask import Flask, render_template
from .config import SECRET_KEY
from .data import cargar_modelo
from .routes import (
    peliculas_similares_bp,
    busqueda_avanzada_bp,
    chatbot_conversacional_bp,
    recomendaciones_ia_bp,
    paginas_web_bp
)


def create_app():
    # Obtener la ruta del directorio raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
    app.secret_key = SECRET_KEY
    
    cargar_modelo()
    
    # Rutas HTML principales (sin blueprint para compatibilidad con templates)
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/top-movies')
    def top_movies():
        return render_template('top_movies.html')

    @app.route('/teoria')
    def teoria():
        return render_template('teoria.html')
    
    app.register_blueprint(peliculas_similares_bp)
    app.register_blueprint(busqueda_avanzada_bp)
    app.register_blueprint(chatbot_conversacional_bp)
    app.register_blueprint(recomendaciones_ia_bp)
    app.register_blueprint(paginas_web_bp)
    
    return app

