import numpy as np
#from sklearn.metrics.pairwise import cosine_similarity
from ..data import cargador_modelo
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _normalize_embeddings(embeddings):
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return embeddings / norms



def obtener_recomendaciones_ia(favoritos_tmdb_ids, top_n=20, pesos=None):
    """
    Genera recomendaciones basadas en una lista de películas favoritas.
    
    Args:
        favoritos_tmdb_ids: Lista de IDs de TMDb de películas favoritas
        top_n: Número de recomendaciones a devolver
        
    Returns:
        list: Lista de TMDb IDs recomendados
    """
    # Verificar que el modelo esté cargado
    if getattr(cargador_modelo, "movie_embeddings", None) is None:
        logger.debug("Modelo NO cargado: cargador_modelo.movie_embeddings es None")
        return None
    # if cargador_modelo.movie_embeddings is None:
    #     return None

    embeddings = cargador_modelo.movie_embeddings
    movie_map = cargador_modelo.movie_map
    movie_idx_to_id = cargador_modelo.movie_idx_to_id
    tmdb_to_movielens = cargador_modelo.tmdb_to_movielens
    movielens_to_tmdb = cargador_modelo.movielens_to_tmdb
    
    # logger.debug("Tamaños de mapas: movie_embeddings=%s, movie_map=%s, tmdb_to_movielens=%s, movielens_to_tmdb=%s",
    #              getattr(cargador_modelo, "movie_embeddings", None).shape if getattr(cargador_modelo, "movie_embeddings", None) is not None else None,
    #              None if cargador_modelo.movie_map is None else len(cargador_modelo.movie_map),
    #              None if cargador_modelo.tmdb_to_movielens is None else len(cargador_modelo.tmdb_to_movielens),
    #              None if cargador_modelo.movielens_to_tmdb is None else len(cargador_modelo.movielens_to_tmdb))

    logger.debug("Tamaños: embeddings=%s, movie_map=%s, tmdb_to_movielens=%s, movielens_to_tmdb=%s",
                 embeddings.shape, len(movie_map), len(tmdb_to_movielens), len(movielens_to_tmdb))

    # Normalizar embeddings para que el coseno/producto punto sea consistente
    embeddings_norm = _normalize_embeddings(embeddings)
    
    # 2. Traducir IDs y obtener vectores ("ADN")
    favorite_vectors = []
    missing_tmdb = []
    for tmdb_id in favoritos_tmdb_ids:
        # Traducción: tmdbId -> movieId
        movie_id = tmdb_to_movielens.get(tmdb_id)
        if movie_id is None:
            missing_tmdb.append(tmdb_id)
            continue
        
        # Traducción: movieId -> movie_idx
        movie_idx = movie_map.get(movie_id)
        if movie_idx is None:
            missing_tmdb.append(tmdb_id)
            continue

        if movie_idx >= embeddings_norm.shape[0]:
            missing_tmdb.append(tmdb_id)
            continue
        vec = embeddings_norm[movie_idx]
        w = 1.0
            
        # Obtener el "ADN" de esa película
        if pesos and tmdb_id in pesos:
            try:
                w = float(pesos[tmdb_id])
            except Exception:
                w = 1.0
        favorite_vectors.append(vec * w)
        logger.debug("Favorito mapeado: tmdb=%s -> movielens=%s -> idx=%s (peso=%s)", tmdb_id, movie_id, movie_idx, w)
    
    if missing_tmdb:
        logger.debug("TMDb no encontrados en mapas: %s", missing_tmdb)

    if not favorite_vectors:
        logger.debug("No se encontraron vectores para los TMDb favoritos proporcionados.")
        return []

    # # 3. Crear el "Perfil de Gusto" del usuario (promedio de "ADN")
    # user_profile = np.mean(favorite_vectors, axis=0)
    # user_profile_reshaped = user_profile.reshape(1, -1) # Para Scikit-learn

    # Perfil de usuario: promedio ponderado de embeddings (mantiene la esencia NN)
    user_profile = np.mean(np.stack(favorite_vectors, axis=0), axis=0)
    user_profile = user_profile / (np.linalg.norm(user_profile) + 1e-12)

    # # 4. Calcular Similitud contra TODAS las películas
    # similarities = cosine_similarity(user_profile_reshaped, cargador_modelo.movie_embeddings)
    # sim_scores = similarities[0]

    # Similitud: producto punto con embeddings normalizados (equivalente a cosine)
    sim_scores = embeddings_norm.dot(user_profile)

    # # 5. Obtener el Top 20 (para tener margen)
    # top_indices = sim_scores.argsort()[-20:][::-1]
    
    # Tomar un margen mayor y filtrar luego favoritos reales
    top_indices = sim_scores.argsort()[-(top_n * 3):][::-1]

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

    logger.debug("Recomendaciones TMDb top: %s", recomendaciones_ids[:top_n])
    return recomendaciones_ids


def obtener_peliculas_disponibles():
    """
    Devuelve la lista de TMDb IDs disponibles en el modelo.
    """
    if cargador_modelo.movielens_to_tmdb is None:
        return None
    return list(set(cargador_modelo.movielens_to_tmdb.values()))
