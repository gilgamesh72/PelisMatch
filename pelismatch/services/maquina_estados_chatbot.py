from rapidfuzz import fuzz, process
from ..data import GENEROS_MAP, DECADAS_CHOICES_MAP, NINGUNO_CHOICES
from ..utils import normalizar_texto
from .busqueda_fuzzy import find_best_match, fuzzy_persona_local
from .api_tmdb import buscar_persona_remoto, recomendar_con_chatbot


async def procesar_chatbot(client, user_message, session):
    """
    Procesa el mensaje del usuario según el estado actual de la FSM.
    
    Args:
        client: Cliente httpx para llamadas asíncronas
        user_message: Mensaje del usuario
        session: Sesión de Flask con el estado actual
        
    Returns:
        dict: Respuesta JSON para el usuario
    """
    current_state = session.get('state', 'S0_INICIO')
    collected_data = session.get('data', {})

    # Comando universal para reiniciar
    if normalizar_texto(user_message) in ['reset', 'salir', 'cancelar', 'reiniciar']:
        session.clear()
        return {"respuesta": "Conversación reiniciada. ¿En qué te puedo ayudar?"}

    # ESTADO S0: INICIO
    if current_state == 'S0_INICIO':
        session['state'] = 'S1_GENERO'
        session['data'] = {} 
        return {"respuesta": "¡Hola! Te ayudaré a encontrar una película. ¿Qué género te gustaría? (Ej: Acción, Comedia, Drama, Ciencia Ficción)"}

    # ESTADO S1: ESPERANDO GÉNERO (CON LÓGICA DIFUSA)
    elif current_state == 'S1_GENERO':
        matched_key, genero_id = find_best_match(user_message, GENEROS_MAP, score_cutoff=70)
        
        if not genero_id:
            return {"respuesta": "No entendí ese género. Por favor, intenta de nuevo (Ej: Acción, Comedia, Drama)."}

        collected_data['genero_id'] = genero_id
        session['data'] = collected_data
        session['state'] = 'S2_DECADA'
        return {"respuesta": f"¡{matched_key.capitalize()}! ¿Buscas algo 'clásico' (antes de 2000) o 'reciente' (2000 en adelante)?"}

    # ESTADO S2: ESPERANDO DÉCADA (CON LÓGICA DIFUSA)
    elif current_state == 'S2_DECADA':
        matched_key, decada_param = find_best_match(user_message, DECADAS_CHOICES_MAP, score_cutoff=70)

        if not decada_param:
            return {"respuesta": "No entendí eso. Por favor, di 'clásico' o 'reciente'."}

        collected_data['decada_param'] = decada_param
        session['data'] = collected_data
        session['state'] = 'S3_PERSONA'
        return {"respuesta": f"Entendido, algo '{matched_key}'. ¿Tienes algún actor o director en mente? (Escribe un nombre o 'ninguno')"}

    # ESTADO S3: ESPERANDO PERSONA (actor/director) CON CONFIRMACIÓN
    elif current_state == 'S3_PERSONA':
        normalized_query = normalizar_texto(user_message)
        ninguno_match = process.extractOne(
            normalized_query,
            NINGUNO_CHOICES,
            scorer=fuzz.token_set_ratio,
            score_cutoff=80
        )
        if ninguno_match:
            # Sin persona, pasar a recomendación directa
            recomendaciones = await recomendar_con_chatbot(client, collected_data)
            session.clear()
            return {
                "respuesta": "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones),
                "recomendaciones": recomendaciones
            }

        # 1. Intento local (catálogo fijo)
        candidatos_local = fuzzy_persona_local(user_message)
        if len(candidatos_local) == 1:
            collected_data['persona_id'] = candidatos_local[0]['id']
            recomendaciones = await recomendar_con_chatbot(client, collected_data)
            session.clear()
            return {
                "respuesta": "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones),
                "recomendaciones": recomendaciones,
                "seleccion_persona": candidatos_local[0]
            }
        elif len(candidatos_local) > 1:
            # Pedir confirmación
            session['state'] = 'S3_CONFIRMAR_PERSONA'
            session['data'] = collected_data
            session['candidatos'] = candidatos_local
            return {
                "respuesta": "Selecciona uno de los siguientes (envía el ID):",
                "opciones_persona": candidatos_local
            }

        # 2. Remoto si no hubo candidatos locales
        candidatos_remotos = await buscar_persona_remoto(client, user_message)
        if not candidatos_remotos:
            return {"respuesta": f"No encontré coincidencias para '{user_message}'. Intenta otro nombre o 'ninguno'."}
        # Si la mejor tiene score muy alto, usar directa
        if candidatos_remotos[0]['score'] >= 85:
            collected_data['persona_id'] = candidatos_remotos[0]['id']
            recomendaciones = await recomendar_con_chatbot(client, collected_data)
            session.clear()
            return {
                "respuesta": "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones),
                "recomendaciones": recomendaciones,
                "seleccion_persona": candidatos_remotos[0]
            }
        # Pedir confirmación con candidatos remotos
        session['state'] = 'S3_CONFIRMAR_PERSONA'
        session['data'] = collected_data
        session['candidatos'] = candidatos_remotos
        return {
            "respuesta": "¿A quién te refieres? Envía el ID de la lista:",
            "opciones_persona": candidatos_remotos
        }

    # ESTADO S3_CONFIRMAR_PERSONA: usuario envía ID elegido
    elif current_state == 'S3_CONFIRMAR_PERSONA':
        candidatos = session.get('candidatos', [])
        collected_data = session.get('data', {})
        normalized_query = normalizar_texto(user_message)
        # Permitir 'ninguno' aún aquí
        ninguno_match = process.extractOne(
            normalized_query,
            NINGUNO_CHOICES,
            scorer=fuzz.token_set_ratio,
            score_cutoff=80
        )
        if ninguno_match:
            # Ignorar persona y recomendar
            recomendaciones = await recomendar_con_chatbot(client, collected_data)
            session.clear()
            return {
                "respuesta": "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones),
                "recomendaciones": recomendaciones
            }
        # Intentar parsear ID
        try:
            elegido_id = int(user_message.strip())
        except ValueError:
            return {"respuesta": "Por favor envía el ID numérico (o 'ninguno')."}
        if not any(c['id'] == elegido_id for c in candidatos):
            return {"respuesta": "ID no válido. Reenvía uno de los mostrados o 'ninguno'."}
        collected_data['persona_id'] = elegido_id
        recomendaciones = await recomendar_con_chatbot(client, collected_data)
        session.clear()
        return {
            "respuesta": "¡Aquí tienes tus recomendaciones! " + ", ".join(recomendaciones),
            "recomendaciones": recomendaciones,
            "persona_confirmada": elegido_id
        }
    
    session.clear()
    return {"respuesta": "Hubo un error en mi lógica. Empecemos de nuevo."}
