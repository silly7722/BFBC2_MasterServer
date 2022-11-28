from BFBC2_MasterServer.consumer import BFBC2Consumer
from packaging import version

from Theater.transactor import Transactor


class TheaterConsumer(BFBC2Consumer):

    prot = None  # Protocol Version
    prod = None  # Game ID
    vers = None  # Game Version
    plat = None  # Platform
    locale = None  # Locale
    sdkVersion = None  # SDK Version

    initialized = False
    transactor = None

    persona = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transactor = Transactor(self)

    async def receive(self, text_data=None, bytes_data=None):
        message = await super().receive(text_data, bytes_data)

        if message is None:
            return

        await self.transactor.finish(message)

    async def initialize(self, data):
        """Initialize connection"""

        self.prot = data["protocolVersion"]
        self.prod = data["product"]
        self.vers = version.parse(data["version"])
        self.plat = data["platform"]
        self.locale = data["locale"]
        self.sdkVersion = version.parse(data["sdkVersion"])

        if self.prot != 2:
            self.logger.warning(
                f"Protocol version {self.prot} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: Your protocol version ({self.prot}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        if self.vers != version.parse("1.0") or self.vers != version.parse("2.0"):
            # 1.0 - Client, 2.0 - Server
            self.logger.warning(
                f"Game version {self.vers} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: Your game version ({self.vers}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        if self.sdkVersion != version.parse("5.1.2.0.0"):
            self.logger.warning(
                f"SDK version {self.sdkVersion} is not officially supported by this server emulator!"
            )

            await self.send(
                text_data=f"WARNING: SDK version ({self.sdkVersion}) is not officially supported by this server emulator, some features may not work properly. Please install latest supported game version by this server emulator (Which is 795745)"
            )

        self.initialized = True
