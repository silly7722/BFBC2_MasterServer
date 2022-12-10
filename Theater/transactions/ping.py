from BFBC2_MasterServer.packet import Packet


async def ping(connection, message):
    yield Packet()
