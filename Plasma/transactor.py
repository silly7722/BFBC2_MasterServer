import gc
from base64 import b64decode, b64encode
from enum import Enum

from BFBC2_MasterServer.packet import HEADER_LENGTH, Packet

from Plasma.error import Error, TransactionError, TransactionException, TransactionSkip
from Plasma.services.connect import TXN as ConnectTXN
from Plasma.services.connect import ConnectService


class TransactionService(Enum):
    ConnectService = "fsys"


class TransactionKind(Enum):
    Initial = 0xC0000000
    InitialError = 0x66657272
    Simple = 0x80000000
    Chunked = 0xF0000000
    ChunkedResponse = 0xB0000000


class Transactor:
    incoming_queue = []
    tid = 0  # Transaction ID

    services = {}
    allowed_uncheduled_transactions = [ConnectTXN.MemCheck.value, ConnectTXN.Ping.value]

    def __init__(self, connection):
        self.connection = connection

        # Init services
        self.services[TransactionService.ConnectService] = ConnectService(connection)

    async def start(self, service: TransactionService, txn: Enum, data: dict):
        """Start a unscheduled transaction"""

        if txn.value not in self.allowed_uncheduled_transactions:
            raise TransactionException("Transaction not allowed to be unscheduled")

        # Unscheduled transactions are always simple, and have no transaction ID

        packet_to_send = await self.services[service].start_transaction(txn, data)

        if isinstance(packet_to_send, TransactionError):
            packet = Packet()
            packet.Set("TXN", packet_to_send.Get("TXN"))
            packet.service = service.value
            packet.kind = TransactionKind.Simple.value
            packet.Set("errorCode", packet_to_send.errorCode)
            packet.Set("localizedMessage", packet_to_send.localizedMessage)
            packet.Set("errorContainer", packet_to_send.errorContainer)

            await self.connection.send_packet(packet, 0)
        else:
            packet_to_send.kind = TransactionKind.Simple.value
            packet_to_send.service = service.value
            packet_to_send.Set("TXN", txn)
            await self.connection.send_packet(packet_to_send, 0)

    async def finish(self, message: Packet):
        """Finish transaction started by client"""

        # Verify that the service is valid
        try:
            service = TransactionService(message.service)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction service {message.service}"
            )
            return

        # Verify that the transaction kind is valid
        transaction_kind_int = message.kind & 0xFF000000

        try:
            transaction_kind = TransactionKind(transaction_kind_int)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction type {hex(transaction_kind_int)}"
            )
            return

        # Verify that the transaction id is valid
        message_tid = message.kind & 0x00FFFFFF

        if transaction_kind == TransactionKind.Initial:
            # This is the first transaction from the client
            self.tid = message_tid  # Set the initial transaction id

        if message_tid != self.tid:
            if transaction_kind == TransactionKind.Simple and message_tid == 0:
                # Simple transactions with a transaction id of 0 are unscheduled transactions (responses)
                # Check if this unscheduled transaction is allowed

                if message.Get("TXN") not in self.allowed_uncheduled_transactions:
                    self.connection.logger.error(
                        f"Unscheduled transaction {message.Get('TXN')} not allowed"
                    )
                    return
            else:
                self.connection.logger.error(
                    f"Invalid transaction id, expected {self.tid}, got {message_tid}. Ignoring message..."
                )
                return

        # Handle the transaction
        if (
            not self.connection.initialized
            and transaction_kind != TransactionKind.Initial
            or not self.connection.initialized
            and service != TransactionService.ConnectService
        ):
            transaction_response = TransactionError(Error.NOT_INITIALIZED)
        elif (
            transaction_kind == TransactionKind.Initial
            or transaction_kind == TransactionKind.Simple
        ):
            transaction_response = await self.services[service].handle(message)
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

                transaction_response = self.services[service].handle(message)
            else:
                # We haven't received all chunks yet
                return

        if transaction_response is None:
            self.connection.logger.error("Transaction service didn't return a response")
            return
        elif isinstance(transaction_response, TransactionSkip):
            return

        # Send the response
        if isinstance(transaction_response, TransactionError):
            packet = Packet()
            packet.Set("TXN", message.Get("TXN"))
            packet.service = service.value
            packet.kind = TransactionKind.Simple.value

            if transaction_kind == TransactionKind.Initial:
                packet.kind = TransactionKind.InitialError.value
                packet.Set("TID", self.tid)

            packet.Set("errorCode", transaction_response.errorCode)
            packet.Set("localizedMessage", transaction_response.localizedMessage)
            packet.Set("errorContainer", transaction_response.errorContainer)

            await self.connection.send_packet(packet, self.tid)
        else:
            transaction_response.kind = TransactionKind.Simple.value
            transaction_response.service = service.value
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
