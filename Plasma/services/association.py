from enum import Enum

from asgiref.sync import sync_to_async
from channels.auth import database_sync_to_async, get_user

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.enumerators.ListFullBehavior import ListFullBehavior
from Plasma.error import TransactionError
from Plasma.models import Assocation, AssociationType


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
        self.resolver_map[
            TXN.NotifyAssociationUpdate
        ] = self.__handle_notify_association_update

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

            if listFullBehavior == ListFullBehavior.ReturnError:
                if len(assoUsr.members) + 1 > maxAssocations:
                    outcome = 23005
            elif listFullBehavior == ListFullBehavior.RollLeastRecentlyModified:
                if len(assoUsr.members) + 1 > maxAssocations:
                    # Roll least recently modified
                    members = await database_sync_to_async(assoUsr.members.all)()

                    # Order by oldest first
                    members = sorted(members, key=lambda member: member.lastModified)
                    oldestMember = members[0]

                    # Remove oldest member
                    await database_sync_to_async(assoUsr.members.remove)(oldestMember)

            # Add new member
            member = await Assocation.objects.add_assocation(
                assoUsr, addRequest["member"]["id"]
            )

            assocations = await Assocation.objects.get_user_assocations(
                self.connection.loggedPersona, assoType
            )

            if not member:
                outcome = 23005

            owner = {
                "id": self.connection.loggedPersona.id,
                "name": self.connection.loggedPersona.name,
                "type": 1,
            }

            resultFinal = {
                "member": member,
                "owner": owner,
                "mutual": 0 if assoType == AssociationType.RECENT_PLAYERS else 1,
                "outcome": outcome,
                "listSize": len(assocations.members),
            }

            result.append(resultFinal)

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("results", result)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_delete_associations(self, data):
        """Delete associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        assoUsr = await Assocation.objects.get_user_assocations(
            self.connection.loggedPersona, assoType
        )

        deleteRequests = data.Get("deleteRequests")
        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        result = []

        for deleteRequest in deleteRequests:
            outcome = 0

            # Remove member
            member = await Assocation.objects.remove_assocation(
                assoUsr, deleteRequest["member"]["id"]
            )

            assocations = await Assocation.objects.get_user_assocations(
                self.connection.loggedPersona, assoType
            )

            if not member:
                outcome = 23005

            owner = {
                "id": self.connection.loggedPersona.id,
                "name": self.connection.loggedPersona.name,
                "type": 1,
            }

            resultFinal = {
                "member": member,
                "owner": owner,
                "mutual": 0 if assoType == AssociationType.RECENT_PLAYERS else 1,
                "outcome": outcome,
                "listSize": len(assocations.members),
            }

            result.append(resultFinal)

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("results", result)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_get_associations(self, data):
        """Get associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        assocationMembers = await Assocation.objects.get_user_assocations(
            self.connection.loggedPersona, assoType
        )

        maxAssocations = 20 if assoType != AssociationType.RECENT_PLAYERS else 100

        result = []

        for member in assocationMembers:
            owner = {
                "id": self.connection.loggedPersona.id,
                "name": self.connection.loggedPersona.name,
                "type": 1,
            }

            resultFinal = {
                "member": member,
                "owner": owner,
                "mutual": 0 if assoType == AssociationType.RECENT_PLAYERS else 1,
                "outcome": 0,
                "listSize": len(assocationMembers),
            }

            result.append(resultFinal)

        response = Packet()
        response.Set("domainPartition", domainPartition)
        response.Set("maxListSize", maxAssocations)
        response.Set("results", result)
        response.Set("type", data.Get("type"))

        return response

    async def __handle_get_association_count(self, data):
        """Get the number of associations between two objects."""

        domainPartition = data.Get("domainPartition")
        assoType = self.__get_assocation_type(data.Get("type"))

        if not assoType:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        assocationMembers = await Assocation.objects.get_user_assocations(
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

    async def __handle_notify_association_update(self, data):
        """Notify the client that an association has been updated."""

        # Is this even called by the game?

        return NotImplementedError(
            "NotifyAssociationUpdate packet handler is not implemented."
        )

    async def __create_notify_association_update(self, data):
        """Create a notify association update packet."""

        # Is this even used?

        # {
        #     "type": string,
        #     "domainPartition": {
        #        "domain": string,
        #        "subDomain": string
        #        "Key": string
        #    },
        #    "entity": {
        #       "id": int,
        #       "type": int,
        #       "name": string,
        #     },
        #     "member": {
        #        "created": datetime,
        #        "modified": datetime,
        #     },
        #     "listSize": int,
        #     "mutual": int,
        #     "operation": "add" or "del"
        # }

        raise NotImplementedError(
            "NotifyAssociationUpdate packet creation is not implemented."
        )
