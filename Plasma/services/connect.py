import random
import string
from datetime import datetime
from enum import Enum

from BFBC2_MasterServer.globals import (
    MESSENGER_IP,
    MESSENGER_PORT,
    THEATER_CLIENT_IP,
    THEATER_CLIENT_PORT,
    THEATER_SERVER_IP,
    THEATER_SERVER_PORT,
)
from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.enumerators.ClientType import ClientType
from Plasma.error import TransactionSkip


class TXN(Enum):
    Hello = "Hello"
    Ping = "Ping"
    Goodbye = "Goodbye"
    Suicide = "Suicide"
    MemCheck = "MemCheck"
    GetPingSites = "GetPingSites"


class ConnectService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.creator_map[TXN.Ping] = self.__create_ping
        self.creator_map[TXN.MemCheck] = self.__create_memcheck

        self.resolver_map[TXN.Hello] = self.__handle_hello
        self.resolver_map[TXN.Ping] = self.__handle_ping
        self.resolver_map[TXN.Goodbye] = self.__handle_goodbye
        self.resolver_map[TXN.Suicide] = self.__handle_suicide
        self.resolver_map[TXN.MemCheck] = self.__handle_memcheck
        self.resolver_map[TXN.GetPingSites] = self.__get_ping_sites

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __create_ping(self, data):
        """Create a Ping packet"""

        response = Packet()
        return response

    async def __create_memcheck(self, data):
        """Create a MemCheck packet"""

        response = Packet()

        # Never saw memcheck containing something (original server also always sends empty memcheck)
        # But memcheck object should look like this
        # {
        #    "addr": integer (4 bytes),
        #    "len": integer (4 bytes),
        # }
        # Never seen that in the wild, and above is just a guess based on my client reverse engineering
        # No idea how this affects the client, but original server never sends it either so we send empty array here
        response.Set("memcheck", [])
        response.Set("type", 0)
        response.Set("salt", "".join(random.choice(string.digits) for _ in range(10)))

        return response

    async def __handle_hello(self, data):
        """Initial packet sent by client, used to determine client type, and other connection details"""

        client_data = {
            "clientString": data.Get("clientString"),
            "clientPlatform": data.Get("clientPlatform"),
            "clientVersion": data.Get("clientVersion"),
            "clientType": data.Get("clientType"),
            "sku": data.Get("sku"),
            "locale": data.Get("locale"),
            "SDKVersion": data.Get("SDKVersion"),
            "protocolVersion": data.Get("protocolVersion"),
            "fragmentSize": data.Get("fragmentSize"),
        }

        await self.connection.initialize_connection(client_data)

        domainPartition = {
            "domain": "eagames",
            "subDomain": "BFBC2",
        }

        theater_ip, theater_port = (None, None)

        if self.connection.clientType == ClientType.CLIENT:
            theater_ip = THEATER_CLIENT_IP
            theater_port = THEATER_CLIENT_PORT
        else:
            theater_ip = THEATER_SERVER_IP
            theater_port = THEATER_SERVER_PORT

        response = Packet()
        response.Set(
            "activityTimeoutSecs", 0
        )  # Client sets this to 200 (3.33 minutes) if set to 0
        response.Set("curTime", datetime.now())
        response.Set(
            "domainPartition", domainPartition
        )  # Game doesn't seem to care about this, but it's sent by the original server
        response.Set("messengerIp", MESSENGER_IP)
        response.Set("messengerPort", MESSENGER_PORT)
        response.Set("theaterIp", theater_ip)
        response.Set("theaterPort", theater_port)

        # Client also supports "addressRemapping" value here, but it's never sent by the original server
        # response.Set("addressRemapping", '\0')
        # If not set, client will set this value to NULL internally (just like above)
        # No clue what this value is used for

        return response

    async def __handle_ping(self, data):
        """Handle a Ping packet"""

        # Ignore
        return TransactionSkip()

    async def __handle_goodbye(self, data):
        """Handle a Goodbye packet (sent by client when disconnecting)"""

        # Just log why client disconnected
        self.connection.logger.info(
            f"Client disconnected (Reason: {data.Get('reason')}, Message: {data.Get('message')})"
        )
        return TransactionSkip()

    async def __handle_suicide(self, data):
        """Handle Suicide packet"""

        # This packet only contains TXN, no idea what it's supposed to do
        # It seems that it's client who would send this kind of transaction
        # But I never managed to make game send this packet
        # So ignore this packet

        return TransactionSkip()

    async def __handle_memcheck(self, data):
        """Handle a MemCheck packet"""

        # Ignore
        return TransactionSkip()

    async def __get_ping_sites(self, data):
        """Get a list of ping sites"""

        # Original server always sends 4 ping sites
        # {
        #    "name": "nrt",
        #    "type": 0,
        #    "addr": "109.200.220.1"
        # }
        # {
        #    "name": "gva",
        #    "type": 0,
        #    "addr": "159.153.72.181"
        # }
        # {
        #    "name": "sjc",
        #    "type": 0,
        #    "addr": "159.153.70.181"
        # }
        # {
        #    "name": "iad",
        #    "type": 0,
        #    "addr": "159.153.93.213"
        # }

        # Because we're only emulating the master server, send the same ping sites, but with localhost address instead (not sure how this affects the client)
        ping_sites = [
            {"name": name, "type": 0, "addr": "127.0.0.1"}
            for name in ["nrt", "gva", "sjc", "iad"]
        ]

        response = Packet()
        response.Set("pingSite", ping_sites)
        response.Set("minPingSitesToPing", 0)

        return response
