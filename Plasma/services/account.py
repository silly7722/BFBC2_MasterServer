import csv
import json
import os
from datetime import date
from enum import Enum
from pathlib import Path

from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from email_validator import EmailNotValidError, validate_email
from Plasma.error import TransactionError


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

        self.resolver_map[TXN.NuAddAccount] = self.__handle_add_account
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

    async def __handle_add_account(self, data):
        """Add a new account"""

        errContainer = []
        umodel = get_user_model()

        # Check if nuid and password are provided
        nuid = data.Get("nuid")
        password = data.Get("password")

        if not nuid or not password:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        try:
            validation = validate_email(nuid, check_deliverability=True)
            nuid = validation.email
        except EmailNotValidError as e:
            self.connection.logger.error(f"-- Not a valid email address. ({e})")

            errContainer.append(
                {
                    "fieldName": "email",
                    "fieldError": 6,
                    "value": "INVALID_VALUE",
                }
            )

            return TransactionError(
                TransactionError.Code.PARAMETERS_ERROR, errContainer
            )

        try:
            validate_password(password)
        except ValidationError as e:
            self.connection.logger.error(f"-- Not a valid password. ({e})")

            errContainer.append(
                {
                    "fieldName": "password",
                    "fieldError": 6,
                    "value": "INVALID_VALUE",
                }
            )

            return TransactionError(
                TransactionError.Code.PARAMETERS_ERROR, errContainer
            )

        dateOfBirth = date(
            data.Get("DOBYear"), data.Get("DOBMonth"), data.Get("DOBDay")
        )

        dateToday = date.today()

        age = (
            dateToday.year
            - dateOfBirth.year
            - ((dateToday.month, dateToday.day) < (dateOfBirth.month, dateOfBirth.day))
        )

        countryConfig = self.countryConfigOverrides.get(data.Get("country"), {})
        errContainer = []

        if countryConfig.get("registrationAgeLimit", 13) > age:
            # New user is too young to register
            errContainer.append(
                {
                    "fieldName": "dob",
                    "fieldError": 15,
                }
            )

            return TransactionError(
                TransactionError.Code.PARAMETERS_ERROR, errContainer
            )
        elif await umodel.objects.user_exists(nuid):
            # User already exists
            return TransactionError(TransactionError.Code.ALREADY_REGISTERED)
        else:
            # Create user
            await umodel.objects.create_user(
                nuid=nuid,
                password=password,
                globalOptin=data.Get("globalOptin"),
                thirdPartyOptin=data.Get("thirdPartyOptin"),
                parentalEmail=data.Get("parentalEmail"),
                dateOfBirth=dateOfBirth,
                firstName=data.Get("first_Name"),
                lastName=data.Get("last_Name"),
                gender=data.Get("gender"),
                address=data.Get("street"),
                address2=data.Get("street2"),
                city=data.Get("city"),
                state=data.Get("state"),
                zipCode=data.Get("zipCode"),
                country=data.Get("country"),
                language=data.Get("language"),
                tosVersion=data.Get("tosVersion"),
            )

            # Create response
            response = Packet()
            return response

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
