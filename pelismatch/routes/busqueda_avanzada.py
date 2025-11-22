from flask import Blueprint, jsonify, request
import asyncio
import httpx
from ..services import fetch_movies_by_criteria

bp = Blueprint('busqueda_avanzada', __name__)


@bp.route("/buscar/logica", methods=['POST'])
async def busqueda_logica():
    try:
        data = request.get_json()
        incluir_data = data.get('incluir', {})
        excluir_data = data.get('excluir', {})
    except Exception:
        return jsonify({"error": "JSON mal formateado"}), 400

    incluir_directores = "|".join(map(str, incluir_data.get('directores', [])))
    incluir_actores = "|".join(map(str, incluir_data.get('actores', [])))
    incluir_generos = "|".join(map(str, incluir_data.get('generos', [])))
    excluir_directores = "|".join(map(str, excluir_data.get('directores', [])))
    excluir_actores = "|".join(map(str, excluir_data.get('actores', [])))
    excluir_generos = "|".join(map(str, excluir_data.get('generos', [])))

    async with httpx.AsyncClient() as client:
        # Creamos una lista de "tareas" (las 6 llamadas a la API)
        tareas = [
            fetch_movies_by_criteria(client, 'with_crew', incluir_directores),
            fetch_movies_by_criteria(client, 'with_cast', incluir_actores),
            fetch_movies_by_criteria(client, 'with_genres', incluir_generos),
            fetch_movies_by_criteria(client, 'with_crew', excluir_directores),
            fetch_movies_by_criteria(client, 'with_cast', excluir_actores),
            fetch_movies_by_criteria(client, 'with_genres', excluir_generos),
        ]
        
        # asyncio.gather() ejecuta todas las tareas al mismo tiempo
        resultados_api = await asyncio.gather(*tareas)

    # 4. Combinar resultados de INCLUSIÓN (C_incl)
    inclusion_map = {}
    inclusion_map.update(resultados_api[0]) # Directores incluir
    inclusion_map.update(resultados_api[1]) # Actores incluir
    inclusion_map.update(resultados_api[2]) # Géneros incluir

    # 5. Combinar resultados de EXCLUSIÓN (C_excl)
    exclusion_map = {}
    exclusion_map.update(resultados_api[3]) # Directores excluir
    exclusion_map.update(resultados_api[4]) # Actores excluir
    exclusion_map.update(resultados_api[5]) # Géneros excluir

    # 6. Aplicar la Lógica Proposicional (Teoría de Conjuntos)
    # F = C_incl AND (NOT C_excl) -> Set(Inclusión) - Set(Exclusión)
    
    inclusion_ids = set(inclusion_map.keys())
    exclusion_ids = set(exclusion_map.keys())
    
    final_ids = inclusion_ids.difference(exclusion_ids)
    
    # 7. Preparar los resultados finales
    resultados_finales = [inclusion_map[id] for id in final_ids]

    return jsonify(resultados_finales)
