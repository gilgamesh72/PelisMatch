from flask import Blueprint, jsonify, render_template
import requests
from ..config import API_KEY, BASE_URL, IMAGE_BASE_URL
from ..data import directores_tmdb, actores_tmdb

bp = Blueprint('paginas_web', __name__, url_prefix=None)


@bp.route('/api/top-peliculas')
def api_top_peliculas():
    """Genera un ranking ponderado de películas usando la fórmula IMDb-like.
    W = (v/(v+m))*R + (m/(v+m))*C
    Se usa /movie/popular para obtener una lista base.
    """
    try:
        url = f"{BASE_URL}/movie/popular"
        params = {"api_key": API_KEY, "language": "es-ES", "page": 1}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        resultados = resp.json().get('results', [])
    except requests.RequestException as e:
        return jsonify({"error": f"Error consultando TMDb: {e}"}), 500

    # Parámetros de ponderación
    m = 1000  # mínimo de votos requerido
    C = 7.0   # rating promedio global aproximado

    ranking = []
    for r in resultados:
        votos = r.get('vote_count', 0)
        rating = r.get('vote_average', 0.0)
        # Evitar división por cero
        ponderado = ((votos / (votos + m)) * rating) + ((m / (votos + m)) * C) if (votos + m) > 0 else 0
        ranking.append({
            "tmdb_id": r.get('id'),
            "titulo": r.get('title'),
            "poster_url": f"{IMAGE_BASE_URL}{r.get('poster_path', '')}",
            "overview": r.get('overview', ''),
            "votos": votos,
            "rating_original": rating,
            "puntuacion_ponderada": round(ponderado, 3)
        })

    # Orden descendente por puntuación ponderada
    ranking_ordenado = sorted(ranking, key=lambda x: x['puntuacion_ponderada'], reverse=True)
    return jsonify({"peliculas": ranking_ordenado[:20]})


@bp.route('/api/genres')
def api_genres():
    """Devuelve lista de géneros TMDb (id, name)."""
    try:
        url = f"{BASE_URL}/genre/movie/list"
        params = {"api_key": API_KEY, "language": "es-ES"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        genres = resp.json().get('genres', [])
        return jsonify({"genres": genres})
    except requests.RequestException as e:
        return jsonify({"error": f"Error consultando géneros: {e}"}), 500


@bp.route('/api/catalogo/personas')
def api_catalogo_personas():
    """Devuelve catálogos fijos de directores y actores para selección frontend."""
    return jsonify({
        "directores": directores_tmdb,
        "actores": actores_tmdb
    })
