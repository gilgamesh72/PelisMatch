import numpy as np
import json

# Variables globales para almacenar los datos cargados
movie_embeddings = None
movie_map = None
movie_idx_to_id = None
tmdb_to_movielens = None
movielens_to_tmdb = None



def cargar_modelo():
    global movie_embeddings, movie_map, movie_idx_to_id, tmdb_to_movielens, movielens_to_tmdb
    
    try:
        movie_embeddings = np.load('movie_embeddings.npy')
        print("Embeddings cargados.")

        with open('model_maps.json', 'r') as f:
            model_maps = json.load(f)
        
        # movie_map = {int(k): v for k, v in model_maps['movie_map'].items()}
        # movie_idx_to_id = {int(k): v for k, v in model_maps['movie_idx_to_id'].items()}
        # tmdb_to_movielens = {int(k): v for k, v in model_maps['tmdb_to_movielens'].items()}
        # movielens_to_tmdb = {int(k): v for k, v in model_maps['movielens_to_tmdb'].items()}

        # Asegurar que keys y values sean ints donde correspondemovie_map = {int(k): int(v) for k, v in model_maps['movie_map'].items()}
        movielens_to_tmdb = {int(k): int(v) for k, v in model_maps.get('movielens_to_tmdb', {}).items()}
        tmdb_to_movielens = {tmdb: mlen for mlen, tmdb in movielens_to_tmdb.items()}
        movie_map = {int(k): int(v) for k, v in model_maps.get('movie_map', {}).items()}
        movie_idx_to_id = {int(k): int(v) for k, v in model_maps.get('movie_idx_to_id', {}).items()}


        # Filtrar movielens_to_tmdb para que sólo queden movielens con índice/embedding válido
        valid_movielens_to_tmdb = {}
        for mlen_id, tmdb_id in movielens_to_tmdb.items():
            if mlen_id in movie_map and movie_map[mlen_id] < movie_embeddings.shape[0]:
                valid_movielens_to_tmdb[mlen_id] = tmdb_id
        movielens_to_tmdb = valid_movielens_to_tmdb

        # Reconstruir tmdb->movielens a partir del movielens_to_tmdb filtrado (garantiza paridad)
        tmdb_to_movielens = {tmdb: mlen for mlen, tmdb in movielens_to_tmdb.items()}

        print(f"Mapas cargados: embeddings={movie_embeddings.shape}, movie_map={len(movie_map)}, movielens_to_tmdb={len(movielens_to_tmdb)}, tmdb_to_movielens={len(tmdb_to_movielens)}")
        print("Mapas del modelo cargados.")
        return True
        
    except Exception as e:
        print(f"Error al cargar modelos: {e}")
        return False
