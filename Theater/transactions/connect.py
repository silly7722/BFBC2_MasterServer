from time import time

from BFBC2_MasterServer.packet import Packet


async def connect(connection, message):
    """Handle connection transaction"""

    if connection.initialized:
        connection.logger.error("Client is already initialized")
        return

    prot = message.Get("PROT")

    initData = {
        "protocolVersion": prot,
        "product": message.Get("PROD"),
        "version": message.Get("VERS"),
        "platform": message.Get("PLAT"),
        "locale": message.Get("LOCALE"),
        "sdkVersion": message.Get("SDKVERSION"),
    }

    # Check if all required fields were provided by client
    if any(map(lambda x: x is None, initData.values())):
        connection.logger.error("Client sent invalid Connection packet")
        return

    await connection.initialize(initData)

    response = Packet()
    response.Set("TIME", int(time()))
    response.Set("activityTimeoutSecs", 240)
    response.Set("PROT", prot)

    yield response
