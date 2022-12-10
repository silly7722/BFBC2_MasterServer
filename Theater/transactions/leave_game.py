from BFBC2_MasterServer.packet import Packet
from Theater.models import Game


async def leave_game(connection, message):
    lid = message.Get("LID")
    gid = message.Get("GID")

    # TODO: Queue system

    response = Packet()
    response.Set("LID", lid)
    response.Set("GID", gid)

    yield response
