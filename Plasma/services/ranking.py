from enum import Enum

from BFBC2_MasterServer.service import Service


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

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]
