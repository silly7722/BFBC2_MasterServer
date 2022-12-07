import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from BFBC2_MasterServer.packet import Packet, PacketParseException


class BFBC2Consumer(AsyncWebsocketConsumer):
    async def connect(self):
        ip = None

        for header in self.scope["headers"]:
            if header[0].decode().upper() == settings.REAL_IP_HEADER:
                ip = header[1].decode().split(",")[0].strip()
                break

        if ip is None:
            ip, port = self.scope["client"]
        else:
            _, port = self.scope["client"]

        self.ip = ip

        self.logger = logging.LoggerAdapter(
            logging.getLogger("consumer"),
            {"path": self.scope["path"], "address": f"{self.ip}:{port}"},
        )

        self.logger.setLevel(logging.DEBUG)

        self.logger.info("-- Connected")
        await self.accept()

    async def disconnect(self, close_code):
        self.logger.info(f"-- Disconnected (Code: {close_code})")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is not None:
            self.logger.error(
                f"-- Received text data which are not supported, disconnecting"
            )
            return await self.close()

        try:
            packet = Packet(raw_data=bytes_data)
            self.logger.debug(f"<- {packet}")
        except PacketParseException as e:
            self.logger.exception(f"-- {e}")
            return await self.close()

        return packet

    async def send_packet(self, packet: Packet):
        self.logger.debug(f"-> {packet}")
        await self.send(bytes_data=packet.compile())

    async def external_send(self, event):
        raise NotImplementedError("external_send not implemented")
