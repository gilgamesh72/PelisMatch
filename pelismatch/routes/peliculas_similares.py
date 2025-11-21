from flask import Blueprint, jsonify
import asyncio
import httpx
import requests
from ..config import IMAGE_BASE_URL, BASE_URL, API_KEY
from ..services import (
    buscar_pelicula_por_nombre,
    fetch_movie_details_and_credits,
    calcular_similitud_optimizado
)

bp = Blueprint('peliculas_similares', __name__)


@bp.route("/similares/<string:nombre_pelicula>")
async def get_similares(nombre_pelicula):
    pelicula_principal_sync = buscar_pelicula_por_nombre(nombre_pelicula)
    if not pelicula_principal_sync:
        return jsonify({"error": "Película no encontrada"}), 404

    url_recomendadas = f"{BASE_URL}/movie/{pelicula_principal_sync['id']}/recommendations"
    params = {'api_key': API_KEY, 'language': 'es-ES'}
    try:
        response_vecinos = requests.get(url_recomendadas, params=params)
        response_vecinos.raise_for_status()
        vecinos_candidatos = response_vecinos.json().get('results', [])
    except requests.RequestException:
        return jsonify({"error": "No se pudieron obtener recomendaciones"}), 500

    resultados_similares = []
    
    async with httpx.AsyncClient() as client:
        # Obtener los detalles de la película principal con créditos
        pelicula_principal_task = fetch_movie_details_and_credits(client, pelicula_principal_sync['id'])
        
        # Crear una lista de tareas para obtener todos los detalles de los vecinos en paralelo
        tareas_vecinos = [fetch_movie_details_and_credits(client, vecino['id']) for vecino in vecinos_candidatos]
        
        # Ejecutar todas las tareas en paralelo
        resultados_completos = await asyncio.gather(pelicula_principal_task, *tareas_vecinos)

    pelicula_principal = resultados_completos[0]
    vecinos_completos = resultados_completos[1:]

    if not pelicula_principal:
         return jsonify({"error": "No se pudo obtener detalles de la película principal"}), 500

    for vecino_completo in vecinos_completos:
        if vecino_completo:
            # Aqui se aplica la logica de grafos con la función optimizada
            peso_arista = calcular_similitud_optimizado(pelicula_principal, vecino_completo)
            
            if peso_arista > 0:
                resultados_similares.append({
                    "nombre": vecino_completo['title'],
                    "similitud": peso_arista,
                    "poster_url": f"{IMAGE_BASE_URL}{vecino_completo.get('poster_path', '')}"
                })

    # 4. Ordenar los vecinos por el peso calculado
    vecinos_ordenados = sorted(resultados_similares, key=lambda x: x['similitud'], reverse=True)

    # 5. Devolver el JSON final
    return jsonify({
        "pelicula_buscada": {
            "nombre": pelicula_principal['title'],
            "poster_url": f"{IMAGE_BASE_URL}{pelicula_principal.get('poster_path', '')}",
            "overview": pelicula_principal['overview'],
            "tmdb_id": pelicula_principal.get('id')
        },
        "similares": vecinos_ordenados
    })
