from enum import Enum

from BFBC2_MasterServer.service import Service


class TXN(Enum):
    AddAssociations = "AddAssociations"
    DeleteAssociations = "DeleteAssociations"
    GetAssociations = "GetAssociations"
    GetAssociationCount = "GetAssociationCount"
    NotifyAssociationUpdate = "NotifyAssociationUpdate"


class AssociationService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]
