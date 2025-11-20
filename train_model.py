import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import Input, Embedding, Flatten, Dense, Concatenate
from tensorflow.keras.models import Model
import json

# Cargar los datos
ratings_df = pd.read_csv('ml-latest-small/ratings.csv')
movies_df = pd.read_csv('ml-latest-small/movies.csv')
links_df = pd.read_csv('ml-latest-small/links.csv')

# Preparacion de datos
user_ids = ratings_df['userId'].unique()
movie_ids = ratings_df['movieId'].unique()

user_map = {int(id): i for i, id in enumerate(user_ids)}
movie_map = {int(id): i for i, id in enumerate(movie_ids)}

# Mapeo inverso (para encontrar el título después)
movie_idx_to_id = {i: int(id) for id, i in movie_map.items()}



# Aplicar los mapeos a dataframe
ratings_df['user_idx'] = ratings_df['userId'].map(user_map)
ratings_df['movie_idx'] = ratings_df['movieId'].map(movie_map)

# Contar el número de usuarios y películas únicos
n_users = len(user_map)
n_movies = len(movie_map)

# Preparar el mapeo entre movieId y tmdbId
links_df = links_df.dropna(subset=['tmdbId'])
links_df['tmdbId'] = links_df['tmdbId'].astype(int)

# Crear los diccionarios traductores
tmdb_to_movielens = {int(tmdbId): int(movieId) for tmdbId, movieId in zip(links_df.tmdbId, links_df.movieId)}
movielens_to_tmdb = {int(movieId): int(tmdbId) for movieId, tmdbId in zip(links_df.movieId, links_df.tmdbId)}



maps_to_save = {
    'user_map': user_map,       # userId -> user_idx
    'movie_map': movie_map,     # movieId -> movie_idx
    'movie_idx_to_id': movie_idx_to_id, # movie_idx -> movieId
    'tmdb_to_movielens': tmdb_to_movielens, # tmdbId -> movieId
    'movielens_to_tmdb': movielens_to_tmdb  # movieId -> tmdbId
}

with open('model_maps.json', 'w') as f:
    json.dump(maps_to_save, f)
print("Mapas guardados en 'model_maps.json'.")


# --- Construcción de la Red Neuronal (Neural Collaborative Filtering) ---

# 1. Capas de Entrada
user_input = Input(shape=[1], name='user_input')
movie_input = Input(shape=[1], name='movie_input')

# 2. Capas de Embedding (El "aprendizaje" de características latentes)
# Usaremos un embedding de 50 dimensiones para cada uno
embedding_size = 50

user_embedding = Embedding(input_dim=n_users, 
                           output_dim=embedding_size, 
                           name='user_embedding')(user_input)
movie_embedding_layer = Embedding(input_dim=n_movies, 
                                  output_dim=embedding_size, 
                                  name='movie_embedding') 
movie_embedding = movie_embedding_layer(movie_input)

# 3. Aplanar los embeddings
user_vec = Flatten(name='flatten_user')(user_embedding)
movie_vec = Flatten(name='flatten_movie')(movie_embedding)

# 4. Concatenar los vectores
concat = Concatenate()([user_vec, movie_vec])

# 5. Red de Perceptrón Multicapa 
dense1 = Dense(128, activation='relu')(concat)
dense2 = Dense(64, activation='relu')(dense1)
output = Dense(1)(dense2) # Salida: una sola neurona para predecir el rating

# 6. Crear el Modelo
model = Model(inputs=[user_input, movie_input], outputs=output)
model.compile(optimizer='adam', loss='mean_squared_error')

# Preparar datos de entrenamiento
X = [ratings_df['user_idx'], ratings_df['movie_idx']]
y = ratings_df['rating']

print("Iniciando entrenamiento...")
model.fit(X, y, 
          batch_size=64, 
          epochs=20, 
          validation_split=0.1)

# --- Guardar el Modelo ---
print("Entrenamiento finalizado. Guardando modelo...")
model.save('recommender_model.h5')
print("¡Modelo guardado como 'recommender_model.h5'!")

# Extraer los pesos de la capa de embedding
movie_embeddings = movie_embedding_layer.get_weights()[0]

# Guardarlo como un archivo NumPy para carga rápida
np.save('movie_embeddings.npy', movie_embeddings)