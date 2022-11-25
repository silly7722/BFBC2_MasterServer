import threading

from BFBC2_MasterServer.consumer import BFBC2Consumer
from BFBC2_MasterServer.globals import (
    CLIENT_INITIAL_MEMCHECK_INTERVAL,
    CLIENT_MEMCHECK_INTERVAL,
    CLIENT_PING_INTERVAL,
    SERVER_INITIAL_MEMCHECK_INTERVAL,
    SERVER_MEMCHECK_INTERVAL,
    SERVER_PING_INTERVAL,
)
from django.core.cache import cache
from packaging import version

from Plasma.enumerators.ClientLocale import ClientLocale
from Plasma.enumerators.ClientPlatform import ClientPlatform
from Plasma.enumerators.ClientType import ClientType
from Plasma.services.connect import TXN as ConnectTXN
from Plasma.transactor import TransactionKind, TransactionService, Transactor


class PlasmaConsumer(BFBC2Consumer):

    clientString: str = None
    clientPlatform: ClientPlatform = None
    clientVersion = None
    clientType: ClientType = None
    sku: str = None
    locale: ClientLocale = None
    SDKVersion = None
    protocolVersion = None
    fragmentSize: int = None
    initialized = False

    transactor = None

    memcheckTimer = None
    pingTimer = None

    loggedUser, loggedUserKey = None, None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transactor = Transactor(self)

    async def disconnect(self, code):
        await super().disconnect(code)

        if self.pingTimer is not None:
            self.pingTimer.cancel()
            self.pingTimer = None

        if self.memcheckTimer is not None:
            self.memcheckTimer.cancel()
            self.memcheckTimer = None

        if self.loggedUser and self.loggedUserKey:
            # Remove consumer session from cache
            cache.delete(f"userSession:{self.loggedUser.id}")

            # Set user session to expire in 3 hours (approximitely that's how long the session is valid in original server)
            cache.touch(f"userLoginKey:{self.loggedUser.id}", 60 * 60 * 3)

    async def receive(self, text_data=None, bytes_data=None):
        message = await super().receive(text_data, bytes_data)

        if message is None:
            return

        await self.transactor.finish(message)

    async def send_packet(self, packet, tid):
        if packet.kind != TransactionKind.InitialError.value:
            packet.kind = packet.kind & 0xFF000000 | tid

        await super().send_packet(packet)

    async def initialize_connection(self, data: dict):
        self.clientString = data["clientString"]
        self.clientPlatform = ClientPlatform(data["clientPlatform"])
        self.clientVersion = version.parse(data["clientVersion"])
        self.clientType = ClientType(data["clientType"])
        self.sku = data["sku"]
        self.locale = ClientLocale(data["locale"])
        self.SDKVersion = version.parse(data["SDKVersion"])
        self.protocolVersion = version.parse(data["protocolVersion"])
        self.fragmentSize = data["fragmentSize"]
        self.initialized = True

        self.logger.info(
            f"Connection with {self.clientString} [{self.clientType}] (Platform: {self.clientPlatform}, Locale: {self.locale}, Version: {self.clientVersion}) initialized"
        )

        await self.send(
            text_data=f"Hello {self.clientString}! You are now connected to Plasma Master Server emulator (as {'client' if self.clientType == ClientType.CLIENT else 'server'}). Have fun!"
        )

        if self.clientVersion != version.parse("1.0"):
            self.logger.warning(
                f"Client version {self.clientVersion} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: Your client version ({self.clientVersion}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        if self.SDKVersion != version.parse("5.1.2.0.0"):
            self.logger.warning(
                f"SDK version {self.SDKVersion} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: SDK version ({self.clientVersion}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        if self.protocolVersion != version.parse("2.0"):
            self.logger.warning(
                f"Protocol version {self.protocolVersion} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: Protocol version ({self.clientVersion}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        await self.transactor.start(
            TransactionService.ConnectService, ConnectTXN.MemCheck, {}
        )

        if self.memcheckTimer is None and self.pingTimer is None:
            # Activate both ping and memcheck timers
            self.pingTimer = threading.Timer(
                CLIENT_PING_INTERVAL
                if self.clientType == ClientType.CLIENT
                else SERVER_PING_INTERVAL,
                self.__ping_client,
            )
            self.memcheckTimer = threading.Timer(
                CLIENT_INITIAL_MEMCHECK_INTERVAL
                if self.clientType == ClientType.CLIENT
                else SERVER_INITIAL_MEMCHECK_INTERVAL,
                self.__memcheck_client,
            )

            self.pingTimer.start()
            self.memcheckTimer.start()

    async def __memcheck_client(self):
        await self.transactor.start(
            TransactionService.ConnectService, ConnectTXN.MemCheck, {}
        )

        self.memcheckTimer = threading.Timer(
            CLIENT_MEMCHECK_INTERVAL
            if self.clientType == ClientType.CLIENT
            else SERVER_MEMCHECK_INTERVAL,
            self.__memcheck_client,
        )
        self.memcheckTimer.start()

    async def __ping_client(self):
        await self.transactor.start(
            TransactionService.ConnectService, ConnectTXN.Ping, {}
        )

        self.pingTimer = threading.Timer(
            CLIENT_PING_INTERVAL
            if self.clientType == ClientType.CLIENT
            else SERVER_PING_INTERVAL,
            self.__ping_client,
        )
        self.pingTimer.start()
