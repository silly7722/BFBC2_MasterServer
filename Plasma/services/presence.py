import asyncio
import json
from base64 import b64decode, b64encode
from enum import Enum

from django.core.cache import cache

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.error import TransactionError
from Plasma.models import Persona


class TXN(Enum):
    PresenceSubscribe = "PresenceSubscribe"
    PresenceUnsubscribe = "PresenceUnsubscribe"
    SetPresenceStatus = "SetPresenceStatus"
    AsyncPresenceStatusEvent = "AsyncPresenceStatusEvent"


class PresenceService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.creator_map[
            TXN.AsyncPresenceStatusEvent
        ] = self.__create_async_presence_status_event

        self.resolver_map[TXN.PresenceSubscribe] = self.__handle_presence_subscribe
        self.resolver_map[TXN.PresenceUnsubscribe] = self.__handle_presence_unsubscribe
        self.resolver_map[TXN.SetPresenceStatus] = self.__handle_set_presence_status

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __handle_presence_subscribe(self, data):
        requests = data.Get("requests")

        responses = []

        for request in requests:
            userId = request["userId"]

            # Add the user to the list of subscribed users (if not already subscribed)
            if userId not in self.connection.subscribedTo:
                self.connection.subscribedTo.append(userId)

            owner = await Persona.objects.get_persona_by_id(userId)

            responses.append({"owner": owner, "outcome": 0})

            currPres = cache.get(f"presence:{userId}")

            if currPres:
                asyncio.ensure_future(
                    self.connection.transactor.start(
                        "pres",
                        TXN.AsyncPresenceStatusEvent,
                        {"initial": True, "owner": owner, "status": currPres},
                    )
                )

        response = Packet()
        response.Set("responses", responses)

        return response

    async def __handle_presence_unsubscribe(self, data):
        requests = data.Get("requests")

        responses = []

        for request in requests:
            userId = request["userId"]

            # Remove the user from the list of subscribed users (if subscribed)
            if userId in self.connection.subscribedTo:
                self.connection.subscribedTo.remove(userId)

            owner = await Persona.objects.get_persona_by_id(userId)

            responses.append({"owner": owner, "outcome": 0})

        response = Packet()
        response.Set("responses", responses)

        return response

    async def __handle_set_presence_status(self, data):
        status = data.Get("status")

        # Encode the status as a JSON string, base64 encoded, and store it in the cache
        statusJSON = json.dumps(status)
        statusEncoded = b64encode(statusJSON.encode("utf-8"))

        cache.set(f"presence:{self.connection.loggedPersona.id}", statusEncoded)

        owner = await Persona.objects.get_persona_by_id(
            self.connection.loggedPersona.id
        )

        for userId in self.connection.subscribedTo:
            # I'm assuming here that if client A is subscribed to client B, client B is also subscribed to client A
            # (Because the clients should be friends with each other)
            await self.connection.start_remote_transaction(
                userId,
                "pres",
                TXN.AsyncPresenceStatusEvent.value,
                {"owner": owner, "status": statusEncoded},
            )

        return Packet()

    async def __create_async_presence_status_event(self, data):
        isInitial = data.get("initial", False)
        owner = data.get("owner")

        if not owner:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        response = Packet()
        response.Set("initial", int(isInitial))
        response.Set("owner", owner)

        if (
                owner["id"] == self.connection.loggedPersona.id
                or owner["id"] in self.connection.subscribedTo
        ):
            status = data.get("status")

            if status:
                statusDecoded = b64decode(status)
                statusJSON = json.loads(statusDecoded)

                response.Set("status", statusJSON)

        return response
