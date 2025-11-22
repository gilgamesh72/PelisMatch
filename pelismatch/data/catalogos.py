# Mapa de géneros TMDb
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

# Mapa para las décadas
DECADAS_CHOICES_MAP = {
    "clasico": ('release_date.lte', '2000-01-01'),
    "antiguo": ('release_date.lte', '2000-01-01'),
    "viejo": ('release_date.lte', '2000-01-01'),
    "reciente": ('release_date.gte', '2000-01-01'),
    "moderno": ('release_date.gte', '2000-01-01'),
    "nuevo": ('release_date.gte', '2000-01-01')
}

# Opciones para respuesta 'ninguno'
NINGUNO_CHOICES = ["ninguno", "nadie", "no", "saltar", "omitir"]

# Catálogo de directores populares
directores_tmdb = [
    {"nombre": "Christopher Nolan", "id": 525},
    {"nombre": "Steven Spielberg", "id": 488},
    {"nombre": "Quentin Tarantino", "id": 138},
    {"nombre": "Martin Scorsese", "id": 1032},
    {"nombre": "Stanley Kubrick", "id": 240},
    {"nombre": "Guillermo del Toro", "id": 10828},
    {"nombre": "Greta Gerwig", "id": 139820},
    {"nombre": "James Cameron", "id": 2710},
    {"nombre": "Tim Burton", "id": 510},
    {"nombre": "Hayao Miyazaki", "id": 608},
    {"nombre": "Francis Ford Coppola", "id": 1776},
    {"nombre": "Alfred Hitchcock", "id": 2636}
]

# Catálogo de actores populares
actores_tmdb = [
    {"nombre": "Brad Pitt", "id": 287},
    {"nombre": "Tom Cruise", "id": 500},
    {"nombre": "Leonardo DiCaprio", "id": 6193},
    {"nombre": "Robert Downey Jr.", "id": 3223},
    {"nombre": "Scarlett Johansson", "id": 1245},
    {"nombre": "Johnny Depp", "id": 85},
    {"nombre": "Tom Hanks", "id": 31},
    {"nombre": "Margot Robbie", "id": 234352},
    {"nombre": "Meryl Streep", "id": 5064},
    {"nombre": "Denzel Washington", "id": 5292},
    {"nombre": "Emma Stone", "id": 54693},
    {"nombre": "Cillian Murphy", "id": 2037}
]
