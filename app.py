from flask import Flask, jsonify, request, session, render_template, redirect, url_for
from rapidfuzz import fuzz, process
import requests
import asyncio
import httpx
import numpy as np
import json
from sklearn.metrics.pairwise import cosine_similarity
app = Flask(__name__)
app.secret_key = 'cinegraph_2025_diana_katherine'  # Para sesiones del chatbot

# --- 1. CONFIGURACIÓN DE TMDb ---
API_KEY = "310313c5dfcadae4d9bb178828d491a0" 
BASE_URL = "https://api.themoviedb.org/3"
# URL para las imágenes (para que tu compañera de frontend las muestre)
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# --- 2. LÓGICA DEL GRAFO (Cálculo de Pesos) ---
W_DIRECTOR = 3.0
W_GENERO = 2.0
W_ACTOR = 1.5

#=============================NODOS====================================================

async def fetch_movie_details_and_credits(client, movie_id):
    """
    Función asíncrona para obtener detalles y créditos de una película en una sola llamada.
    """
    url = f"{BASE_URL}/movie/{movie_id}"
    # append_to_response=credits es la clave para la optimización
    params = {'api_key': API_KEY, 'language': 'es-ES', 'append_to_response': 'credits'}
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        print(f"Error fetching details for movie {movie_id}: {e}")
        return None

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

def calcular_similitud(pelicula_a, pelicula_b):
    """
    Calcula el peso de la arista (similitud) entre dos películas.
    Ambos 'pelicula_a' y 'pelicula_b' son objetos JSON de TMDb.
    """
    peso = 0.0

    # 1. Comparar Director
    # (Se usa función auxiliar para obtener el director)
    director_a = obtener_director(pelicula_a['id'])
    director_b = obtener_director(pelicula_b['id'])
    
    if director_a and director_b and director_a == director_b:
        peso += W_DIRECTOR

    # 2. Comparar Géneros (TMDb da una lista de géneros)
    generos_a = {g['id'] for g in pelicula_a['genres']}
    generos_b = {g['id'] for g in pelicula_b['genres']}
    
    # Usamos intersección de conjuntos para encontrar el numero de generos iguales
    generos_comunes = generos_a.intersection(generos_b)
    peso += len(generos_comunes) * W_GENERO

    # 3. Comparar Actores Principales
    actores_a = obtener_actores_principales(pelicula_a['id'])
    actores_b = obtener_actores_principales(pelicula_b['id'])
    
    # Usamos intersección para contar actores comunes
    actores_comunes = actores_a.intersection(actores_b)
    peso += len(actores_comunes) * W_ACTOR

    return peso

def obtener_director(pelicula_id):
    """
    Función para obtener el director de una película desde TMDb.
    """
    try:
        # Llama al endpoint de "credits"
        url = f"{BASE_URL}/movie/{pelicula_id}/credits"
        params = {'api_key': API_KEY}
        response = requests.get(url, params=params)
        response.raise_for_status()
        creditos = response.json()
        
        # Busca en el "crew" a la persona cuyo "job" es "Director"
        for persona in creditos.get('crew', []):
            if persona['job'] == 'Director':
                return persona['name']
    except requests.RequestException:
        return None
    return None

def obtener_actores_principales(pelicula_id, num_actores=3):
    """
    Función para obtener los nombres de los N actores principales de una película.
    Por defecto, devuelve los 3 actores con mayor 'order'.
    """
    try:
        # Llama al endpoint de "credits"
        url = f"{BASE_URL}/movie/{pelicula_id}/credits"
        params = {'api_key': API_KEY}
        response = requests.get(url, params=params)
        response.raise_for_status()
        creditos = response.json()
        
        # Filtra los primeros N actores del 'cast' (que ya vienen ordenados por popularidad/importancia)
        actores = [
            actor['name'] 
            for actor in creditos.get('cast', [])
        ]
        
        return set(actores[:num_actores])
    except requests.RequestException:
        return set()
    return set()

def buscar_pelicula_por_nombre(nombre):
    """
    Encuentra la película principal (nodo central) por su nombre.
    """
    try:
        url = f"{BASE_URL}/search/movie"
        params = {'api_key': API_KEY, 'query': nombre, 'language': 'es-ES'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        resultados = response.json().get('results', [])
        
        if not resultados:
            return None
        
        # Devuelve el ID de la primera película encontrada
        primera_pelicula_id = resultados[0]['id']
        
        # Ahora obtenemos los detalles completos de esa película
        url_detalles = f"{BASE_URL}/movie/{primera_pelicula_id}"
        params_detalles = {'api_key': API_KEY, 'language': 'es-ES'}
        response_detalles = requests.get(url_detalles, params=params_detalles)
        response_detalles.raise_for_status()
        
        return response_detalles.json()
        
    except requests.RequestException as e:
        print(f"Error en API: {e}")
        return None

# --- 3. ENDPOINT DE LA API (Flask) ---

@app.route("/similares/<string:nombre_pelicula>")
async def get_similares(nombre_pelicula): # <--- CONVERTIDO A ASYNC
    """
    Este endpoint busca una película y devuelve sus películas similares
    basadas en el grafo de similitud DINÁMICO calculado con TMDb.
    ¡VERSIÓN OPTIMIZADA CON LLAMADAS ASÍNCRONAS!
    """
    
    # 1. Encontrar el Nodo Central (la película buscada)
    # Esta parte sigue siendo síncrona, pero es solo una llamada.
    pelicula_principal_sync = buscar_pelicula_por_nombre(nombre_pelicula)
    if not pelicula_principal_sync:
        return jsonify({"error": "Película no encontrada"}), 404

    # 2. Encontrar Nodos Vecinos (candidatos)
    url_recomendadas = f"{BASE_URL}/movie/{pelicula_principal_sync['id']}/recommendations"
    params = {'api_key': API_KEY, 'language': 'es-ES'}
    try:
        # Esta llamada inicial también puede ser síncrona
        response_vecinos = requests.get(url_recomendadas, params=params)
        response_vecinos.raise_for_status()
        vecinos_candidatos = response_vecinos.json().get('results', [])
    except requests.RequestException:
        return jsonify({"error": "No se pudieron obtener recomendaciones"}), 500

    # 3. Calcular Pesos de Aristas y Ordenar (¡LA PARTE OPTIMIZADA!)
    resultados_similares = []
    
    async with httpx.AsyncClient() as client:
        # Obtener los detalles de la película principal con créditos
        pelicula_principal_task = fetch_movie_details_and_credits(client, pelicula_principal_sync['id'])
        
        # Crear una lista de tareas para obtener todos los detalles de los vecinos en paralelo
        tareas_vecinos = [fetch_movie_details_and_credits(client, vecino['id']) for vecino in vecinos_candidatos]
        
        # Ejecutar todas las tareas en paralelo
        resultados_completos = await asyncio.gather(pelicula_principal_task, *tareas_vecinos)

    pelicula_principal = resultados_completos[0]
    vecinos_completos = resultados_completos[1:]

    if not pelicula_principal:
         return jsonify({"error": "No se pudo obtener detalles de la película principal"}), 500

    for vecino_completo in vecinos_completos:
        if vecino_completo:
            # Aqui se aplica la logica de grafos con la función optimizada
            peso_arista = calcular_similitud_optimizado(pelicula_principal, vecino_completo)
            
            if peso_arista > 0:
                resultados_similares.append({
                    "nombre": vecino_completo['title'],
                    "similitud": peso_arista,
                    "poster_url": f"{IMAGE_BASE_URL}{vecino_completo.get('poster_path', '')}"
                })

    # 4. Ordenar los vecinos por el peso calculado
    vecinos_ordenados = sorted(resultados_similares, key=lambda x: x['similitud'], reverse=True)

    # 5. Devolver el JSON final
    return jsonify({
        "pelicula_buscada": {
            "nombre": pelicula_principal['title'],
            "poster_url": f"{IMAGE_BASE_URL}{pelicula_principal.get('poster_path', '')}",
            "overview": pelicula_principal['overview']
        },
        "similares": vecinos_ordenados
    })

#=================================PROPOSICIONES LOGICAS====================================================0
async def fetch_movies_by_criteria(client, parametro, ids_string):
    """
    Esta función es 'async' y usa 'httpx' (client).
    Devuelve un DICCIONARIO de películas {id: info}.
    """
    if not ids_string:
        return {} # No hacer llamada si no hay IDs

    url = f"{BASE_URL}/discover/movie"
    params = {
        'api_key': API_KEY,
        'language': 'es-ES',
        parametro: ids_string,
        'sort_by': 'popularity.desc'
    }
    
    try:
        #Usamos await client.get() en lugar de requests.get()
        response = await client.get(url, params=params)
        response.raise_for_status() # Lanza error si la API falla
        resultados = response.json().get('results', [])
        
        movies_map = {}
        for movie in resultados:
            movies_map[movie['id']] = {
                "nombre": movie['title'],
                "poster_url": f"{IMAGE_BASE_URL}{movie.get('poster_path', '')}",
                "overview": movie.get('overview', 'No disponible.')
            }
        return movies_map
        
    except httpx.RequestError as e:
        print(f"Error en API (fetch_movies_by_criteria): {e}")
        return {}

# --- ENDPOINT DE BÚSQUEDA LÓGICA (ASÍNCRONO) ---

@app.route("/buscar/logica", methods=['POST'])
async def busqueda_logica(): # CAMBIO: El endpoint ahora es 'async def'
    """
    Este endpoint implementa la lógica proposicional de forma ASÍNCRONA.
    """
    
    # 1. Obtener los datos JSON (esto no cambia)
    try:
        data = request.get_json()
        incluir_data = data.get('incluir', {})
        excluir_data = data.get('excluir', {})
    except Exception:
        return jsonify({"error": "JSON mal formateado"}), 400

    # 2. Formatear los IDs 
    incluir_directores = "|".join(map(str, incluir_data.get('directores', [])))
    incluir_actores = "|".join(map(str, incluir_data.get('actores', [])))
    incluir_generos = "|".join(map(str, incluir_data.get('generos', [])))
    excluir_directores = "|".join(map(str, excluir_data.get('directores', [])))
    excluir_actores = "|".join(map(str, excluir_data.get('actores', [])))
    excluir_generos = "|".join(map(str, excluir_data.get('generos', [])))

    # 3. Ejecutar todas las llamadas en PARALELO
    async with httpx.AsyncClient() as client:
        # Creamos una lista de "tareas" (las 6 llamadas a la API)
        tareas = [
            fetch_movies_by_criteria(client, 'with_crew', incluir_directores),
            fetch_movies_by_criteria(client, 'with_cast', incluir_actores),
            fetch_movies_by_criteria(client, 'with_genres', incluir_generos),
            fetch_movies_by_criteria(client, 'with_crew', excluir_directores),
            fetch_movies_by_criteria(client, 'with_cast', excluir_actores),
            fetch_movies_by_criteria(client, 'with_genres', excluir_generos),
        ]
        
        # asyncio.gather() ejecuta todas las tareas al mismo tiempo
        # 'resultados_api' será una lista con los 6 diccionarios de resultados
        resultados_api = await asyncio.gather(*tareas)

    # 4. Combinar resultados de INCLUSIÓN (C_incl)
    inclusion_map = {}
    inclusion_map.update(resultados_api[0]) # Directores incluir
    inclusion_map.update(resultados_api[1]) # Actores incluir
    inclusion_map.update(resultados_api[2]) # Géneros incluir

    # 5. Combinar resultados de EXCLUSIÓN (C_excl)
    exclusion_map = {}
    exclusion_map.update(resultados_api[3]) # Directores excluir
    exclusion_map.update(resultados_api[4]) # Actores excluir
    exclusion_map.update(resultados_api[5]) # Géneros excluir

    # 6. Aplicar la Lógica Proposicional (Teoría de Conjuntos)
    # F = C_incl AND (NOT C_excl) -> Set(Inclusión) - Set(Exclusión)
    
    inclusion_ids = set(inclusion_map.keys())
    exclusion_ids = set(exclusion_map.keys())
    
    final_ids = inclusion_ids.difference(exclusion_ids)
    
    # 7. Preparar los resultados finales
    resultados_finales = [inclusion_map[id] for id in final_ids]

    return jsonify(resultados_finales)


#========================================= CHAT BOT ======================================================00000
GENEROS_MAP = {
    "accion": 28,
    "aventura": 12,
    "animacion": 16,
    "comedia": 35,
    "crimen": 80,
    "documental": 99,
    "drama": 18,
    "familia": 10751,
    "fantasia": 14,
    "historia": 36,
    "terror": 27,
    "musica": 10402,
    "misterio": 9648,
    "romance": 10749,
    "ciencia ficcion": 878,
    "pelicula de tv": 10770,
    "suspense": 53,
    "guerra": 10752,
    "western": 37
}

# Mapa mejorado para las décadas
DECADAS_CHOICES_MAP = {
    # (El texto que el usuario podría escribir): (parámetro_api, valor_api)
    "clasico": ('release_date.lte', '2000-01-01'),
    "antiguo": ('release_date.lte', '2000-01-01'),
    "viejo": ('release_date.lte', '2000-01-01'),
    "reciente": ('release_date.gte', '2000-01-01'),
    "moderno": ('release_date.gte', '2000-01-01'),
    "nuevo": ('release_date.gte', '2000-01-01')
}

# Opciones para la respuesta 'ninguno'
NINGUNO_CHOICES = ["ninguno", "nadie", "no", "saltar", "omitir"]

def normalizar_texto(texto):
    """
    Limpia y normaliza el texto para la comparación difusa.
    """
    texto = texto.lower()
    # Mantenemos tildes y eñes, quitamos otros caracteres no alfanuméricos
    texto = ''.join(c for c in texto if c.isalnum() or c == ' ' or c in 'áéíóúüñ')
    return texto.strip()

def find_best_match(query, choices_dict, score_cutoff=75):
    """
    Busca la mejor coincidencia difusa en las *claves* de un diccionario.
    Devuelve la clave y el valor de la mejor coincidencia si supera el score_cutoff.
    """
    normalized_query = normalizar_texto(query)
    choices_list = list(choices_dict.keys())
    
    # process.extractOne devuelve (choice, score, index)
    resultado_fuzz = process.extractOne(
        normalized_query,
        choices_list,
        scorer=fuzz.token_set_ratio,
        score_cutoff=score_cutoff
    )
    
    if resultado_fuzz:
        mejor_coincidencia_key, score, _ = resultado_fuzz
        print(f"Coincidencia difusa (score: {score}): '{query}' -> '{mejor_coincidencia_key}'")
        mejor_coincidencia_value = choices_dict[mejor_coincidencia_key]
        # Devuelve la clave (para la respuesta) y el valor (para la API)
        return mejor_coincidencia_key, mejor_coincidencia_value
    
    print(f"Sin coincidencia difusa para: '{query}'")
    return None, None

# --- 3. FUNCIONES ASÍNCRONAS DE API ---

async def buscar_id_persona(client, nombre):
    """
    Busca el ID de un actor o director por nombre.
    """
    try:
        url = f"{BASE_URL}/search/person"
        params = {'api_key': API_KEY, 'query': nombre, 'language': 'es-ES'}
        response = await client.get(url, params=params)
        response.raise_for_status()
        resultados = response.json().get('results', [])
        if resultados:
            return resultados[0]['id'] # Devuelve el ID de la primera coincidencia
    except httpx.RequestError as e:
        print(f"Error buscando persona: {e}")
    return None

async def recomendar_con_chatbot(client, collected_data):
    """
    Llama a la API /discover de TMDb con los datos recopilados.
    """
    params = {
        'api_key': API_KEY,
        'language': 'es-ES',
        'sort_by': 'popularity.desc'
    }

    if 'genero_id' in collected_data:
        params['with_genres'] = collected_data['genero_id']

    if 'decada_param' in collected_data:
        clave, valor = collected_data['decada_param']
        params[clave] = valor 

    if 'persona_id' in collected_data:
        params['with_people'] = collected_data['persona_id']

    try:
        url = f"{BASE_URL}/discover/movie"
        response = await client.get(url, params=params)
        response.raise_for_status()
        resultados = response.json().get('results', [])
        return [p['title'] for p in resultados[:3]]
    except httpx.RequestError as e:
        print(f"Error en /discover: {e}")
        return ["Error al buscar recomendaciones."]
    except Exception as e:
        print(f"Error inesperado en API: {e}")
        return ["Hubo un problema con la API."]

# --- ENDPOINT DEL CHATBOT (FSM) ---

@app.route("/chatbot", methods=['POST'])
async def handle_chatbot():
    """
    Maneja la conversación del chatbot usando FSM y lógica difusa.
    """
    
    data = request.get_json()
    user_message = data.get('message', '')
    
    current_state = session.get('state', 'S0_INICIO')
    collected_data = session.get('data', {})

    # Comando universal para reiniciar
    if normalizar_texto(user_message) in ['reset', 'salir', 'cancelar', 'reiniciar']:
        session.clear()
        return jsonify({"respuesta": "Conversación reiniciada. ¿En qué te puedo ayudar?"})

    # ESTADO S0: INICIO
    if current_state == 'S0_INICIO':
        session['state'] = 'S1_GENERO'
        session['data'] = {} 
        return jsonify({"respuesta": "¡Hola! Te ayudaré a encontrar una película. ¿Qué género te gustaría? (Ej: Acción, Comedia, Drama, Ciencia Ficción)"})

    # ESTADO S1: ESPERANDO GÉNERO (CON LÓGICA DIFUSA)
    elif current_state == 'S1_GENERO':
        
        # *** INICIO DE LA MODIFICACIÓN FUZZY ***
        matched_key, genero_id = find_best_match(user_message, GENEROS_MAP, score_cutoff=70)
        
        if not genero_id:
            # Si el usuario escribe 'comedia romantica', 'genero_id' será None
            # porque no es una coincidencia directa.
            return jsonify({"respuesta": "No entendí ese género. Por favor, intenta de nuevo (Ej: Acción, Comedia, Drama)."})
        # *** FIN DE LA MODIFICACIÓN FUZZY ***

        collected_data['genero_id'] = genero_id
        session['data'] = collected_data
        session['state'] = 'S2_DECADA'
        # Usamos 'matched_key' para una respuesta más natural
        return jsonify({"respuesta": f"¡{matched_key.capitalize()}! ¿Buscas algo 'clásico' (antes de 2000) o 'reciente' (2000 en adelante)?"})

    # ESTADO S2: ESPERANDO DÉCADA (CON LÓGICA DIFUSA)
    elif current_state == 'S2_DECADA':
        
        # *** INICIO DE LA MODIFICACIÓN FUZZY ***
        matched_key, decada_param = find_best_match(user_message, DECADAS_CHOICES_MAP, score_cutoff=70)

        if not decada_param:
            return jsonify({"respuesta": "No entendí eso. Por favor, di 'clásico' o 'reciente'."})
        # *** FIN DE LA MODIFICACIÓN FUZZY ***

        collected_data['decada_param'] = decada_param
        session['data'] = collected_data
        session['state'] = 'S3_PERSONA'
        return jsonify({"respuesta": f"Entendido, algo '{matched_key}'. ¿Tienes algún actor o director en mente? (Escribe un nombre o 'ninguno')"})

    # ESTADO S3: ESPERANDO PERSONA (CON LÓGICA DIFUSA PARA 'NINGUNO')
    elif current_state == 'S3_PERSONA':
        
        async with httpx.AsyncClient() as client:
            
            # *** INICIO DE LA MODIFICACIÓN FUZZY ***
            normalized_query = normalizar_texto(user_message)
            ninguno_match = process.extractOne(
                normalized_query,
                NINGUNO_CHOICES,
                scorer=fuzz.token_set_ratio,
                score_cutoff=80
            )
            
            if ninguno_match:
                print(f"Coincidencia difusa para 'ninguno': {ninguno_match[0]}")
                # El usuario dijo 'ninguno', no hacemos nada con 'persona_id'
            # *** FIN DE LA MODIFICACIÓN FUZZY ***
            else:
                # Si no es 'ninguno', buscamos a la persona
                persona_id = await buscar_id_persona(client, user_message)
                if persona_id:
                    collected_data['persona_id'] = persona_id
                else:
                    return jsonify({"respuesta": f"No encontré a '{user_message}'. ¿Quieres intentar con otro nombre o decir 'ninguno'?"})

            # ¡ESTADO FINAL!
            recomendaciones = await recomendar_con_chatbot(client, collected_data)

        session.clear()
        
        # Formatear la respuesta final
        if recomendaciones:
            respuesta_final = "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones)
        else:
            respuesta_final = "No encontré películas con esos criterios. ¡Empecemos de nuevo!"
            
        return jsonify({
            "respuesta": respuesta_final,
            "recomendaciones": recomendaciones,
            "criterios_usados": collected_data
        })
    
    session.clear()
    return jsonify({"respuesta": "Hubo un error en mi lógica. Empecemos de nuevo."})

#================================= REDES NEURONALES ===================================================
try:

    
    # Cargar los "ADN de Película"
    movie_embeddings = np.load('movie_embeddings.npy')
    print("Embeddings 'movie_embeddings.npy' cargados.")

    # Cargar TODOS los mapas
    with open('model_maps.json', 'r') as f:
        model_maps = json.load(f)
    
    # Convertir claves de JSON (string) a int/numérico
    movie_map = {int(k): v for k, v in model_maps['movie_map'].items()}
    movie_idx_to_id = {int(k): v for k, v in model_maps['movie_idx_to_id'].items()}
    tmdb_to_movielens = {int(k): v for k, v in model_maps['tmdb_to_movielens'].items()}
    movielens_to_tmdb = {int(k): v for k, v in model_maps['movielens_to_tmdb'].items()}
    

except Exception as e:
    print(f"Error fatal al cargar modelos o mapas: {e}")
    print("Asegúrate de ejecutar 'train_model.py' primero.")
    movie_embeddings = None


# --- FUNCIÓN AUXILIAR ASÍNCRONA PARA BUSCAR DETALLES ---
# para obtener los pósters y títulos al final
async def fetch_movie_details(client, tmdb_id):
    """Obtiene los detalles de un tmdb_id."""
    if not tmdb_id:
        return None
    url = f"{BASE_URL}/movie/{int(tmdb_id)}"
    params = {'api_key': API_KEY, 'language': 'es-ES'}
    try:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                "titulo": data['title'],
                "tmdb_id": int(tmdb_id),
                "poster_url": f"{IMAGE_BASE_URL}{data.get('poster_path', '')}"
            }
    except httpx.RequestError as e:
        print(f"Error buscando detalles de {tmdb_id}: {e}")
    return None

# --- ENDPOINT DE RECOMENDACIÓN NN---

@app.route("/recomendaciones/favoritos", methods=['POST'])
async def get_recomendaciones_favoritos():
    """
    Genera recomendaciones de NN basadas en una lista de 
    favoritos (TMDb IDs) del usuario.
    """
    if movie_embeddings is None:
        return jsonify({"error": "El servicio de recomendación no está listo."}), 503

    # 1. Obtener la lista de favoritos del usuario
    try:
        data = request.get_json()
        favoritos_tmdb_ids = data.get('favoritos_tmdb_ids', [])
        # Asegurarnos de que sean enteros
        favoritos_tmdb_ids = [int(id) for id in favoritos_tmdb_ids]
    except Exception:
        return jsonify({"error": "JSON mal formateado. Se esperaba {'favoritos_tmdb_ids': [id1, id2, ...]}"}), 400

    if not favoritos_tmdb_ids:
        return jsonify({"error": "La lista de favoritos está vacía."}), 400

    # 2. Traducir IDs y obtener vectores ("ADN")
    favorite_vectors = []
    for tmdb_id in favoritos_tmdb_ids:
        # Traducción: tmdbId -> movieId
        movie_id = tmdb_to_movielens.get(tmdb_id)
        if not movie_id:
            continue
        
        # Traducción: movieId -> movie_idx
        movie_idx = movie_map.get(movie_id)
        if not movie_idx:
            continue
            
        # Obtener el "ADN" de esa película
        favorite_vectors.append(movie_embeddings[movie_idx])

    if not favorite_vectors:
        return jsonify({"error": "Ninguna de las películas favoritas se encontró en nuestro modelo de datos."}), 404

    # 3. Crear el "Perfil de Gusto" del usuario (promedio de "ADN")
    user_profile = np.mean(favorite_vectors, axis=0)
    user_profile_reshaped = user_profile.reshape(1, -1) # Para Scikit-learn

    # 4. Calcular Similitud contra TODAS las películas
    # Compara el perfil del usuario (1, 50) contra todas las películas (N, 50)
    similarities = cosine_similarity(user_profile_reshaped, movie_embeddings)
    
    # 'similarities' es un array [1, N], lo aplanamos
    sim_scores = similarities[0]

    # 5. Obtener el Top 20 (para tener margen)
    # .argsort() da los índices de menor a mayor
    top_indices = sim_scores.argsort()[-20:][::-1] # Invertido (mayor a menor)

    # 6. Traducir de vuelta y devolver
    recomendaciones_ids = []
    movielens_favoritos = [tmdb_to_movielens.get(id) for id in favoritos_tmdb_ids]
    
    for idx in top_indices:
        movie_id = movie_idx_to_id.get(idx)
        
        # ¡IMPORTANTE! No recomendar una película que ya está en favoritos
        if movie_id in movielens_favoritos:
            continue
            
        tmdb_id = movielens_to_tmdb.get(movie_id)
        if tmdb_id:
            recomendaciones_ids.append(tmdb_id)
            
        # Parar cuando tengamos 10 recomendaciones
        if len(recomendaciones_ids) >= 10:
            break

    # 7. Obtener detalles de TMDb para una respuesta amigable
    async with httpx.AsyncClient() as client:
        tareas = [fetch_movie_details(client, tmdb_id) for tmdb_id in recomendaciones_ids]
        resultados_detalles = await asyncio.gather(*tareas)
    
    # Filtrar cualquier resultado 'None' si una API falló
    resultados_finales = [res for res in resultados_detalles if res is not None]

    return jsonify({
        "basado_en": favoritos_tmdb_ids,
        "recomendaciones": resultados_finales
    })

# ================================= RUTAS DEL FRONTEND ===================================================

@app.route('/')
def index():
    """Página principal del sistema"""
    return render_template('index.html')

@app.route('/top-movies')
def top_movies():
    """Página de mejores películas (Top N Ponderado)"""
    return render_template('top_movies.html')

@app.route('/teoria')
def teoria():
    """Página explicativa de la teoría matemática"""
    return render_template('teoria.html')

@app.route('/resultados')
def resultados():
    """Página de resultados de búsqueda"""
    return render_template('resultados.html')

# Endpoint para obtener películas más populares (Top N Ponderado)
@app.route('/api/top-peliculas')
def api_top_peliculas():
    """
    Endpoint para obtener las mejores películas usando función de media ponderada.
    Implementa el concepto de Top N Ponderado del proyecto.
    """
    try:
        # Obtener películas populares de TMDb
        url = f"{BASE_URL}/movie/popular"
        params = {
            'api_key': API_KEY,
            'language': 'es-ES',
            'page': 1
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        peliculas = response.json().get('results', [])
        
        # Calcular puntuación ponderada: (rating * num_votos) / (num_votos + constante)
        # Esta es la función de Media Ponderada mencionada en el proyecto
        peliculas_ponderadas = []
        
        for pelicula in peliculas[:20]:  # Top 20
            rating = pelicula.get('vote_average', 0)
            votos = pelicula.get('vote_count', 0)
            
            # Función de ponderación (similar a IMDb weighted rating)
            # W = (v ÷ (v+m)) × R + (m ÷ (v+m)) × C
            # donde: v = votos, m = mínimo votos, R = rating promedio, C = rating global promedio
            m = 1000  # Mínimo de votos requeridos
            C = 7.0   # Rating promedio global
            
            if votos >= 100:  # Filtrar películas con pocos votos
                peso_ponderado = (votos / (votos + m)) * rating + (m / (votos + m)) * C
                
                peliculas_ponderadas.append({
                    "tmdb_id": pelicula['id'],
                    "titulo": pelicula['title'],
                    "rating_original": rating,
                    "votos": votos,
                    "puntuacion_ponderada": round(peso_ponderado, 2),
                    "poster_url": f"{IMAGE_BASE_URL}{pelicula.get('poster_path', '')}",
                    "overview": pelicula.get('overview', 'No disponible')
                })
        
        # Ordenar por puntuación ponderada
        peliculas_ponderadas.sort(key=lambda x: x['puntuacion_ponderada'], reverse=True)
        
        return jsonify({
            "peliculas": peliculas_ponderadas,
            "explicacion": "Ranking calculado usando función de media ponderada: W = (v÷(v+m)) × R + (m÷(v+m)) × C"
        })
        
    except requests.RequestException as e:
        return jsonify({"error": "Error al obtener datos de películas"}), 500

if __name__ == '__main__':
    app.run(debug=True)