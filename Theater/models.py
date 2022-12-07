from django.db import models

from Plasma.enumerators.ClientLocale import ClientLocale
from Plasma.enumerators.ClientPlatform import ClientPlatform
from Plasma.models import Persona
from Theater.enumerators.GameType import GameType
from Theater.enumerators.JoinMode import JoinMode
from Theater.managers import GameManager, LobbyManager


# Create your models here.
class Lobby(models.Model):
    name = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Lobby Name",
        help_text="Name of the lobby",
    )
    locale = models.CharField(
        max_length=5,
        verbose_name="Locale",
        help_text="Locale of the lobby",
        choices=ClientLocale.choices,
    )
    maxGames = models.IntegerField(
        default=10000,
        verbose_name="Max Games",
        help_text="Maximum number of games in the lobby",
    )

    objects = LobbyManager()

    def __str__(self) -> str:
        return f"{self.name} ({self.locale})"

    class Meta:
        verbose_name = "Lobby"
        verbose_name_plural = "Lobbies"
        ordering = ("id",)


class Game(models.Model):
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE)
    owner = models.ForeignKey(Persona, on_delete=models.CASCADE)

    name = models.TextField(verbose_name="Server Name", help_text="Name of the server")

    addrIp = models.GenericIPAddressField(
        verbose_name="IP Address", help_text="IP Address of the server"
    )
    addrPort = models.IntegerField(verbose_name="Port", help_text="Port of the server")

    joiningPlayers = models.IntegerField(
        default=0,
        verbose_name="Joining Players",
        help_text="Number of players joining the server right now",
    )
    queuedPlayers = models.IntegerField(
        default=0,
        verbose_name="Queued Players",
        help_text="Number of players in the queue",
    )
    activePlayers = models.IntegerField(
        default=0,
        verbose_name="Active Players",
        help_text="Number of players currently in the server",
    )
    maxPlayers = models.IntegerField(
        verbose_name="Max Players", help_text="Maximum number of players in the server"
    )

    platform = models.CharField(
        max_length=5,
        verbose_name="Platform",
        help_text="Platform of the server",
        choices=ClientPlatform.choices,
    )

    joinMode = models.CharField(
        max_length=1,
        verbose_name="Join Mode",
        help_text="Theater join mode",
        choices=JoinMode.choices,
    )
    gameType = models.CharField(
        max_length=1,
        verbose_name="Game Type",
        help_text="Theater game type",
        choices=GameType.choices,
    )

    isPasswordRequired = models.BooleanField(
        default=False,
        verbose_name="Password Required",
        help_text="Is a password required to join the server?",
    )

    serverSoftcore = models.BooleanField(
        default=False,
        verbose_name="Server Softcore",
        help_text="Is the server softcore?",
    )
    serverHardcore = models.BooleanField(
        default=False,
        verbose_name="Server Hardcore",
        help_text="Is the server hardcore?",
    )
    serverHasPassword = models.BooleanField(
        default=False,
        verbose_name="Server Has Password",
        help_text="Does the server have a password?",
    )
    serverPunkbuster = models.BooleanField(
        default=False,
        verbose_name="Server Punkbuster",
        help_text="Is the server Punkbuster protected?",
    )
    serverEA = models.BooleanField(
        default=False,
        verbose_name="Server EA",
        help_text="Is the server official EA server?",
    )
    serverVersion = models.CharField(
        max_length=16, verbose_name="Server Version", help_text="Version of the server"
    )
    clientVersion = models.CharField(
        max_length=16,
        verbose_name="Client Version",
        help_text="Client version of the server",
    )

    gameLevel = models.TextField(
        null=True,
        verbose_name="Game Level",
        help_text="Current level of the server",
    )
    gameMod = models.TextField(
        null=True,
        verbose_name="Game Mod",
        help_text="Current mod of the server",
    )
    gameMode = models.TextField(
        null=True,
        verbose_name="Game Mode",
        help_text="Current game mode of the server",
    )
    gameSGUID = models.TextField(
        null=True,
        verbose_name="Game SGUID",
        help_text="Current SGUID of the server",
    )
    gameTime = models.TextField(
        null=True, verbose_name="Uptime", help_text="Uptime of the server"
    )
    gameHash = models.TextField(
        null=True,
        verbose_name="Game Hash",
        help_text="Current game hash of the server",
    )
    gameRegion = models.CharField(
        null=True,
        max_length=2,
        verbose_name="Game Region",
        help_text="Current game region of the server",
    )
    gamePublic = models.BooleanField(
        default=False, verbose_name="Game Public", help_text="Is the game public?"
    )
    gameElo = models.IntegerField(
        default=1000, verbose_name="Game Elo", help_text="Current Elo of the server"
    )

    gameAutoBalance = models.BooleanField(
        default=False,
        verbose_name="Game Auto Balance",
        help_text="Is the game auto balanced?",
    )

    gameBannerUrl = models.TextField(
        null=True,
        verbose_name="Game Banner URL",
        help_text="URL of the game banner",
    )

    gameCrosshair = models.BooleanField(
        default=False,
        verbose_name="Game Crosshair",
        help_text="Is the crosshair enabled?",
    )

    gameFriendlyFire = models.FloatField(
        default=0,
        verbose_name="Game Friendly Fire",
        help_text="Is the friendly fire enabled?",
    )

    gameKillCam = models.BooleanField(
        default=False,
        verbose_name="Game Kill Cam",
        help_text="Is the kill cam enabled?",
    )

    gameMinimap = models.BooleanField(
        default=False,
        verbose_name="Game Minimap",
        help_text="Is the minimap enabled?",
    )

    gameMinimapSpotting = models.BooleanField(
        default=False,
        verbose_name="Game Minimap Spotting",
        help_text="Is the minimap spotting enabled?",
    )

    gameThirdPersonVehicleCameras = models.BooleanField(
        default=False,
        verbose_name="Game Third Person Vehicle Cameras",
        help_text="Is the third person vehicle cameras enabled?",
    )

    gameThreeDSpotting = models.BooleanField(
        default=False,
        verbose_name="Game 3D Spotting",
        help_text="Is the 3D spotting enabled?",
    )

    gameDescription = models.TextField(
        null=True,
        verbose_name="Game Description",
        help_text="Description of the game",
    )

    pdat = models.TextField(verbose_name="Player Data")

    numObservers = models.IntegerField(
        verbose_name="Game Observers", help_text="Number of observers in the server"
    )
    maxObservers = models.IntegerField(
        verbose_name="Max Observers",
        help_text="Maximum number of observers in the server",
    )

    providerId = models.TextField(
        null=True,
        verbose_name="Provider ID",
        help_text="Provider ID of the server",
    )
    queueLength = models.IntegerField(
        verbose_name="Queue Length", help_text="Length of the queue"
    )

    punkBusterVersion = models.TextField(
        null=True,
        verbose_name="Punkbuster Version",
        help_text="Punkbuster version of the server",
    )

    ugid = models.CharField(
        max_length=16,
        verbose_name="UGID",
        help_text="UGID of the server",
    )

    ekey = models.CharField(
        max_length=32,
        verbose_name="EKEY",
        help_text="EKEY of the server",
    )

    secret = models.CharField(
        max_length=100,
        verbose_name="Secret",
        help_text="Secret of the server",
    )

    objects = GameManager()

    def __str__(self) -> str:
        return f"{self.name} ({self.addrIp}:{self.addrPort})"

    class Meta:
        verbose_name = "Game"
        verbose_name_plural = "Games"
        ordering = ("id",)
