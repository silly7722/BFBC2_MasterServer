from Theater.models import Game


async def update_game_details(connection, message):
    pdatStr = ""
    for pdatID in range(32):
        pdat = message.Get("PDAT" + "{:02d}".format(pdatID))

        if pdat is None:
            pdatStr = None
            break
        else:
            pdatStr += pdat

    if pdatStr is not None:
        message.Set("D-pdat", pdatStr)

    keys = message.GetKeys()

    for key in keys:
        await Game.objects.update_game(connection.game, key, message.Get(key))

    yield
    return
