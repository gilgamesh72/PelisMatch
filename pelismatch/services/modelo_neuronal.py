import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from ..data import cargador_modelo


def obtener_recomendaciones_ia(favoritos_tmdb_ids, top_n=10):
    """
    Genera recomendaciones basadas en una lista de películas favoritas.
    
    Args:
        favoritos_tmdb_ids: Lista de IDs de TMDb de películas favoritas
        top_n: Número de recomendaciones a devolver
        
    Returns:
        list: Lista de TMDb IDs recomendados
    """
    # Verificar que el modelo esté cargado
    if cargador_modelo.movie_embeddings is None:
        return None
    
    # 2. Traducir IDs y obtener vectores ("ADN")
    favorite_vectors = []
    for tmdb_id in favoritos_tmdb_ids:
        # Traducción: tmdbId -> movieId
        movie_id = cargador_modelo.tmdb_to_movielens.get(tmdb_id)
        if not movie_id:
            continue
        
        # Traducción: movieId -> movie_idx
        movie_idx = cargador_modelo.movie_map.get(movie_id)
        if not movie_idx:
            continue
            
        # Obtener el "ADN" de esa película
        favorite_vectors.append(cargador_modelo.movie_embeddings[movie_idx])

    if not favorite_vectors:
        return None

    # 3. Crear el "Perfil de Gusto" del usuario (promedio de "ADN")
    user_profile = np.mean(favorite_vectors, axis=0)
    user_profile_reshaped = user_profile.reshape(1, -1) # Para Scikit-learn

    # 4. Calcular Similitud contra TODAS las películas
    similarities = cosine_similarity(user_profile_reshaped, cargador_modelo.movie_embeddings)
    sim_scores = similarities[0]

    # 5. Obtener el Top 20 (para tener margen)
    top_indices = sim_scores.argsort()[-20:][::-1]

    # 6. Traducir de vuelta y devolver
    recomendaciones_ids = []
    movielens_favoritos = [cargador_modelo.tmdb_to_movielens.get(id) for id in favoritos_tmdb_ids]
    
    for idx in top_indices:
        movie_id = cargador_modelo.movie_idx_to_id.get(idx)
        
        # ¡IMPORTANTE! No recomendar una película que ya está en favoritos
        if movie_id in movielens_favoritos:
            continue
            
        tmdb_id = cargador_modelo.movielens_to_tmdb.get(movie_id)
        if tmdb_id:
            recomendaciones_ids.append(tmdb_id)
            
        # Parar cuando tengamos suficientes recomendaciones
        if len(recomendaciones_ids) >= top_n:
            break

    return recomendaciones_ids


def obtener_peliculas_disponibles():
    """
    Devuelve la lista de TMDb IDs disponibles en el modelo.
    """
    if cargador_modelo.movielens_to_tmdb is None:
        return None
    return list(set(cargador_modelo.movielens_to_tmdb.values()))
