import os
import pickle
import numpy as np
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ruta esperada del paquete generado por `entrenar_modelo.py`
RECOMMENDER_PKL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'recommender_data.pkl')

# Variables cargadas
_MOVIE_VECTORS = None
_ID_MAP = None  # tmdb_id -> index
_METADATA = None
_META_MAP = None  # tmdb_id -> metadata dict


def _load_recommender():
    global _MOVIE_VECTORS, _ID_MAP, _METADATA, _META_MAP
    if _MOVIE_VECTORS is not None:
        return True

    try:
        with open(RECOMMENDER_PKL, 'rb') as f:
            data = pickle.load(f)

        _MOVIE_VECTORS = np.asarray(data.get('movie_vectors'))
        _ID_MAP = data.get('map_id_to_index', {})
        _METADATA = data.get('movies_metadata', [])
        _META_MAP = {m['tmdb_id']: m for m in _METADATA if isinstance(m, dict) and 'tmdb_id' in m}

        # Normalize embeddings for fast cosine via dot product
        if _MOVIE_VECTORS is not None:
            norms = np.linalg.norm(_MOVIE_VECTORS, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-12)
            _MOVIE_VECTORS[:] = _MOVIE_VECTORS / norms

        logger.debug('Recommender cargado: vectors=%s, ids=%s',
                     None if _MOVIE_VECTORS is None else _MOVIE_VECTORS.shape,
                     len(_ID_MAP) if _ID_MAP else 0)
        return True
    except FileNotFoundError:
        logger.error('No se encontró %s. Ejecuta entrenar_modelo.py para generar el paquete.', RECOMMENDER_PKL)
        return False
    except Exception as e:
        logger.exception('Error cargando recommender_data.pkl: %s', e)
        return False


def obtener_peliculas_disponibles():
    """Devuelve lista de TMDb IDs disponibles en el modelo (o None si no cargado)."""
    ok = _load_recommender()
    if not ok:
        return None
    return list(_ID_MAP.keys())


def obtener_recomendaciones_ia(favoritos_tmdb_ids, top_n=20, pesos=None):
    """Genera recomendaciones usando los embeddings de `recommender_data.pkl`.

    Recibe una lista de TMDb ids (enteros). Devuelve una lista de TMDb ids recomendados.
    """
    if not _load_recommender():
        return None

    if not isinstance(favoritos_tmdb_ids, (list, tuple)) or len(favoritos_tmdb_ids) == 0:
        return []

    # Obtener vectores válidos para los favoritos
    fav_vecs = []
    missing = []
    for tmdb in favoritos_tmdb_ids:
        try:
            idx = _ID_MAP.get(int(tmdb))
        except Exception:
            idx = None
        if idx is None:
            missing.append(tmdb)
            continue
        if idx < 0 or idx >= _MOVIE_VECTORS.shape[0]:
            missing.append(tmdb)
            continue
        vec = _MOVIE_VECTORS[idx]
        w = 1.0
        if pesos and tmdb in pesos:
            try:
                w = float(pesos[tmdb])
            except Exception:
                w = 1.0
        fav_vecs.append(vec * w)

    if not fav_vecs:
        logger.debug('No se encontraron vectores para los TMDb favoritos: %s', missing)
        return []

    # Perfil del usuario: promedio + normalización
    user_profile = np.mean(np.stack(fav_vecs, axis=0), axis=0)
    user_profile = user_profile / (np.linalg.norm(user_profile) + 1e-12)

    # Similitud por producto punto (embeddings ya normalizados)
    sim_scores = _MOVIE_VECTORS.dot(user_profile)

    # Obtener indices ordenados de mayor a menor
    candidate_indices = sim_scores.argsort()[::-1]

    recomendaciones = []
    favoritos_set = set()
    for f in favoritos_tmdb_ids:
        try:
            favoritos_set.add(int(f))
        except Exception:
            pass

    # construir mapa inverso tmdb_id <- index
    index_to_tmdb = {v: k for k, v in _ID_MAP.items()}

    for idx in candidate_indices:
        tmdb_id = index_to_tmdb.get(int(idx))
        if tmdb_id is None:
            continue
        if tmdb_id in favoritos_set:
            continue
        recomendaciones.append(tmdb_id)
        if len(recomendaciones) >= top_n:
            break

    logger.debug('Recomendaciones (usando recommender_data.pkl): %s', recomendaciones[:top_n])
    return recomendaciones


def resolver_titulos_a_ids(titulos):
    """Resuelve una lista de títulos (strings) a TMDb IDs disponibles en el modelo.

    Retorna un dict con dos claves: `resolved` (lista de ids encontrados en el mismo orden aproximado)
    y `unresolved` (lista de títulos que no se pudieron resolver).
    """
    if not _load_recommender():
        return None

    if not isinstance(titulos, (list, tuple)):
        return {'resolved': [], 'unresolved': list(titulos) if titulos is not None else []}

    resolved = []
    unresolved = []

    # Preparar mapa de títulos lowercase -> tmdb
    title_map = {}
    for m in _METADATA:
        if not isinstance(m, dict):
            continue
        title = (m.get('title') or m.get('name') or m.get('original_title') or '').strip()
        if title:
            key = title.lower()
            # preferir primeros apariciones
            if key not in title_map and 'tmdb_id' in m:
                title_map[key] = m['tmdb_id']

    for t in titulos:
        if not isinstance(t, str):
            unresolved.append(t)
            continue
        s = t.strip()
        if not s:
            unresolved.append(t)
            continue
        key = s.lower()
        # búsqueda exacta
        tid = title_map.get(key)
        if tid and tid in _ID_MAP:
            resolved.append(tid)
            continue

        # busqueda por substring (primer match)
        found = False
        for k, tid_candidate in title_map.items():
            if key in k and tid_candidate in _ID_MAP:
                resolved.append(tid_candidate)
                found = True
                break
        if found:
            continue

        unresolved.append(t)

    # deduplicate preserving order
    seen = set()
    cleaned = []
    for x in resolved:
        if x not in seen:
            seen.add(x)
            cleaned.append(x)

    return {'resolved': cleaned, 'unresolved': unresolved}

