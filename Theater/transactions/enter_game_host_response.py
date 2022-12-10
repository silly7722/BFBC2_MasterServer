from BFBC2_MasterServer.packet import Packet
from Theater.models import Game


async def enter_game_host_response(connection, message):
    lid = message.Get("LID")
    gid = message.Get("GID")

    isAllowed = message.Get("ALLOWED")

    if isAllowed:
        # Update player count on server
        await Game.objects.increment_joining_players(lid, gid)

    yield Packet()
