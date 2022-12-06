from enum import Enum

from channels.auth import database_sync_to_async

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.enumerators.AssocationUpdateOperation import AssocationUpdateOperation
from Plasma.enumerators.ListFullBehavior import ListFullBehavior
from Plasma.error import TransactionError
from Plasma.models import Assocation, AssociationType, Persona


class TXN(Enum):
    AddAssociations = "AddAssociations"
    DeleteAssociations = "DeleteAssociations"
    GetAssociations = "GetAssociations"
    GetAssociationCount = "GetAssociationCount"
    NotifyAssociationUpdate = "NotifyAssociationUpdate"


class AssociationService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.creator_map[
            TXN.NotifyAssociationUpdate
        ] = self.__create_notify_association_update

        self.resolver_map[TXN.AddAssociations] = self.__handle_add_associations
        self.resolver_map[TXN.DeleteAssociations] = self.__handle_delete_associations
        self.resolver_map[TXN.GetAssociations] = self.__handle_get_associations
        self.resolver_map[TXN.GetAssociationCount] = self.__handle_get_association_count

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    def __get_assocation_type(self, assoType):
        match assoType:
            case "PlasmaMute":
                return AssociationType.MUTE
            case "PlasmaBlock":
                return AssociationType.BLOCK
            case "PlasmaFriends":
                return AssociationType.FRIENDS
            case "PlasmaRecentPlayers":
                return AssociationType.RECENT_PLAYERS

        return None

    async def __handle_add_associations(self, data):
        """Add associations between two objects."""

        domainPartition = data.Get("domainPartition")
        listFullBehavior = data.Get("listFullBehavior")

        if not listFullBehavior:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        listFullBehavior = ListFullBehavior(listFullBehavior)

        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        addRequests = data.Get("addRequests")

        assoUsr = await Assocation.objects.get_user_assocations(
            self.connection.loggedPersona, assoType
        )
        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        result = []

        for addRequest in addRequests:
            outcome = 0

            assoLen = await Assocation.objects.get_user_assocations_count(
                self.connection.loggedPersona, assoType
            )

            if listFullBehavior == ListFullBehavior.ReturnError:
                if assoLen + 1 > maxAssocations:
                    outcome = 23005
            elif listFullBehavior == ListFullBehavior.RollLeastRecentlyModified:
                if assoLen + 1 > maxAssocations:
                    # Order by oldest first
                    members = sorted(members, key=lambda member: member.get("modified"))
                    oldestMember = members[0]

                    # Remove oldest member
                    database_sync_to_async(assoUsr.members.remove)(oldestMember)

            # Add new member
            member = await Assocation.objects.add_assocation(
                self.connection.loggedPersona, assoType, addRequest["member"]["id"]
            )

            assoLen = await Assocation.objects.get_user_assocations_count(
                self.connection.loggedPersona, assoType
            )

            uid = await Persona.objects.get_user_id_by_persona_id(member["id"])

            owner = {
                "id": self.connection.loggedPersona.id,
                "name": self.connection.loggedPersona.name,
                "type": 1,
            }

            await self.connection.start_remote_transaction(
                uid,
                "asso",
                TXN.NotifyAssociationUpdate.value,
                {
                    "domainPartition": domainPartition,
                    "listSize": assoLen,
                    "member": member,
                    "operation": AssocationUpdateOperation.ADD.value,
                    "owner": owner,
                    "type": data.Get("type"),
                },
            )

            if not member:
                outcome = 23005

            resultFinal = {
                "member": member,
                "owner": owner,
                "mutual": 0 if assoType == AssociationType.RECENT_PLAYERS else 1,
                "outcome": outcome,
                "listSize": assoLen,
            }

            result.append(resultFinal)

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("result", result)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_delete_associations(self, data):
        """Delete associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        await Assocation.objects.get_user_assocations(
            self.connection.loggedPersona, assoType
        )

        deleteRequests = data.Get("deleteRequests")
        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        result = []

        for deleteRequest in deleteRequests:
            outcome = 0

            # Remove member
            member = await Assocation.objects.remove_assocation(
                self.connection.loggedPersona, assoType, deleteRequest["member"]["id"]
            )

            owner = {
                "id": self.connection.loggedPersona.id,
                "name": self.connection.loggedPersona.name,
                "type": 1,
            }

            assoLen = await Assocation.objects.get_user_assocations_count(
                self.connection.loggedPersona, assoType
            )

            uid = await Persona.objects.get_user_id_by_persona_id(member["id"])

            await self.connection.start_remote_transaction(
                uid,
                "asso",
                TXN.NotifyAssociationUpdate.value,
                {
                    "domainPartition": domainPartition,
                    "listSize": assoLen,
                    "member": member,
                    "operation": AssocationUpdateOperation.DEL.value,
                    "owner": owner,
                    "type": data.Get("type"),
                },
            )

            if not member:
                outcome = 23005

            resultFinal = {
                "member": member,
                "owner": owner,
                "mutual": 0 if assoType == AssociationType.RECENT_PLAYERS else 1,
                "outcome": outcome,
                "listSize": assoLen,
            }

            result.append(resultFinal)

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("result", result)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_get_associations(self, data):
        """Get associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        assocationMembers = await Assocation.objects.get_user_assocations_dict(
            self.connection.loggedPersona, assoType
        )

        owner = {
            "id": self.connection.loggedPersona.id,
            "name": self.connection.loggedPersona.name,
            "type": 1,
        }

        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("members", assocationMembers)
        response.Set("owner", owner)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_get_association_count(self, data):
        """Get the number of associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        assocationMembers = await Assocation.objects.get_user_assocations_dict(
            self.connection.loggedPersona, assoType
        )

        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        owner = {
            "id": self.connection.loggedPersona.id,
            "name": self.connection.loggedPersona.name,
            "type": 1,
        }

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("count", len(assocationMembers))
        response.Set("owner", owner)

        return response

    async def __create_notify_association_update(self, data):
        """Create a notify association update packet."""

        response = Packet()

        for key in data:
            response.Set(key, data[key])

        return response
