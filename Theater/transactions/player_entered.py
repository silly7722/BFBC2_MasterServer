from BFBC2_MasterServer.packet import Packet


async def player_entered(connection, message):
    pid = message.Get("PID")

    response = Packet()
    response.Set("PID", pid)

    yield response
