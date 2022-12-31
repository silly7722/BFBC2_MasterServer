from BFBC2_MasterServer.packet import Packet
from Theater.models import Game


async def get_game_details(connection, message):
    lid = message.Get("LID")
    gid = message.Get("GID")

    response = Packet()

    if not lid or not gid:
        yield response
        return

    gameData = await Game.objects.get_game_data(lid, gid)

    for key in gameData:
        response.Set(key, gameData[key])

    yield response

    gameDetails = await Game.objects.get_game_details(lid, gid)

    response = Packet(service="GDET")

    for key in gameDetails:
        response.Set(key, gameDetails[key])

    yield response
