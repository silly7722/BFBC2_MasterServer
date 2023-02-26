import gc
from base64 import b64decode, b64encode
from enum import Enum

from BFBC2_MasterServer.packet import HEADER_LENGTH, Packet
from Plasma.error import TransactionError, TransactionException, TransactionSkip
from Plasma.services.account import AccountService
from Plasma.services.account import TXN as AccountTXN
from Plasma.services.association import AssociationService
from Plasma.services.association import TXN as AssocationTXN
from Plasma.services.connect import ConnectService
from Plasma.services.connect import TXN as ConnectTXN
from Plasma.services.message import ExtensibleMessageService
from Plasma.services.message import TXN as MessageTXN
from Plasma.services.playnow import PlayNowService
from Plasma.services.playnow import TXN as PlayNowTXN
from Plasma.services.presence import PresenceService
from Plasma.services.presence import TXN as PresenceTXN
from Plasma.services.ranking import RankingService
from Plasma.services.record import RecordService


class TransactionService(Enum):
    ConnectService = "fsys"
    AccountService = "acct"
    AssociationService = "asso"
    ExtensibleMessageService = "xmsg"
    PlayNowService = "pnow"
    PresenceService = "pres"
    RankingService = "rank"
    RecordService = "recp"


class TransactionKind(Enum):
    InitialError = 0x66657272
    Simple = 0xC0000000
    SimpleResponse = 0x80000000
    Chunked = 0xF0000000
    ChunkedResponse = 0xB0000000


class Transactor:
    incoming_queue = []
    tid = 0  # Transaction ID

    services = {}
    allowed_unscheduled_transactions = [
        ConnectTXN.MemCheck.value,
        ConnectTXN.Ping.value,
        ConnectTXN.Goodbye.value,
        AssocationTXN.NotifyAssociationUpdate.value,
        MessageTXN.AsyncMessageEvent.value,
        MessageTXN.AsyncPurgedEvent.value,
        PresenceTXN.AsyncPresenceStatusEvent.value,
        PlayNowTXN.Status.value,
    ]
    allowed_transactions_without_auth = [
        # All transactions from ConnectService are allowed without auth (not included in this list)
        # Only some transactions from AccountService are allowed without auth (included in this list)
        AccountTXN.NuLogin.value,
        AccountTXN.NuAddAccount.value,
        AccountTXN.GetCountryList.value,
        AccountTXN.NuGetTos.value,
        AccountTXN.NuEntitleGame.value,
    ]

    def __init__(self, connection):
        self.connection = connection

        # Init services
        self.services[TransactionService.ConnectService] = ConnectService(connection)
        self.services[TransactionService.AccountService] = AccountService(connection)
        self.services[TransactionService.AssociationService] = AssociationService(
            connection
        )
        self.services[
            TransactionService.ExtensibleMessageService
        ] = ExtensibleMessageService(connection)
        self.services[TransactionService.PlayNowService] = PlayNowService(connection)
        self.services[TransactionService.PresenceService] = PresenceService(connection)
        self.services[TransactionService.RankingService] = RankingService(connection)
        self.services[TransactionService.RecordService] = RecordService(connection)

    async def get_response(self, service, message):
        """Get response from a transaction"""

        if not self.connection.loggedUser and not self.connection.loggedUserKey:
            # User is not logged in, check if the transaction is allowed without auth

            if (
                service == TransactionService.ConnectService
                or message.Get("TXN") in self.allowed_transactions_without_auth
            ):
                # Transaction is allowed without auth
                transaction_response = await self.services[service].handle(message)
            else:
                # Transaction is not allowed without auth
                self.connection.logger.error(
                    f"Transaction {message.Get('TXN')} not allowed without auth"
                )

                transaction_response = TransactionError(
                    TransactionError.Code.SESSION_NOT_AUTHORIZED
                )
        else:
            # User is logged in
            transaction_response = await self.services[service].handle(message)

        return transaction_response

    async def start(
        self, service: TransactionService | str, txn: Enum | str, data: dict
    ):
        """Start a unscheduled transaction"""

        if isinstance(service, str):
            service = TransactionService(service)

        txnVal = txn if isinstance(txn, str) else txn.value

        if txnVal not in self.allowed_unscheduled_transactions:
            raise TransactionException("Transaction not allowed to be unscheduled")

        # Unscheduled transactions are always "SimpleResponse" kind, and have no transaction ID

        packet_to_send = await self.services[service].start_transaction(txnVal, data)

        if isinstance(packet_to_send, TransactionError):
            packet = Packet()
            packet.service = service.value
            packet.kind = TransactionKind.SimpleResponse.value
            packet.Set("TXN", txnVal)
            packet.Set("errorCode", packet_to_send.errorCode)
            packet.Set("localizedMessage", packet_to_send.localizedMessage)
            packet.Set("errorContainer", packet_to_send.errorContainer)

            await self.connection.send_packet(packet, 0)
        else:
            packet_to_send.service = service.value
            packet_to_send.kind = TransactionKind.SimpleResponse.value
            packet_to_send.Set("TXN", txnVal)
            await self.connection.send_packet(packet_to_send, 0)

    async def verify_transaction(self, message):
        # Verify that the service is valid
        error = False

        try:
            service = TransactionService(message.service)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction service {message.service}"
            )

            service = None
            error = True

        # Verify that the transaction kind is valid
        transaction_kind_int = message.kind & 0xFF000000

        try:
            transaction_kind = TransactionKind(transaction_kind_int)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction type {hex(transaction_kind_int)}"
            )

            transaction_kind = None
            error = True

        # Verify that the transaction id is valid
        message_tid = message.kind & 0x00FFFFFF

        if (
            not self.connection.initialized
            and service == TransactionService.ConnectService
        ):
            # This is the first transaction from the client
            self.tid = message_tid  # Set the initial transaction id

        if message_tid != self.tid:
            if transaction_kind == TransactionKind.SimpleResponse and message_tid == 0:
                # Simple transactions with a transaction id of 0 are unscheduled transactions (responses)
                # Check if this unscheduled transaction is allowed

                if message.Get("TXN") not in self.allowed_unscheduled_transactions:
                    self.connection.logger.error(
                        f"Unscheduled transaction {message.Get('TXN')} not allowed"
                    )

                    error = True
            else:
                self.connection.logger.error(
                    f"Invalid transaction id, expected {self.tid}, got {message_tid}. Ignoring message..."
                )
                error = True

        return service, transaction_kind, transaction_kind_int, error

    async def finish(self, message: Packet):
        """Finish transaction started by client"""

        (
            service,
            transaction_kind,
            transaction_kind_int,
            verifyError,
        ) = await self.verify_transaction(message)

        if verifyError:
            transaction_response = TransactionError(TransactionError.Code.SYSTEM_ERROR)
        else:
            # Handle the transaction
            if (
                not self.connection.initialized
                and transaction_kind != TransactionKind.Simple
                or not self.connection.initialized
                and service != TransactionService.ConnectService
            ):
                transaction_response = TransactionError(
                    TransactionError.Code.NOT_INITIALIZED
                )
            elif (
                transaction_kind == TransactionKind.Simple
                or transaction_kind == TransactionKind.SimpleResponse
            ):
                transaction_response = await self.get_response(service, message)
            elif transaction_kind == TransactionKind.Chunked:
                self.incoming_queue.append(message)

                received_length = 0

                for incoming_message in self.incoming_queue:
                    received_length += len(incoming_message.Get("data"))

                if received_length == message.Get("size"):
                    # We have received all chunks, process the transaction
                    encoded_data = ""

                    for incoming_message in self.incoming_queue:
                        encoded_data += incoming_message.Get("data")

                    self.incoming_queue.clear()

                    decoded_data = b64decode(encoded_data)

                    message = Packet(
                        service=service.value, kind=message.kind, data=decoded_data
                    )

                    transaction_response = await self.get_response(service, message)
                else:
                    # We haven't received all chunks yet
                    return
            else:
                self.connection.logger.error(
                    f"Invalid transaction kind {hex(transaction_kind_int)}"
                )
                return

        if transaction_response is None:
            self.connection.logger.error("Transaction service didn't return a response")
            return
        elif isinstance(transaction_response, TransactionSkip):
            return

        # Send the response
        if isinstance(transaction_response, TransactionError):
            packet = Packet()
            packet.service = service.value if service is not None else message.service
            packet.kind = TransactionKind.SimpleResponse.value
            packet.Set("TXN", message.Get("TXN"))

            if not self.connection.initialized:
                packet.kind = TransactionKind.InitialError.value
                packet.Set("TID", self.tid)

            packet.Set("errorCode", transaction_response.errorCode)
            packet.Set("localizedMessage", transaction_response.localizedMessage)
            packet.Set("errorContainer", transaction_response.errorContainer)

            await self.connection.send_packet(packet, self.tid)
        else:
            transaction_response.service = service.value
            transaction_response.kind = TransactionKind.SimpleResponse.value
            transaction_response.Set("TXN", message.Get("TXN"))
            message_bytes = transaction_response.compile()

            if (
                len(message_bytes) > self.connection.fragmentSize
                and self.connection.fragmentSize != -1
            ):
                # Packet is too big, we need to base64 encode it and split it into fragments
                message_bytes = message_bytes[HEADER_LENGTH:]  # Get rid of the header

                decoded_message_size = len(message_bytes)
                message_bytes = b64encode(message_bytes).decode()
                encoded_message_size = len(message_bytes)

                fragments = [
                    message_bytes[i : i + self.connection.fragmentSize]
                    for i in range(0, len(message_bytes), self.connection.fragmentSize)
                ]

                for fragment in fragments:
                    fragment_packet = Packet()
                    fragment_packet.service = service.value
                    fragment_packet.kind = TransactionKind.ChunkedResponse.value

                    fragment_packet.Set("data", fragment)
                    fragment_packet.Set("decodedSize", decoded_message_size)
                    fragment_packet.Set("size", encoded_message_size)

                    await self.connection.send_packet(fragment_packet, self.tid)

                    gc.collect()
            else:
                await self.connection.send_packet(transaction_response, self.tid)

        self.tid += 1
