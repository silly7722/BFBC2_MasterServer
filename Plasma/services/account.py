import csv
import json
import os
from enum import Enum
from pathlib import Path

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from django.conf import settings


class TXN(Enum):
    NuLogin = "NuLogin"
    NuAddAccount = "NuAddAccount"
    NuAddPersona = "NuAddPersona"
    NuDisablePersona = "NuDisablePersona"
    GetCountryList = "GetCountryList"
    NuGetTos = "NuGetTos"
    NuCreateEncryptedToken = "NuCreateEncryptedToken"
    NuSuggestPersonas = "NuSuggestPersonas"
    NuLoginPersona = "NuLoginPersona"
    NuUpdatePassword = "NuUpdatePassword"
    NuGetAccount = "NuGetAccount"
    NuGetAccountByNuid = "NuGetAccountByNuid"
    NuGetAccountByPS3Ticket = "NuGetAccountByPS3Ticket"
    NuGetPersonas = "NuGetPersonas"
    NuUpdateAccount = "NuUpdateAccount"
    GameSpyPreAuth = "GameSpyPreAuth"
    NuXBL360Login = "NuXBL360Login"
    NuXBL360AddAccount = "NuXBL360AddAccount"
    NuPS3Login = "NuPS3Login"
    NuPS3AddAccount = "NuPS3AddAccount"
    TransactionException = "TransactionException"
    NuLookupUserInfo = "NuLookupUserInfo"
    NuSearchOwners = "NuSearchOwners"
    GetTelemetryToken = "GetTelemetryToken"
    NuGetEntitlements = "NuGetEntitlements"
    NuGetEntitlementCount = "NuGetEntitlementCount"
    NuEntitleGame = "NuEntitleGame"
    NuEntitleUser = "NuEntitleUser"
    NuGrantEntitlement = "NuGrantEntitlement"
    GetLockerURL = "GetLockerURL"


class AccountService(Service):

    countryListPath = os.path.join(settings.BASE_DIR, "Plasma/data/CountryList")
    tosPath = os.path.join(settings.BASE_DIR, "Plasma/data/TOS")

    countryConfigOverrides = {}
    validCountryCodes = []

    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.resolver_map[TXN.GetCountryList] = self.__handle_get_country_list
        self.resolver_map[TXN.NuGetTos] = self.__handle_get_tos

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    def __get_locale(self):
        locale = self.connection.locale.value

        if settings.DEBUG:
            locale = "test"

        return locale

    async def __handle_get_country_list(self, data):
        """Get the list of countries"""

        locale = self.__get_locale()

        countryList = []
        countryListFilename = "CountryList.csv"

        if Path(
            os.path.join(
                self.countryListPath, countryListFilename.replace(".", f".{locale}.")
            )
        ).exists():
            countryListFilename = countryListFilename.replace(".", f".{locale}.")

        with open(os.path.join(self.countryListPath, "overrides.json"), "r") as file:
            overrides = json.load(file)

            if settings.DEBUG:
                overrides["DBG"] = {
                    "allowEmailsDefaultValue": 0,
                    "parentalControlAgeLimit": 18,
                    "registrationAgeLimit": 13,
                }

            self.countryConfigOverrides = overrides

        with open(os.path.join(self.countryListPath, countryListFilename), "r") as file:
            reader = csv.DictReader(file)

            for row in reader:
                iso_code = row["ISOCode"]

                if iso_code in overrides:
                    for key in overrides[iso_code]:
                        row[key] = overrides[iso_code][key]

                self.validCountryCodes.append(iso_code)
                countryList.append(row)

        # This is simple packet, example country looks like this:
        # {
        #     "ISOCode": "DBG",
        #     "description": "Example Country",
        # }
        #
        # ISOCode is the country code, description is the country name (visible in game)
        # ISOCode is usually 2 letters, but can be up to 3 letters (like DBG above)
        #
        # Each country can specify optional fields:
        # allowEmailsDefaultValue: 0 or 1 (default is 0)
        # parentalControlAgeLimit: int (default is 18)
        # registrationAgeLimit: int (default is 13)
        #

        response = Packet()
        response.Set("countryList", countryList)

        return response

    async def __handle_get_tos(self, data):
        """Get the Terms of Service"""

        selected_country_code = data.Get("countryCode")

        if selected_country_code is None:
            self.connection.logger.warning("No country code provided for NuGetTos.")
        elif selected_country_code not in self.validCountryCodes:
            raise ValueError(
                f"{selected_country_code} is not valid country code for NuGetTos."
            )

        # In theory everything shows that here we should send the TOS for the selected country code.
        # However, this doesn't seem to be the case. Original server sends the same TOS for every country code, only (game) language seems to have any effect.

        locale = self.__get_locale()

        tosFilename = "TOS.txt"

        if Path(
            os.path.join(self.tosPath, tosFilename.replace(".", f".{locale}."))
        ).exists():
            tosFilename = tosFilename.replace(".", f".{locale}.")

        finalPath = os.path.join(self.tosPath, tosFilename)

        with open(finalPath, "r") as file:
            tos_content = file.read()

        with open(finalPath.replace(".txt", ".version"), "r") as file:
            tos_version = file.read()

        response = Packet()
        response.Set("tos", tos_content)
        response.Set("version", tos_version)

        return response
