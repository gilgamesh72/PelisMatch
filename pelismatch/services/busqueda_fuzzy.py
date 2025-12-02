from rapidfuzz import fuzz, process
from ..utils import normalizar_texto
from ..data import directores_tmdb, actores_tmdb


# Construcción de índices para búsqueda local rápida
def _build_person_indices():
    try:
        actores_index = {normalizar_texto(a['nombre']): a for a in actores_tmdb}
        directores_index = {normalizar_texto(d['nombre']): d for d in directores_tmdb}
        return actores_index, directores_index
    except Exception:
        return {}, {}


ACTORES_INDEX, DIRECTORES_INDEX = _build_person_indices()


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


def fuzzy_persona_local(query, max_candidates=6, cutoff=70):
    """Devuelve lista de candidatos locales (actores/directores) con score >= cutoff.
    Cada candidato: {tipo, nombre, id, score}
    """
    q = normalizar_texto(query)
    choices = list(ACTORES_INDEX.keys()) + list(DIRECTORES_INDEX.keys())
    if not choices:
        return []
    resultados = process.extract(
        q,
        choices,
        scorer=fuzz.token_set_ratio,
        score_cutoff=cutoff,
        limit=max_candidates
    )
    candidatos = []
    for choice, score, _ in resultados:
        if choice in ACTORES_INDEX:
            item = ACTORES_INDEX[choice]; tipo = 'actor'
        else:
            item = DIRECTORES_INDEX[choice]; tipo = 'director'
        candidatos.append({
            'tipo': tipo,
            'nombre': item['nombre'],
            'id': item['id'],
            'score': score
        })
    return candidatos
