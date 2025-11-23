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

# def recomendaciones_debug(favoritos_tmdb_ids, top_n=30, strategy='average', vecinos_k=10):
#     """
#     Devuelve mappings y candidatos con score para depuración.
#     mappings: list of {tmdb, movielens, idx}
#     candidatos: list of {tmdb, movielens, idx, score}
#     """
#     if getattr(cargador_modelo, "movie_embeddings", None) is None:
#         logger.debug("Modelo no cargado en recomendaciones_debug")
#         return None

#     embeddings = cargador_modelo.movie_embeddings
#     embeddings_norm = _normalize_embeddings(embeddings)
#     movie_map = cargador_modelo.movie_map or {}
#     movie_idx_to_id = cargador_modelo.movie_idx_to_id or {}
#     tmdb_to_movielens = cargador_modelo.tmdb_to_movielens or {}
#     movielens_to_tmdb = cargador_modelo.movielens_to_tmdb or {}

#     logger.debug("recomendaciones_debug: tamaños embeddings=%s movie_map=%s tmdb_to_movielens=%s movielens_to_tmdb=%s",
#                  embeddings.shape if embeddings is not None else None,
#                  len(movie_map),
#                  len(tmdb_to_movielens),
#                  len(movielens_to_tmdb))

#     mappings = []
#     fav_vectors = []
#     for tmdb in favoritos_tmdb_ids:
#         mov_id = tmdb_to_movielens.get(tmdb)
#         idx = movie_map.get(mov_id) if mov_id is not None else None
#         mappings.append({"tmdb": int(tmdb), "movielens": int(mov_id) if mov_id is not None else None, "idx": int(idx) if idx is not None else None})
#         if idx is not None and 0 <= idx < embeddings_norm.shape[0]:
#             fav_vectors.append((tmdb, embeddings_norm[idx], mov_id, idx))
#         else:
#             logger.debug("favorito no mapeado a vector: tmdb=%s movielens=%s idx=%s", tmdb, mov_id, idx)

#     if not fav_vectors:
#         logger.debug("recomendaciones_debug: no hay vectores para favoritos recibidos: %s", favoritos_tmdb_ids)
#         return {"mappings": mappings, "candidatos": []}

#     # Strategy: vecinos por favorito (agrega scores) o perfil promedio
#     if strategy == 'neighbors':
#         score_map = {}
#         for tmdb, vec, mov_id, idx in fav_vectors:
#             sims = embeddings_norm.dot(vec)  # 1D
#             top_idx = sims.argsort()[-(vec.shape[0] if False else vecinos_k+1):][::-1]
#             for i in top_idx:
#                 movie_id = movie_idx_to_id.get(int(i))
#                 if movie_id is None:
#                     continue
#                 tm = movielens_to_tmdb.get(movie_id)
#                 if tm is None:
#                     continue
#                 score_map[int(tm)] = score_map.get(int(tm), 0.0) + float(sims[int(i)])
#         candidatos = sorted([{"tmdb": k, "score": v} for k, v in score_map.items()], key=lambda x: -x["score"])[:top_n]
#     else:
#         # average profile
#         stacked = np.stack([v for (_, v, _, _) in fav_vectors], axis=0)
#         profile = np.mean(stacked, axis=0)
#         profile = profile / (np.linalg.norm(profile) + 1e-12)
#         sims = embeddings_norm.dot(profile)
#         top_idx = sims.argsort()[-top_n:][::-1]
#         candidatos = []
#         for i in top_idx:
#             movie_id = movie_idx_to_id.get(int(i))
#             if movie_id is None:
#                 continue
#             tm = movielens_to_tmdb.get(movie_id)
#             if tm is None:
#                 continue
#             candidatos.append({"tmdb": int(tm), "movielens": int(movie_id), "idx": int(i), "score": float(sims[int(i)])})

#     logger.debug("recomendaciones_debug: mapas %s candidatos_top %s", len(mappings), candidatos[:5])
#     return {"mappings": mappings, "candidatos": candidatos}


# def obtener_recomendaciones_ia(favoritos_tmdb_ids, top_n=20, pesos=None, strategy='average'):
#     """
#     Devuelve lista de TMDb IDs recomendados (usa embeddings / red neuronal).
#     """
#     debug = recomendaciones_debug(favoritos_tmdb_ids, top_n=max(50, top_n * 3), strategy=strategy, vecinos_k=10)
#     if debug is None:
#         return None

#     candidatos = [c.get("tmdb") for c in debug.get("candidatos", []) if c.get("tmdb")]
#     if not candidatos:
#         logger.debug("obtener_recomendaciones_ia: no hay candidatos tras debug. mappings=%s", debug.get("mappings"))
#         return []

#     recomendaciones = [int(x) for x in candidatos[:top_n]]
#     logger.debug("obtener_recomendaciones_ia -> recomendaciones: %s", recomendaciones[:10])
#     return recomendaciones


# def vecinos_de_pelicula_tmdb(tmdb_id, top_n=10):
#     """Devuelve vecinos TMDb de una película (debug)."""
#     if getattr(cargador_modelo, "movie_embeddings", None) is None:
#         return None

#     embeddings = cargador_modelo.movie_embeddings
#     embeddings_norm = _normalize_embeddings(embeddings)
#     movie_map = cargador_modelo.movie_map or {}
#     movie_idx_to_id = cargador_modelo.movie_idx_to_id or {}
#     movielens_to_tmdb = cargador_modelo.movielens_to_tmdb or {}
#     tmdb_to_movielens = cargador_modelo.tmdb_to_movielens or {}

#     movielens_id = tmdb_to_movielens.get(tmdb_id)
#     if movielens_id is None:
#         return []

#     idx = movie_map.get(movielens_id)
#     if idx is None or idx >= embeddings_norm.shape[0]:
#         return []

#     vec = embeddings_norm[int(idx)].reshape(1, -1)
#     sims = embeddings_norm.dot(vec.T).ravel()
#     top_idx = sims.argsort()[-(top_n + 1):][::-1]
#     result = []
#     for i in top_idx:
#         mid = movie_idx_to_id.get(int(i))
#         if mid is None:
#             continue
#         t = movielens_to_tmdb.get(mid)
#         if t and t != tmdb_id:
#             result.append(int(t))
#         if len(result) >= top_n:
#             break
#     logger.debug("Vecinos para %s -> %s", tmdb_id, result[:5])
#     return result

# def recomendaciones_debug(favoritos_tmdb_ids, top_n=30, strategy='average', vecinos_k=10):
#     """
#     Devuelve estructura para debugging:
#       - mappings: listado de (tmdb, movielens, idx)
#       - candidatos: lista de (tmdb, movielens_id, idx, score)
#     strategy: 'average' (perfil promedio) o 'neighbors' (agrupar vecinos por favorito)
#     """
#     if getattr(cargador_modelo, "movie_embeddings", None) is None:
#         return None

#     embeddings = cargador_modelo.movie_embeddings
#     embeddings_norm = _normalize_embeddings(embeddings)
#     movie_map = cargador_modelo.movie_map
#     movie_idx_to_id = cargador_modelo.movie_idx_to_id
#     tmdb_to_movielens = cargador_modelo.tmdb_to_movielens
#     movielens_to_tmdb = cargador_modelo.movielens_to_tmdb

#     logger.debug("recomendaciones_debug: tamaños embeddings=%s movie_map=%s tmdb_to_movielens=%s movielens_to_tmdb=%s",
#                  embeddings.shape if embeddings is not None else None,
#                  len(movie_map),
#                  len(tmdb_to_movielens),
#                  len(movielens_to_tmdb))

#     mappings = []
#     fav_vectors = []
#     for tmdb in favoritos_tmdb_ids:
#         mov_id = tmdb_to_movielens.get(tmdb)
#         idx = movie_map.get(mov_id) if mov_id is not None else None
#         mappings.append({"tmdb": tmdb, "movielens": mov_id, "idx": idx})
#         if idx is not None and 0 <= idx < embeddings_norm.shape[0]:
#             fav_vectors.append((tmdb, embeddings_norm[idx], mov_id, idx))
#         else:
#             logger.debug("favorito no mapeado a vector: tmdb=%s movielens=%s idx=%s", tmdb, mov_id, idx)
    
#     if not fav_vectors:
#         logger.debug("recomendaciones_debug: no hay vectores para favoritos recibidos: %s", favoritos_tmdb_ids)
#         return {"mappings": mappings, "candidatos": []}


#     # Si strategy == 'neighbors' -> para cada favorito tomar sus k vecinos y combinar scores
#     if strategy == 'neighbors' and fav_vectors:
#         score_map = {}
#         for tmdb, vec, mov_id, idx in fav_vectors:
#             sims = embeddings_norm.dot(vec)  # 1D
#             top_idx = sims.argsort()[-(vec.shape[0] if False else vecinos_k+1):][::-1]
#             for i in top_idx:
#                 movie_id = movie_idx_to_id.get(int(i))
#                 if movie_id is None:
#                     continue
#                 tm = movielens_to_tmdb.get(movie_id)
#                 if tm is None:
#                     continue
#                 score_map[tm] = score_map.get(tm, 0.0) + float(sims[int(i)])
#         candidatos = sorted([{"tmdb": k, "score": v} for k,v in score_map.items()], key=lambda x: -x["score"])[:top_n]
#     else:
#         # average profile
#         stacked = np.stack([v for (_,v,_,_) in fav_vectors], axis=0)
#         profile = np.mean(stacked, axis=0)
#         profile = profile / (np.linalg.norm(profile) + 1e-12)
#         sims = embeddings_norm.dot(profile)
#         top_idx = sims.argsort()[-top_n:][::-1]
#         candidatos = []
#         for i in top_idx:
#             movie_id = movie_idx_to_id.get(int(i))
#             if movie_id is None:
#                 continue
#             tm = movielens_to_tmdb.get(movie_id)
#             if tm is None:
#                 continue
#             candidatos.append({"tmdb": int(tm), "movielens": movie_id, "idx": int(i), "score": float(sims[int(i)])})
    
#     logger.debug("recomendaciones_debug: mapas %s candidatos_top %s", len(mappings), candidatos[:5])

#     return {"mappings": mappings, "candidatos": candidatos}

# def obtener_recomendaciones_ia(favoritos_tmdb_ids, top_n=20, pesos=None, strategy='average'):
#     """
#     Devuelve lista de TMDb IDs recomendados (usa embeddings / red neuronal).
#     """
#     debug = recomendaciones_debug(favoritos_tmdb_ids, top_n=max(50, top_n * 3), strategy=strategy, vecinos_k=10)
#     if debug is None:
#         return None

#     candidatos = [c.get("tmdb") for c in debug.get("candidatos", []) if c.get("tmdb")]
#     if not candidatos:
#         logger.debug("obtener_recomendaciones_ia: no hay candidatos tras debug. mappings=%s", debug.get("mappings"))
#         return []

#     # Mantener orden top_n y convertir a int
#     recomendaciones = [int(x) for x in candidatos[:top_n]]
#     logger.debug("obtener_recomendaciones_ia -> recomendaciones: %s", recomendaciones[:10])
#     return recomendaciones

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
