import os
from base64 import b64encode

from asgiref.sync import sync_to_async
from django.db import models


class LobbyManager(models.Manager):
    @sync_to_async
    def get_lobby(self, lid, locale=None, platform=None):
        if lid == -1:
            lobbyNameBase = f"bfbc2{platform.value}"
            lobbyName = lobbyNameBase
            platformLobbies = self.filter(name__startswith=lobbyName).count()

            if platformLobbies == 0:
                platformLobbies = 1

            lobbyName += "{:02d}".format(platformLobbies)

            from Theater.models import Game

            if Game.objects.filter(lobby__name=lobbyName).count() >= 10000:
                lobbyName = lobbyNameBase + "{:02d}".format(platformLobbies + 1)

            return self.get_or_create(name=lobbyName, locale=locale)[0]
        else:
            return self.get(id=lid)


class GameManager(models.Manager):
    @sync_to_async
    def create_game(self, lobby, owner, address, clientVersion, clientPlatform, data):
        secret = data.Get("SECRET")

        game = self.create(
            lobby=lobby,
            owner=owner,
            name=data.Get("NAME").lstrip('"').rstrip('"'),
            addrIp=address[0],
            addrPort=address[1],
            platform=clientPlatform,
            gameType=data.Get("TYPE"),
            queueLength=data.Get("QLEN"),
            maxPlayers=data.Get("MAX-PLAYERS"),
            maxObservers=data.Get("B-maxObservers"),
            numObservers=data.Get("B-numObservers"),
            serverHardcore=data.Get("B-U-Hardcore"),
            serverHasPassword=data.Get("B-U-HasPassword"),
            serverPunkbuster=data.Get("B-U-Punkbuster"),
            clientVersion=clientVersion,
            serverVersion=data.Get("B-version"),
            joinMode=data.Get("JOIN"),
            ugid=data.Get("UGID"),
            ekey=b64encode(os.urandom(16)).decode(),
            secret=secret if len(secret) != 0 else b64encode(os.urandom(64)).decode(),
        )

        return game, {
            "LID": game.lobby.id,
            "GID": game.id,
            "MAX-PLAYERS": game.maxPlayers,
            "EKEY": game.ekey,
            "UGID": game.ugid,
            "JOIN": game.joinMode,
            "SECRET": game.secret,
            "J": game.joinMode,
        }

    @sync_to_async
    def delete_game(self, game):
        gameLobby = game.lobby
        game.delete()

        if self.filter(lobby=gameLobby).count() == 0:
            gameLobby.delete()

    @sync_to_async
    def update_game(self, game, key, value):
        if isinstance(value, str):
            value = value.lstrip('"').rstrip('"')

        match key:
            case "NAME":
                game.name = value
            case "MAX-PLAYERS":
                game.maxPlayers = value
            case "JOIN":
                game.joinMode = value
            case "TYPE":
                game.gameType = value
            case "UGID":
                game.ugid = value
            case "JP":
                game.joiningPlayers = value
            case "QP":
                game.queuedPlayers = value
            case "AP":
                game.activePlayers = value
            case "PL":
                game.platform = value
            case "PW":
                game.isPasswordRequired = value
            case "B-U-level":
                game.gameLevel = value
            case "B-U-QueueLength":
                game.queueLength = value
            case "B-U-Softcore":
                game.serverSoftcore = value
            case "B-U-Hardcore":
                game.serverHardcore = value
            case "B-U-HasPassword":
                game.serverHasPassword = value
            case "B-U-Punkbuster":
                game.serverPunkbuster = value
            case "B-U-PunkbusterVersion":
                game.punkBusterVersion = value
            case "B-U-EA":
                game.serverEA = value
            case "B-U-gameMod":
                game.gameMod = value
            case "B-U-gamemode":
                game.gameMode = value
            case "B-U-Time":
                game.gameTime = value
            case "B-U-region":
                game.gameRegion = value
            case "B-version":
                game.serverVersion = value
            case "B-U-public":
                game.gamePublic = value
            case "B-U-elo":
                game.gameElo = value
            case "B-numObservers":
                game.numObservers = value
            case "B-maxObservers":
                game.maxObservers = value
            case "B-U-sguid":
                game.gameSGUID = value
            case "B-U-hash":
                game.gameHash = value
            case "B-U-Provider":
                game.providerId = value
            case "D-AutoBalance":
                game.gameAutoBalance = value
            case "D-BannerUrl":
                game.gameBannerUrl = value
            case "D-Crosshair":
                game.gameCrosshair = value
            case "D-FriendlyFire":
                game.gameFriendlyFire = value
            case "D-KillCam":
                game.gameKillCam = value
            case "D-Minimap":
                game.gameMinimap = value
            case "D-MinimapSpotting":
                game.gameMinimapSpotting = value
            case "D-ServerDescription0":
                game.gameDescription = value
            case "D-ThirdPersonVehicleCameras":
                game.gameThirdPersonVehicleCameras = value
            case "D-ThreeDSpotting":
                game.gameThreeDSpotting = value
            case "D-pdat":
                game.pdat = value

        game.save()
