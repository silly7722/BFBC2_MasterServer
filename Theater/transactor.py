from enum import Enum

from Theater.transactions.connect import connect
from Theater.transactions.create_game import create_game
from Theater.transactions.echo import echo
from Theater.transactions.login import login


class Transaction(Enum):
    Connect = "CONN"
    Login = "USER"
    Echo = "ECHO"
    CreateGame = "CGAM"


class TransactionKind(Enum):
    Normal = 0x40000000
    NormalResponse = 0x00000000


class Transactor:

    tid = 0  # Transaction ID
    transactions = {}

    def __init__(self, connection):
        self.connection = connection

        self.transactions[Transaction.Connect] = connect
        self.transactions[Transaction.Login] = login
        self.transactions[Transaction.Echo] = echo
        self.transactions[Transaction.CreateGame] = create_game

    async def finish(self, message):
        """Finish transaction started by client"""

        # Verify that the service is valid
        try:
            transaction = Transaction(message.service)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction service {message.service}"
            )
            return

        # Verify that the transaction kind is valid
        try:
            TransactionKind(message.kind)
        except ValueError:
            self.connection.logger.error(
                f"Invalid transaction type {hex(message.kind)}"
            )
            return

        if transaction == Transaction.Echo:
            responses = self.transactions[transaction](self.connection, message)
            response = next(responses)

            response.service = transaction.value
            response.kind = TransactionKind.NormalResponse.value
            await self.connection.send_packet(response)
            return

        tid = message.Get("TID")

        if not self.connection.initialized and transaction == Transaction.Connect:
            # This is the first transaction from the client
            self.tid = tid  # Set the initial transaction id
        elif not self.connection.initialized and transaction != Transaction.Connect:
            # Client is not initialized, but the transaction is not CONN
            self.connection.logger.error(
                f"Client sent {transaction} before CONN, ignoring..."
            )
            return

        if tid != self.tid:
            self.connection.logger.error(
                f"Invalid transaction id, expected {self.tid}, got {tid}. Ignoring message..."
            )
            return

        try:
            responses = self.transactions[transaction](self.connection, message)
        except KeyError:
            self.connection.logger.error(
                f"Transaction {transaction} is not implemented"
            )
            return

        if responses is not None:
            async for response in responses:
                response.service = transaction.value
                response.kind = TransactionKind.NormalResponse.value
                response.Set("TID", self.tid)
                await self.connection.send_packet(response)

        self.tid += 1
