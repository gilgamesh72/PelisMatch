import requests
import pandas as pd
import numpy as np
import pickle
import time
from sklearn.preprocessing import MultiLabelBinarizer
from tensorflow.keras import layers, models

# --- CONFIGURACIÓN ---
API_KEY = "310313c5dfcadae4d9bb178828d491a0"
BASE_URL = "https://api.themoviedb.org/3"
PAGES_TO_FETCH = 50  # 50 páginas * 20 pelis = 1000 películas para el ejemplo

def fetch_tmdb_data():
    """Descarga películas populares y sus géneros de TMDB"""
    movies = []
    print("📥 Descargando datos de TMDB...")
    
    for page in range(1, PAGES_TO_FETCH + 1):
        url = f"{BASE_URL}/movie/popular?api_key={API_KEY}&language=es-ES&page={page}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for item in data['results']:
                movies.append({
                    'tmdb_id': item['id'],
                    'title': item['title'],
                    'genre_ids': item['genre_ids'], # Lista ej: [28, 12]
                    'vote_average': item['vote_average']
                })
        else:
            print(f"Error en página {page}")
        
        if page % 10 == 0:
            print(f"   ... Procesadas {page} páginas")
            time.sleep(0.2) # Respetar límites de API
            
    return pd.DataFrame(movies)

def build_content_embedding_model(input_dim, embedding_dim=32):
    """
    Crea una Red Neuronal simple para comprimir los géneros (Sparse)
    en un vector denso (Embedding) que representa el 'alma' de la película.
    """
    input_layer = layers.Input(shape=(input_dim,))
    
    # Capa densa para aprender relaciones entre géneros (ej. Terror suele ir con Suspenso)
    dense_1 = layers.Dense(64, activation='relu')(input_layer)
    
    # Capa de Embedding (El vector comprimido que usaremos)
    embedding_layer = layers.Dense(embedding_dim, activation='linear', name='movie_embedding')(dense_1)
    
    # Capa de salida (reconstrucción - Autoencoder simple)
    output_layer = layers.Dense(input_dim, activation='sigmoid')(embedding_layer)
    
    model = models.Model(inputs=input_layer, outputs=output_layer)
    model.compile(optimizer='adam', loss='binary_crossentropy')
    
    # Modelo auxiliar solo para extraer el vector
    encoder = models.Model(inputs=input_layer, outputs=embedding_layer)
    
    return model, encoder

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    # 1. Obtener Datos
    df = fetch_tmdb_data()
    print(f"✅ Total películas descargadas: {len(df)}")

    # 2. Preprocesamiento (One-Hot Encoding de Géneros)
    # Convertimos [28, 12] en [1, 1, 0, 0...]
    mlb = MultiLabelBinarizer()
    X_genres = mlb.fit_transform(df['genre_ids'])
    
    print(f"Dimensiones de entrada (Num Pelis, Num Géneros): {X_genres.shape}")

    # 3. Entrenamiento de Red Neuronal
    # Entrenamos la red para que aprenda a comprimir estos géneros
    full_model, encoder_model = build_content_embedding_model(input_dim=X_genres.shape[1])
    
    print("🧠 Entrenando red neuronal para entender géneros...")
    full_model.fit(X_genres, X_genres, epochs=10, batch_size=32, verbose=1)

    # 4. Extraer los Vectores (Embeddings)
    # Ahora cada película es un vector de 32 números
    movie_vectors = encoder_model.predict(X_genres)

    # 5. Crear Diccionario de Mapeo (CRUCIAL)
    # Necesitamos encontrar rápido la fila del vector dado un ID de TMDB
    id_to_index_map = {tmdb_id: idx for idx, tmdb_id in enumerate(df['tmdb_id'])}

    # 6. Guardar todo para Flask
    data_package = {
        'movie_vectors': movie_vectors,      # La matriz numpy (N, 32)
        'map_id_to_index': id_to_index_map,  # Diccionario {550: 0, ...}
        'movies_metadata': df[['tmdb_id', 'title', 'vote_average']].to_dict('records') # Info para mostrar
    }

    with open('recommender_data.pkl', 'wb') as f:
        pickle.dump(data_package, f)
    
    print("💾 ¡Archivos guardados en 'recommender_data.pkl'! Listo para Flask.")