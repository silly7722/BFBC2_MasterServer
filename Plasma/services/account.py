from enum import Enum

from BFBC2_MasterServer.service import Service


class TXN(Enum):
    NuLogin = "NuLogin"
    NuAddAccount = "NuAddAccount"
    NuAddPersona = "NuAddPersona"
    NuDisablePersona = "NuDisablePersona"
    GetCountryList = "GetCountryList"
    NuGetTos = "NuGetTos"
    NuCreateEncryptedToken = "NuCreateEncryptedToken"
    NuSuggestPersonas = "NuSuggestPersonas"
    NuLoginPersona = "NuLoginPersona"
    NuUpdatePassword = "NuUpdatePassword"
    NuGetAccount = "NuGetAccount"
    NuGetAccountByNuid = "NuGetAccountByNuid"
    NuGetAccountByPS3Ticket = "NuGetAccountByPS3Ticket"
    NuGetPersonas = "NuGetPersonas"
    NuUpdateAccount = "NuUpdateAccount"
    GameSpyPreAuth = "GameSpyPreAuth"
    NuXBL360Login = "NuXBL360Login"
    NuXBL360AddAccount = "NuXBL360AddAccount"
    NuPS3Login = "NuPS3Login"
    NuPS3AddAccount = "NuPS3AddAccount"
    TransactionException = "TransactionException"
    NuLookupUserInfo = "NuLookupUserInfo"
    NuSearchOwners = "NuSearchOwners"
    GetTelemetryToken = "GetTelemetryToken"
    NuGetEntitlements = "NuGetEntitlements"
    NuGetEntitlementCount = "NuGetEntitlementCount"
    NuEntitleGame = "NuEntitleGame"
    NuEntitleUser = "NuEntitleUser"
    NuGrantEntitlement = "NuGrantEntitlement"
    GetLockerURL = "GetLockerURL"


class AccountService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]
