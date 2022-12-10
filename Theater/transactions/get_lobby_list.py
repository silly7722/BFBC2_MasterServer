from BFBC2_MasterServer.packet import Packet
from Theater.models import Lobby


async def get_lobby_list(connection, message):
    # Game sends filters here, but it doesn't seem to be used in the original server nor game itself
    lobby_list = Packet()

    lobbies = await Lobby.objects.get_lobbies()
    lobby_list.Set("NUM-LOBBIES", len(lobbies))

    yield lobby_list

    for lobby in lobbies:
        lobby_info = Packet(service="LDAT")  # LDAT = Lobby Data
        lobby_info.Set("LID", lobby["lid"])
        lobby_info.Set("PASSING", lobby["numGames"])
        lobby_info.Set("NAME", lobby["name"])
        lobby_info.Set("LOCALE", lobby["locale"])
        lobby_info.Set("MAX-GAMES", lobby["maxGames"])

        # Seems to be static in the original server
        lobby_info.Set("FAVOURITE-GAMES", 0)
        lobby_info.Set("FAVOURITE-PLAYERS", 0)
        lobby_info.Set("NUM-GAMES", lobby["numGames"])

        yield lobby_info
