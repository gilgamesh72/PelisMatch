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
        
        movie_map = {int(k): v for k, v in model_maps['movie_map'].items()}
        movie_idx_to_id = {int(k): v for k, v in model_maps['movie_idx_to_id'].items()}
        tmdb_to_movielens = {int(k): v for k, v in model_maps['tmdb_to_movielens'].items()}
        movielens_to_tmdb = {int(k): v for k, v in model_maps['movielens_to_tmdb'].items()}
        
        print("Mapas del modelo cargados.")
        return True
        
    except Exception as e:
        print(f"Error al cargar modelos: {e}")
        return False
