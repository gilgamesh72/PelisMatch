from ..config import W_DIRECTOR, W_GENERO, W_ACTOR


def calcular_similitud_optimizado(pelicula_a, pelicula_b):
    """
    Calcula la similitud usando datos pre-cargados que incluyen los créditos.
    """
    peso = 0.0

    # 1. Comparar Director (ya está en los datos)
    director_a = next((p['name'] for p in pelicula_a.get('credits', {}).get('crew', []) if p['job'] == 'Director'), None)
    director_b = next((p['name'] for p in pelicula_b.get('credits', {}).get('crew', []) if p['job'] == 'Director'), None)

    if director_a and director_b and director_a == director_b:
        peso += W_DIRECTOR

    # 2. Comparar Géneros
    generos_a = {g['id'] for g in pelicula_a.get('genres', [])}
    generos_b = {g['id'] for g in pelicula_b.get('genres', [])}
    peso += len(generos_a.intersection(generos_b)) * W_GENERO

    # 3. Comparar Actores Principales
    actores_a = {p['name'] for p in pelicula_a.get('credits', {}).get('cast', [])[:3]}
    actores_b = {p['name'] for p in pelicula_b.get('credits', {}).get('cast', [])[:3]}
    peso += len(actores_a.intersection(actores_b)) * W_ACTOR

    return peso
