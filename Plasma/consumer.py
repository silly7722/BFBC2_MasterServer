from BFBC2_MasterServer.consumer import BFBC2Consumer

from Plasma.transactor import TransactionKind, Transactor


class PlasmaConsumer(BFBC2Consumer):

    initialized = False

    transactor = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transactor = Transactor(self)

    async def receive(self, text_data=None, bytes_data=None):
        message = await super().receive(text_data, bytes_data)

        if message is None:
            return

        await self.transactor.finish(message)

    async def send_packet(self, packet, tid):
        if packet.kind != TransactionKind.InitialError.value:
            packet.kind = packet.kind & 0xFF000000 | tid

        await super().send_packet(packet)
