import logging
from enum import Enum

from BFBC2_MasterServer.packet import Packet
from Theater.transactions.connect import connect
from Theater.transactions.create_game import create_game
from Theater.transactions.echo import echo
from Theater.transactions.enter_game_host_response import enter_game_host_response
from Theater.transactions.enter_game_request import enter_game_request
from Theater.transactions.get_game_details import get_game_details
from Theater.transactions.get_game_list import get_game_list
from Theater.transactions.get_lobby_list import get_lobby_list
from Theater.transactions.leave_game import leave_game
from Theater.transactions.login import login
from Theater.transactions.ping import ping
from Theater.transactions.player_entered import player_entered
from Theater.transactions.player_exited import player_exited
from Theater.transactions.update_bracket import update_bracket
from Theater.transactions.update_game_data import update_game_data
from Theater.transactions.update_game_details import update_game_details

logger = logging.getLogger(__name__)


class Transaction(Enum):
    Connect = "CONN"
    Login = "USER"
    Echo = "ECHO"
    GetLobbyList = "LLST"
    GetGameList = "GLST"
    GetGameDetails = "GDAT"
    CreateGame = "CGAM"
    UpdateBracket = "UBRA"
    UpdateGameData = "UGAM"
    UpdateGameDetails = "UGDE"
    EnterGameRequest = "EGAM"
    EnterGameHostRequest = "EGRQ"
    EnterGameHostResponse = "EGRS"
    PlayerEntered = "PENT"
    PlayerExited = "PLVT"
    LeaveGame = "ECNL"
    Ping = "PING"


class TransactionKind(Enum):
    Normal = 0x40000000
    NormalResponse = 0x00000000


class Transactor:

    tid = 0  # Transaction ID
    transactions = {}

    allowed_remote_transactions = [Transaction.EnterGameHostRequest]

    def __init__(self, connection):
        self.connection = connection

        self.transactions[Transaction.Connect] = connect
        self.transactions[Transaction.Login] = login
        self.transactions[Transaction.GetLobbyList] = get_lobby_list
        self.transactions[Transaction.GetGameList] = get_game_list
        self.transactions[Transaction.GetGameDetails] = get_game_details
        self.transactions[Transaction.CreateGame] = create_game
        self.transactions[Transaction.UpdateBracket] = update_bracket
        self.transactions[Transaction.UpdateGameData] = update_game_data
        self.transactions[Transaction.UpdateGameDetails] = update_game_details
        self.transactions[Transaction.EnterGameRequest] = enter_game_request
        self.transactions[Transaction.EnterGameHostResponse] = enter_game_host_response
        self.transactions[Transaction.PlayerEntered] = player_entered
        self.transactions[Transaction.PlayerExited] = player_exited
        self.transactions[Transaction.LeaveGame] = leave_game
        self.transactions[Transaction.Ping] = ping
        self.transactions[Transaction.Echo] = echo

    async def start(self, service, data):
        service = Transaction(service)

        if service not in self.allowed_remote_transactions:
            logger.error(f"Transaction {service} is not allowed to be sent remotely")

        packet = Packet()
        packet.service = service.value
        packet.kind = TransactionKind.NormalResponse.value

        for key in data:
            packet.Set(key, data[key])

        await self.connection.send_packet(packet)

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
            if (
                self.connection.currentlyUpdating
                and transaction == Transaction.UpdateBracket
            ):
                self.tid += 1
            elif transaction == Transaction.Ping:
                pass
            else:
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
                if response is None:
                    continue

                if response.service is None:
                    response.service = transaction.value

                response.kind = TransactionKind.NormalResponse.value

                if transaction != Transaction.Ping:
                    response.Set("TID", self.tid)
                else:
                    response.Set("TID", 0)

                await self.connection.send_packet(response)

        if not self.connection.currentlyUpdating:
            self.tid += 1
