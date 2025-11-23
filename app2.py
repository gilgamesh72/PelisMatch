from flask import Flask, request, jsonify
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# --- CARGA DE DATOS AL INICIO ---
print("⏳ Cargando modelo y datos...")
try:
    with open('recommender_data.pkl', 'rb') as f:
        data = pickle.load(f)
        
    MOVIE_VECTORS = data['movie_vectors']       # Matriz (N, 32)
    ID_MAP = data['map_id_to_index']            # {tmdb_id: indice_matriz}
    METADATA = data['movies_metadata']          # Lista de dicts con titulos
    
    # Creamos un mapa inverso para buscar metadata rápido por ID
    META_MAP = {m['tmdb_id']: m for m in METADATA}
    # Mapa de títulos (lowercase) -> tmdb_id para resolver favoritos por nombre
    TITLE_MAP = {}
    for m in METADATA:
        if isinstance(m, dict):
            title = m.get('title') or m.get('name') or m.get('original_title')
            if title and 'tmdb_id' in m:
                TITLE_MAP[title.strip().lower()] = m['tmdb_id']
    
    print("✅ Sistema de recomendación listo.")
except FileNotFoundError:
    print("❌ ERROR: No se encontró 'recommender_data.pkl'. Ejecuta entrenar_modelo.py primero.")

# --- LÓGICA DE RECOMENDACIÓN ---
def get_recommendations(favorite_tmdb_ids, top_k=5):
    valid_indices = []
    
    # 1. Traducir IDs de TMDB a Índices de nuestra Matriz
    for tmdb_id in favorite_tmdb_ids:
        if tmdb_id in ID_MAP:
            valid_indices.append(ID_MAP[tmdb_id])
    
    if not valid_indices:
        return {"error": "Ninguna de las películas favoritas está en nuestra base de datos actual."}

    # 2. Obtener vectores de los favoritos y calcular el PROMEDIO
    # Si te gusta Matrix (Accion/SciFi) y Toy Story (Animacion), el promedio busca el centro.
    fav_vectors = MOVIE_VECTORS[valid_indices]
    user_profile = np.mean(fav_vectors, axis=0).reshape(1, -1)

    # 3. Similitud de Coseno contra TODAS las películas
    # Esto compara el perfil del usuario contra las 1000 pelis en milisegundos
    similarities = cosine_similarity(user_profile, MOVIE_VECTORS)[0]

    # 4. Ordenar y Filtrar
    # argsort devuelve índices de menor a mayor, invertimos con [::-1]
    similar_indices = similarities.argsort()[::-1]
    
    results = []
    for idx in similar_indices:
        # Ignorar las películas que ya están en favoritos (no recomendar lo que ya vio)
        if idx not in valid_indices:
            tmdb_id_found = METADATA[idx]['tmdb_id']
            movie_info = META_MAP.get(tmdb_id_found)
            # Obtener posible ruta/URL del poster desde distintos campos
            poster_path = None
            if isinstance(movie_info, dict):
                poster_path = movie_info.get('poster_path') or movie_info.get('poster') or movie_info.get('image') or movie_info.get('poster_url')

            if poster_path:
                if str(poster_path).startswith('http'):
                    image_url = poster_path
                else:
                    image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            else:
                image_url = ""

            results.append({
                "id": movie_info['tmdb_id'] if movie_info else tmdb_id_found,
                "titulo": movie_info.get('title') if movie_info else "",
                "coincidencia": round(float(similarities[idx]) * 100, 2),
                "imagen": image_url
            })
            
        if len(results) >= top_k:
            break
            
    return results


def _resolve_favorites_to_ids(favorites):
    """Convierte una lista de entradas (ids numéricos o títulos) a una lista de tmdb_ids válidos.
    Se intenta resolver números, strings numéricos, coincidencia exacta por título y búsqueda por substring.
    """
    resolved = []
    for fav in favorites:
        # Números ya como int
        try:
            if isinstance(fav, (int,)):
                if fav in ID_MAP:
                    resolved.append(int(fav))
                    continue
        except Exception:
            pass

        # Strings: puede ser un número en texto o un título
        if isinstance(fav, str):
            s = fav.strip()
            if s.isdigit():
                v = int(s)
                if v in ID_MAP:
                    resolved.append(v)
                    continue

            key = s.lower()
            # coincidencia rápida en TITLE_MAP
            tid = TITLE_MAP.get(key)
            if tid:
                resolved.append(tid)
                continue

            # busqueda más laxa: exacta sobre metadata
            found = False
            for m in METADATA:
                if not isinstance(m, dict):
                    continue
                t = (m.get('title') or m.get('name') or '').strip().lower()
                if t == key:
                    resolved.append(m.get('tmdb_id'))
                    found = True
                    break
            if found:
                continue

            # búsqueda por substring (primer match)
            for m in METADATA:
                if not isinstance(m, dict):
                    continue
                t = (m.get('title') or m.get('name') or '').strip().lower()
                if key in t and m.get('tmdb_id'):
                    resolved.append(m.get('tmdb_id'))
                    found = True
                    break
            if found:
                continue

    # eliminar duplicados y None
    cleaned = []
    for x in resolved:
        if x and x not in cleaned:
            cleaned.append(x)
    return cleaned

# --- ENDPOINT ---
@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Recibe JSON: { "favorites": [550, 155, 12] }
    """
    req_data = request.get_json()
    
    if not req_data or 'favorites' not in req_data:
        return jsonify({'error': 'Falta la lista "favorites" con IDs de TMDB'}), 400

    fav_ids = req_data['favorites']

    # Resolver favoritos que pueden ser títulos a tmdb ids
    resolved_ids = _resolve_favorites_to_ids(fav_ids)
    if not resolved_ids:
        return jsonify({
            'error': 'No se pudieron resolver los favoritos a IDs válidos',
            'provided_favorites': fav_ids,
            'resolved_ids': resolved_ids
        }), 400

    recommendations = get_recommendations(resolved_ids)
    
    return jsonify({
        "user_favorites": fav_ids,
        "resolved_ids": resolved_ids,
        "recommendations": recommendations
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)