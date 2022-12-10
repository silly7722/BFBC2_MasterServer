from BFBC2_MasterServer.packet import Packet


async def update_bracket(connection, message):
    connection.currentlyUpdating = message.Get("START")

    yield Packet()
