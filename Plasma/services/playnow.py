import asyncio
from enum import Enum

from django.core.cache import cache

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.error import TransactionError


class TXN(Enum):
    Start = "Start"
    Status = "Status"


class PlayNowService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.resolver_map[TXN.Start] = self.__handle_start
        self.creator_map[TXN.Status] = self.__create_status

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __handle_start(self, data):
        cache.get_or_set("matchmakingId", 0, timeout=None)
        self.connection.matchmakingId = cache.incr("matchmakingId")

        response = Packet()

        response.Set("id", {
            "id": self.connection.matchmakingId,
            "partition": "/eagames/BFBC2",
        })

        players = data.Get("players")
        matchmaking_settings = players[0]

        asyncio.get_running_loop().create_task(self.connection.start_matchmaking(matchmaking_settings["props"]))
        return response

    async def __create_status(self, data):
        if not self.connection.matchmakingId:
            raise TransactionError(TransactionError.Code.SYSTEM_ERROR)

        await asyncio.sleep(1)

        response = Packet()

        response.Set("id", {
            "id": self.connection.matchmakingId,
            "partition": "/eagames/BFBC2",
        })

        self.connection.matchmakingId = None

        response.Set("sessionState", "COMPLETE")

        games = []

        gid = data.get("gid")
        lid = data.get("lid")

        if gid and lid:
            games.append({"fit": 1001, "gid": gid, "lid": lid})

        response.Set("props", {
            "{resultType}": "JOIN",
            "{games}": games,
        })

        return response
