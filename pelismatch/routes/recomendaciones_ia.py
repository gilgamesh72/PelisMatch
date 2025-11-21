from flask import Blueprint, jsonify, request
import asyncio
import httpx
from ..services import obtener_recomendaciones_ia, fetch_movie_details, obtener_peliculas_disponibles

bp = Blueprint('recomendaciones_ia', __name__)


@bp.route("/recomendaciones/favoritos", methods=['POST'])
async def get_recomendaciones_favoritos():
    try:
        data = request.get_json()
        favoritos_tmdb_ids = data.get('favoritos_tmdb_ids', [])
        # Asegurarnos de que sean enteros
        favoritos_tmdb_ids = [int(id) for id in favoritos_tmdb_ids]
    except Exception:
        return jsonify({"error": "JSON mal formateado. Se esperaba {'favoritos_tmdb_ids': [id1, id2, ...]}"}), 400

    if not favoritos_tmdb_ids:
        return jsonify({"error": "La lista de favoritos está vacía."}), 400

    recomendaciones_ids = obtener_recomendaciones_ia(favoritos_tmdb_ids)
    
    if recomendaciones_ids is None:
        return jsonify({"error": "El servicio de recomendación no está listo."}), 503
    
    if not recomendaciones_ids:
        return jsonify({"error": "Ninguna de las películas favoritas se encontró en nuestro modelo de datos."}), 404

    async with httpx.AsyncClient() as client:
        tareas = [fetch_movie_details(client, tmdb_id) for tmdb_id in recomendaciones_ids]
        resultados_detalles = await asyncio.gather(*tareas)
    
    resultados_finales = [res for res in resultados_detalles if res is not None]

    return jsonify({
        "basado_en": favoritos_tmdb_ids,
        "recomendaciones": resultados_finales
    })


@bp.route('/peliculas/disponibles')
def peliculas_disponibles():
    """Devuelve los TMDb IDs disponibles en el modelo para la IA."""
    try:
        tmdb_ids = obtener_peliculas_disponibles()
        if tmdb_ids is None:
            return jsonify({"error": "Modelo no cargado"}), 503
        return jsonify({"tmdb_ids": tmdb_ids})
    except Exception as e:
        return jsonify({"error": f"Error obteniendo IDs disponibles: {e}"}), 500
