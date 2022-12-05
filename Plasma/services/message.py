from datetime import datetime, timedelta
from enum import Enum

from channels.auth import database_sync_to_async, get_user, login
from django.utils import timezone

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.error import TransactionError
from Plasma.models import Attachment, Message, Persona


class TXN(Enum):
    SendMessage = "SendMessage"
    GetMessages = "GetMessages"
    GetMessageAttachments = "GetMessageAttachments"
    DeleteMessages = "DeleteMessages"
    PurgeMessages = "PurgeMessages"
    ModifySettings = "ModifySettings"
    AsyncMessageEvent = "AsyncMessageEvent"
    AsyncPurgedEvent = "AsyncPurgedEvent"


class ExtensibleMessageService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.creator_map[TXN.AsyncMessageEvent] = self.__create_async_message_event
        self.creator_map[TXN.AsyncPurgedEvent] = self.__create_async_purged_event

        self.resolver_map[TXN.SendMessage] = self.__handle_send_message
        self.resolver_map[TXN.GetMessages] = self.__handle_get_messages
        self.resolver_map[
            TXN.GetMessageAttachments
        ] = self.__handle_get_message_attachments
        self.resolver_map[TXN.DeleteMessages] = self.__handle_delete_messages
        self.resolver_map[TXN.PurgeMessages] = self.__handle_purge_messages
        self.resolver_map[TXN.ModifySettings] = self.__handle_modify_settings

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __handle_send_message(self, data):
        receivers, messageId = await Message.objects.send_message(
            self.connection.loggedPersona, data
        )

        statuses = []
        for receiver in receivers:
            statuses.append({"userid": receiver.id, "status": 0})

            uid = await Persona.objects.get_user_id_by_persona_id(receiver.id)

            await self.connection.start_remote_transaction(
                uid,
                "xmsg",
                TXN.AsyncMessageEvent.value,
                {
                    "messageId": messageId,
                },
            )

        response = Packet()
        response.Set("messageId", messageId)
        response.Set("status", statuses)

        return response

    async def __handle_get_messages(self, data):
        attachmentTypes = data.Get("attachmentTypes")
        messages = await Message.objects.get_messages(
            self.connection.loggedPersona, attachmentTypes
        )

        response = Packet()
        response.Set("messages", messages)

        return response

    async def __handle_get_message_attachments(self, data):
        # {
        #    "messageId": int,
        #    "keys.[]": int,
        #    "keys": [string array]
        # }

        return Packet()

    async def __handle_delete_messages(self, data):
        messageIds = data.Get("messageIds")

        for messageId in messageIds:
            message = await database_sync_to_async(Message.objects.get)(id=messageId)
            senderId = await Message.objects.get_sender_id_from_message(message)
            uid = await Persona.objects.get_user_id_by_persona_id(senderId)

            await self.connection.start_remote_transaction(
                uid,
                "xmsg",
                TXN.AsyncPurgedEvent.value,
                {
                    "messageIds": [messageId],
                },
            )

            await database_sync_to_async(message.delete)()

        return Packet()

    async def __handle_purge_messages(self, data):
        # Seems to be the same as DeleteMessages
        return await self.__handle_delete_messages(data)

    async def __handle_modify_settings(self, data):
        # Seems to be always called by client, not sure what it does because it doesn't seem to do anything

        # {
        #    "retrieveMessageTypes": [string array],
        #    "retrieveAttachmentTypes": [string array],
        #    "notifyMessages": int
        # }

        # Send acknowledge packet
        return Packet()

    async def __create_async_message_event(self, data):
        messageId = data.get("messageId")
        messageData = await Message.objects.get_message(messageId)

        response = Packet()

        for key in messageData:
            response.Set(key, messageData[key])

        return response

    async def __create_async_purged_event(self, data):
        messageIds = data.get("messageIds")

        response = Packet()
        response.Set("messageIds", messageIds)

        return response
