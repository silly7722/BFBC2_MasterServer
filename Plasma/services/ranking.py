from enum import Enum

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.models import Ranking


class TXN(Enum):
    UpdateStats = "UpdateStats"
    GetStats = "GetStats"
    GetStatsForOwners = "GetStatsForOwners"
    GetRankedStats = "GetRankedStats"
    GetRankedStatsForOwners = "GetRankedStatsForOwners"
    GetTopN = "GetTopN"
    GetTopNAndMe = "GetTopNAndMe"
    GetTopNAndStats = "GetTopNAndStats"
    GetDateRange = "GetDateRange"
    TransactionException = "TransactionException"


class RankingService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.resolver_map[TXN.UpdateStats] = self.__handle_update_stats
        self.resolver_map[TXN.GetStats] = self.__handle_get_stats
        self.resolver_map[TXN.GetStatsForOwners] = self.__handle_get_stats_for_owners
        self.resolver_map[TXN.GetRankedStats] = self.__handle_get_ranked_stats
        self.resolver_map[
            TXN.GetRankedStatsForOwners
        ] = self.__handle_get_stats_for_owners
        self.resolver_map[TXN.GetTopN] = self.__handle_get_top_n
        self.resolver_map[TXN.GetTopNAndMe] = self.__handle_get_top_n_and_me
        self.resolver_map[TXN.GetTopNAndStats] = self.__handle_get_top_n_and_stats
        self.resolver_map[TXN.GetDateRange] = self.__handle_get_date_range

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __handle_update_stats(self, data):
        # TODO: Implement it
        raise NotImplementedError("UpdateStats not implemented (yet)")

    async def __handle_get_stats(self, data):
        """Get stats for a current persona"""
        keys = data.Get("keys")

        stats = []

        for key in keys:
            value = await Ranking.objects.get_stat(self.connection.loggedPersona, key)
            stat = {"key": key, "value": value}
            stats.append(stat)

        response = Packet()
        response.Set("stats", stats)

        return response

    async def __handle_get_stats_for_owners(self, data):
        """Get stats for a list of personas"""
        owners = data.Get("owners")
        keys = data.Get("keys")

        stats = []

        for owner in owners:
            ownerId = owner["ownerId"]
            ownerStats = []

            for key in keys:
                value = await Ranking.objects.get_stat_by_id(ownerId, key)
                stat = {"key": key, "value": value}
                ownerStats.append(stat)

            stats.append(
                {
                    "stats": ownerStats,
                    "ownerId": ownerId,
                    "ownerType": owner["ownerType"],
                }
            )

        response = Packet()
        response.Set("stats", stats)

        return response

    async def __handle_get_ranked_stats(self, data):
        """Get ranked stats for a current persona"""

        keys = data.Get("keys")

        stats = []

        for key in keys:
            value, rank = await Ranking.objects.get_ranked_stat(
                self.connection.loggedPersona, key
            )

            stat = {"key": key, "rank": rank, "value": value}
            stats.append(stat)

        response = Packet()
        response.Set("stats", stats)

        return response

    async def __handle_get_stats_for_owners(self, data):
        """Get ranked stats for a list of personas"""

        owners = data.Get("owners")
        keys = data.Get("keys")

        stats = []

        for owner in owners:
            ownerId = owner["ownerId"]
            ownerStats = []

            for key in keys:
                value, rank = await Ranking.objects.get_ranked_stat_by_id(ownerId, key)

                stat = {"key": key, "rank": rank, "value": value}
                ownerStats.append(stat)

            stats.append(
                {
                    "rankedStats": ownerStats,
                    "ownerId": ownerId,
                    "ownerType": owner["ownerType"],
                }
            )

        response = Packet()
        response.Set("rankedStats", stats)
        return response

    async def __handle_get_top_n(self, data):
        """Leaderboards (without current player?)"""

        key = data.Get("key")
        minRank = data.Get("minRank")
        maxRank = data.Get("maxRank")

        leaderboardUsers = await Ranking.objects.get_leaderboard_users(
            key, minRank, maxRank, self.connection.loggedPersona
        )

        response = Packet()
        response.Set("stats", leaderboardUsers)

        return response

    async def __handle_get_top_n_and_me(self, data):
        """Leaderboards (with current player?)"""

        key = data.Get("key")
        minRank = data.Get("minRank")
        maxRank = data.Get("maxRank")

        leaderboardUsers = await Ranking.objects.get_leaderboard_users(
            key, minRank, maxRank
        )

        response = Packet()
        response.Set("stats", leaderboardUsers)

        return response

    async def __handle_get_top_n_and_stats(self, data):
        """Leaderboards and stats"""

        key = data.Get("key")
        keys = data.Get("keys")
        minRank = data.Get("minRank")
        maxRank = data.Get("maxRank")

        leaderboardUsers = await Ranking.objects.get_leaderboard_users(
            key, minRank, maxRank
        )

        for i, user in enumerate(leaderboardUsers):
            leaderboardUsers[i]["addStats"] = []

            for key in keys:
                value = await Ranking.objects.get_stat_by_id(user["owner"], key)
                leaderboardUsers[i]["addStats"] = {"key": key, "value": value}

        response = Packet()
        response.Set("stats", leaderboardUsers)

        return response

    async def __handle_get_date_range(self, data):
        # Not sure what this does, is it even called by game?

        # Input:
        # {
        #    "key": string,
        #    "periodId": int
        # }
        #
        # Output:
        # {
        #    "startDate": datetime,
        #    "endDate": datetime
        # }
        raise NotImplementedError("GetDateRange not implemented")
