from enum import Enum

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service


class TXN(Enum):
    AddRecord = "AddRecord"
    GetRecord = "GetRecord"
    UpdateRecord = "UpdateRecord"
    AddRecordAsMap = "AddRecordAsMap"
    GetRecordAsMap = "GetRecordAsMap"
    UpdateRecordAsMap = "UpdateRecordAsMap"
    TransactionException = "TransactionException"


class RecordService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]
