from Theater.models import Game, GameDescription, PlayerData


async def update_game_details(connection, message):
    maxPlayers = connection.game.maxPlayers

    for i in range(maxPlayers):
        if maxPlayers < 10:
            pdat = message.Get(f"D-pdat{i}")
        else:
            pdat = message.Get(f"D-pdat{i:02}")

        if pdat is None:
            continue

        await PlayerData.objects.update_player_data(connection.game, i, pdat)

    serverDescriptionCount = message.Get("D-ServerDescriptionCount")
    GameDescription.objects.set_game_description_count(
        connection.game, serverDescriptionCount
    )

    if serverDescriptionCount:
        for i in range(serverDescriptionCount):
            if serverDescriptionCount < 10:
                desc = message.Get(f"D-ServerDescription{i}")
            else:
                desc = message.Get(f"D-ServerDescription{i:02}")

            if desc is None:
                continue

            await GameDescription.objects.set_game_description(connection.game, i, desc)

    keys = message.GetKeys()

    for key in keys:
        await Game.objects.update_game(connection.game, key, message.Get(key))

    yield
