from channels.auth import database_sync_to_async
from django.core.cache import cache

from BFBC2_MasterServer.packet import Packet
from Plasma.models import Persona


async def login(connection, message):
    """Handle login transaction"""

    # Game sends here:
    # {
    #     "CID": "", # Client ID(?) (Always empty?)
    #     "MAC": "$000000000000", # MAC address (Always zeroed-out?)
    #     "SKU": "PC",
    #     "LKEY": "", # Persona login key
    #     "NAME": "", # Persona name(?) (Always empty?)
    # }

    # Server replies with persona name

    lkey = message.Get("LKEY")

    if lkey is None:
        connection.logger.error("Client sent invalid Login packet")
        return

    persona_id = cache.get(f"lkeyMap:{lkey}")

    if persona_id is None:
        connection.logger.error("Invalid persona login key, login failed")
        return

    try:
        persona = await database_sync_to_async(Persona.objects.get)(id=persona_id)
        connection.persona = persona
    except Persona.DoesNotExist:
        connection.logger.error("Login key is for invalid persona, login failed")
        return

    connection.logger.info(f"Persona {persona.name} logged in")

    response = Packet()
    response.Set("NAME", persona.name)

    cache.set(f"theaterSession:{lkey}", connection.channel_name, timeout=None)
    connection.lkey = lkey

    yield response
