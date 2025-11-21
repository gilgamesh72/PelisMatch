from flask import Blueprint, jsonify, request, session
import httpx
from ..services import procesar_chatbot

bp = Blueprint('chatbot_conversacional', __name__)


@bp.route("/chatbot", methods=['POST'])
async def handle_chatbot():
    data = request.get_json()
    user_message = data.get('message', '')
    
    async with httpx.AsyncClient() as client:
        respuesta = await procesar_chatbot(client, user_message, session)
    
    return jsonify(respuesta)
