import requests
import httpx
from ..config import API_KEY, BASE_URL, IMAGE_BASE_URL
from rapidfuzz import fuzz, process


def buscar_pelicula_por_nombre(nombre, min_score: int = 60):
    """Busca una película por nombre usando coincidencia exacta o aproximada.

    1. Realiza búsqueda en TMDb (/search/movie) con el texto ingresado.
    2. Si hay resultados, aplica fuzzy matching (rapidfuzz) sobre los títulos
       para elegir la mejor coincidencia (token_set_ratio) por encima de
       'min_score'. Si no supera el umbral pero hay resultados, toma el primero.
    3. Devuelve el JSON de detalles completos (/movie/{id}).

    Args:
        nombre (str): Texto ingresado por el usuario.
        min_score (int): Umbral mínimo de similitud (0-100) para aceptar
            la coincidencia difusa. Por defecto 60.

    Returns:
        dict | None: JSON de detalles de la película o None si no se encuentra.
    """
    try:
        url = f"{BASE_URL}/search/movie"
        params = {'api_key': API_KEY, 'query': nombre, 'language': 'es-ES'}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        resultados = response.json().get('results', [])

        if not resultados:
            return None

        # Preparar lista de títulos para fuzzy
        titulos = [r.get('title', '') for r in resultados]
        mejor = None
        try:
            # process.extractOne devuelve (choice, score, index)
            mejor = process.extractOne(
                nombre,
                titulos,
                scorer=fuzz.token_set_ratio,
                score_cutoff=min_score
            )
        except Exception as fe:
            print(f"Fuzzy error: {fe}")

        if mejor:
            _, score, idx = mejor
            elegido = resultados[idx]
            print(f"Fuzzy match '{nombre}' -> '{elegido.get('title')}' (score={score})")
        else:
            # Fallback al primer resultado de TMDb
            elegido = resultados[0]
            print(f"Fuzzy sin coincidencia >= {min_score}. Usando primer resultado: '{elegido.get('title')}'")

        pelicula_id = elegido['id']
        url_detalles = f"{BASE_URL}/movie/{pelicula_id}"
        params_detalles = {'api_key': API_KEY, 'language': 'es-ES'}
        response_detalles = requests.get(url_detalles, params=params_detalles, timeout=10)
        response_detalles.raise_for_status()
        return response_detalles.json()

    except requests.RequestException as e:
        print(f"Error en API búsqueda fuzzy: {e}")
        return None


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
        # Usamos await client.get() en lugar de requests.get()
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


async def buscar_persona_remoto(client, nombre, limit=5):
    """Consulta TMDb /search/person y retorna candidatos con score fuzzy local al nombre."""
    from ..utils import normalizar_texto
    
    url = f"{BASE_URL}/search/person"
    params = {'api_key': API_KEY, 'query': nombre, 'language': 'es-ES'}
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        results = r.json().get('results', [])[:limit]
        out = []
        for p in results:
            nombre_p = p.get('name', '')
            score = fuzz.token_set_ratio(normalizar_texto(nombre), normalizar_texto(nombre_p))
            out.append({'nombre': nombre_p, 'id': p.get('id'), 'score': score})
        return sorted(out, key=lambda x: x['score'], reverse=True)
    except httpx.RequestError as e:
        print(f"Error remoto persona: {e}")
        return []


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
