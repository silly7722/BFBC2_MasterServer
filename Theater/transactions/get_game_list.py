from BFBC2_MasterServer.packet import Packet
from Theater.models import Game, Lobby


async def get_game_list(connection, message):
    lobby = await Lobby.objects.get_lobby(message.Get("LID"))

    gameType = message.Get("TYPE")
    gameMod = message.Get("FILTER-ATTR-U-gameMod")
    count = message.Get("COUNT")

    favOnly = message.Get("FILTER-FAV-ONLY")
    favGame = None

    if favOnly:
        favGame = message.Get("FAV-GAME")

    notFull = message.Get("FILTER-NOT-FULL")
    minPlayers = message.Get("FILTER-MIN-SIZE")

    # Attributes
    gamemode = message.Get("FILTER-ATTR-U-gamemode")
    level = message.Get("FILTER-ATTR-U-level")
    region = message.Get("FILTER-ATTR-U-region")

    public = message.Get("FILTER-ATTR-U-public")
    punkbuster = message.Get("FILTER-ATTR-U-Punkbuster")
    password = message.Get("FILTER-ATTR-U-HasPassword")
    softcore = message.Get("FILTER-ATTR-U-Softcore")
    ea = message.Get("FILTER-ATTR-U-EA")

    gid = message.Get("GID")

    if gid is None:
        gid = 0

    games = await Game.objects.get_games(lobby, gameType, gameMod, int(count), gid,
                                         favGame=favGame,
                                         notFull=notFull,
                                         minPlayers=minPlayers,
                                         gamemode=gamemode,
                                         level=level,
                                         region=region,
                                         public=public,
                                         punkbuster=punkbuster,
                                         password=password,
                                         softcore=softcore,
                                         ea=ea)

    lobby_game_count = await Game.objects.get_lobby_games_count(lobby)

    game_list = Packet()
    game_list.Set("LOBBY-NUM-GAMES", lobby_game_count)
    game_list.Set("NUM-GAMES", len(games))
    game_list.Set("LID", lobby.id)
    game_list.Set("LOBBY-MAX-GAMES", lobby.maxGames)

    yield game_list

    for game in games:
        game_data = Packet(service="GDAT")  # GDAT = Game Data

        for key in game:
            if game[key] == None:
                continue

            game_data.Set(key, game[key])

        yield game_data
