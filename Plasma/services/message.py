from datetime import datetime, timedelta
from enum import Enum

from channels.auth import database_sync_to_async, get_user, login

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

        self.resolver_map[TXN.SendMessage] = self.__handle_send_message
        self.resolver_map[TXN.GetMessages] = self.__handle_get_messages
        self.resolver_map[
            TXN.GetMessageAttachments
        ] = self.__handle_get_message_attachments
        self.resolver_map[TXN.DeleteMessages] = self.__handle_delete_messages

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

        response = Packet()
        response.Set("messageId", messageId)
        response.Set("status", statuses)

        # TODO: Send AsyncMessageEvent to receivers

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
            await database_sync_to_async(message.delete)()

        return Packet()
