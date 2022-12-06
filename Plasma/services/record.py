import re
from enum import Enum

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from Plasma.error import TransactionError
from Plasma.models import Record, RecordName


class TXN(Enum):
    AddRecord = "AddRecord"
    GetRecord = "GetRecord"
    UpdateRecord = "UpdateRecord"
    AddRecordAsMap = "AddRecordAsMap"
    GetRecordAsMap = "GetRecordAsMap"
    UpdateRecordAsMap = "UpdateRecordAsMap"
    TransactionException = "TransactionException"


class RecordService(Service):
    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.resolver_map[TXN.AddRecord] = self.__handle_add_record
        self.resolver_map[TXN.GetRecord] = self.__handle_get_record
        self.resolver_map[TXN.UpdateRecord] = self.__handle_update_record
        self.resolver_map[TXN.AddRecordAsMap] = self.__handle_add_record_as_map
        self.resolver_map[TXN.GetRecordAsMap] = self.__handle_get_record_as_map
        self.resolver_map[TXN.UpdateRecordAsMap] = self.__handle_update_record_as_map

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    async def __handle_add_record(self, data):
        """Add a record (clan, dogtags) to the database"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)
        values = data.Get("values")

        for valueData in values:
            key = valueData["key"]
            value = valueData["value"]

            await Record.objects.add_records(
                self.connection.loggedPersona, recordName, key, value
            )

        return Packet()

    async def __handle_get_record(self, data):
        """Get a record (clan, dogtags) from the database"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)

        response = Packet()

        values = []
        records = await Record.objects.get_records(
            self.connection.loggedPersona, recordName
        )

        if not records:
            return TransactionError(TransactionError.Code.RECORD_NOT_FOUND)

        for record in records:
            values.append({"key": record.key, "value": record.value})

        response.Set("values", values)

        return response

    async def __handle_update_record(self, data):
        """Update a record (clan, dogtags) in the database"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)
        values = data.Get("values")

        for valueData in values:
            key = valueData["key"]
            value = valueData["value"]

            await Record.objects.update_records(
                self.connection.loggedPersona, recordName, key, value
            )

        return Packet()

    async def __handle_add_record_as_map(self, data):
        """Add a record (clan, dogtags) to the database (in map format)"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)

        keys = data.GetKeys()

        for key in keys:
            if key == "values.{}":
                continue

            if key.startswith("values."):
                key_value = re.match(r"values.{([\d]{1,})}", key).group(1)
                value = data.Get(key)

                await Record.objects.add_records(
                    self.connection.loggedPersona, recordName, key_value, value
                )

        return Packet()

    async def __handle_get_record_as_map(self, data):
        """Get a record (clan, dogtags) from the database (in map format)"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)

        records = await Record.objects.get_records(
            self.connection.loggedPersona, recordName
        )

        if not records:
            return TransactionError(TransactionError.Code.RECORD_NOT_FOUND)

        first = False

        response = Packet()
        for record in records:
            response.Set("values.{}".format(record["key"]), record["value"])

            if not first:
                first = True
                response.Set("lastModified", record["updated_at"])

        response.Set("state", 1)
        response.Set("TTL", 0)

        return response

    async def __handle_update_record_as_map(self, data):
        """Update a record (clan, dogtags) in the database (in map format)"""

        recordName = data.Get("recordName")

        if recordName is None:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        recordName = RecordName(recordName)

        keys = data.GetKeys()

        for key in keys:
            if key == "values.{}":
                continue

            if key.startswith("values."):
                key_value = re.match(r"values.{([\d]{1,})}", key).group(1)
                value = data.Get(key)

                await Record.objects.update_records(
                    self.connection.loggedPersona, recordName, key_value, value
                )

        return Packet()
