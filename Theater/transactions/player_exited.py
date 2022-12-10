from BFBC2_MasterServer.packet import Packet
from Theater.models import Game


async def player_exited(connection, message):
    gid = message.Get("GID")
    lid = message.Get("LID")
    pid = message.Get("PID")

    kickPacket = Packet(service="KICK")
    kickPacket.Set("GID", gid)
    kickPacket.Set("LID", lid)
    kickPacket.Set("PID", pid)

    yield kickPacket

    await Game.objects.decrement_active_players(lid, gid)

    response = Packet()
    yield response
