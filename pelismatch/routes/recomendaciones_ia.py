from flask import Blueprint, jsonify, request
import asyncio
import httpx
import logging
from ..services import obtener_recomendaciones_ia, fetch_movie_details, obtener_peliculas_disponibles, resolver_titulos_a_ids

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('recomendaciones_ia', __name__)

@bp.route("/recomendaciones/favoritos", methods=['POST'])
async def get_recomendaciones_favoritos():
    try:
        data = request.get_json()

        # Soportamos dos formatos de entrada:
        # 1) {'favoritos_tmdb_ids': [id1, id2, ...]}
        # 2) {'favoritos': ['The Matrix', 'Toy Story', ...]} (recomendado)

        if 'favoritos_tmdb_ids' in data:
            favoritos_tmdb_ids = [int(x) for x in data.get('favoritos_tmdb_ids', [])]
        else:
            favoritos = data.get('favoritos', [])
            # resolver titulos a ids usando el servicio de modelo
            resolver = resolver_titulos_a_ids(favoritos)
            if resolver is None:
                return jsonify({"error": "Modelo no cargado para resolver títulos."}), 503
            favoritos_tmdb_ids = resolver.get('resolved', [])
            unresolved = resolver.get('unresolved', [])
    except Exception:
        return jsonify({"error": "JSON mal formateado. Se esperaba {'favoritos': [titulo1, titulo2,...]} o {'favoritos_tmdb_ids': [id1,...]}"}), 400
    


    if not favoritos_tmdb_ids:
        return jsonify({"error": "La lista de favoritos está vacía o no se pudieron resolver los títulos proporcionados.",
                        "unresolved": unresolved if 'unresolved' in locals() else []}), 400

    disponibles = obtener_peliculas_disponibles()
    if disponibles is None:
        return jsonify({"error": "Modelo no cargado"}), 503
    
    no_en_modelo = [tmdb for tmdb in favoritos_tmdb_ids if tmdb not in set(disponibles)]
    if len(no_en_modelo) == len(favoritos_tmdb_ids):
        # Ningún favorito está en el modelo: devolver 404 con detalles
        logger.debug("Todos los favoritos faltan en el modelo: %s", no_en_modelo)
        return jsonify({
            "error": "Ninguna de las películas favoritas se encontró en nuestro modelo de datos.",
            "favoritos_recibidos": favoritos_tmdb_ids,
            "no_en_modelo": no_en_modelo,
            "cantidad_disponibles": len(disponibles)
        }), 404

    if no_en_modelo:
        logger.debug("Algunos favoritos no están en el modelo: %s", no_en_modelo)
        # continuar usando solo los que están en el modelo
        favoritos_tmdb_ids = [tmdb for tmdb in favoritos_tmdb_ids if tmdb in set(disponibles)]

    recomendaciones_ids = obtener_recomendaciones_ia(favoritos_tmdb_ids)
    
    if recomendaciones_ids is None:
        return jsonify({"error": "El servicio de recomendación no está listo."}), 503
    
    if not recomendaciones_ids:
        return jsonify({"error": "Ninguna de las películas favoritas se encontró en nuestro modelo de datos."}), 404

    async with httpx.AsyncClient() as client:
        tareas = [fetch_movie_details(client, tmdb_id) for tmdb_id in recomendaciones_ids]
        resultados_detalles = await asyncio.gather(*tareas)
    
    resultados_finales = [res for res in resultados_detalles if res is not None]

    response = {
        "basado_en": favoritos_tmdb_ids,
        "recomendaciones": resultados_finales
    }
    # Si venían títulos y hubo no resueltos, añadirlos al response
    if 'unresolved' in locals() and unresolved:
        response['no_resueltos'] = unresolved

    return jsonify(response)


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
