import csv
import json
import os
import random
import string
from base64 import b64decode, b64encode
from datetime import date
from enum import Enum
from pathlib import Path

from asgiref.sync import sync_to_async
from BFBC2_MasterServer.packet import Packet
from BFBC2_MasterServer.service import Service
from BFBC2_MasterServer.tools import legacy_b64encode
from channels.auth import database_sync_to_async, get_user, login
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from email_validator import EmailNotValidError, validate_email
from Plasma.enumerators.ActivationResult import ActivationResult
from Plasma.enumerators.ClientType import ClientType
from Plasma.error import TransactionError
from Plasma.models import Entitlement, Persona
from Plasma.services.connect import TXN as ConnectTXN


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

    ENCRYPTED_PREFIX = "Ciyvab0tregdVsBtboIpeChe4G6uzC1v5_-SIxmvSL"

    countryListPath = os.path.join(settings.BASE_DIR, "Plasma/data/CountryList")
    tosPath = os.path.join(settings.BASE_DIR, "Plasma/data/TOS")

    countryConfigOverrides = {}
    validCountryCodes = []

    def __init__(self, connection) -> None:
        super().__init__(connection)

        self.resolver_map[TXN.NuLogin] = self.__handle_login
        self.resolver_map[TXN.NuAddAccount] = self.__handle_add_account
        self.resolver_map[TXN.NuAddPersona] = self.__handle_add_persona
        self.resolver_map[TXN.NuDisablePersona] = self.__handle_disable_persona
        self.resolver_map[TXN.GetCountryList] = self.__handle_get_country_list
        self.resolver_map[TXN.NuGetTos] = self.__handle_get_tos
        self.resolver_map[TXN.NuLoginPersona] = self.__handle_login_persona
        self.resolver_map[TXN.NuGetPersonas] = self.__handle_get_personas
        self.resolver_map[TXN.GetTelemetryToken] = self.__handle_get_telemetry_token
        self.resolver_map[TXN.NuGetEntitlements] = self.__handle_get_entitlements
        self.resolver_map[TXN.NuEntitleGame] = self.__handle_entitle_game

    def _get_resolver(self, txn):
        return self.resolver_map[TXN(txn)]

    def _get_creator(self, txn):
        return self.creator_map[TXN(txn)]

    def __get_locale(self):
        locale = self.connection.locale.value

        if settings.DEBUG:
            locale = "test"

        return locale

    def __get_tos(self):
        """Get TOS"""

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

        return tos_content, tos_version

    async def __internal_login(self, data: Packet, allow_unentitled=False):
        """Internal login handler"""

        nuid = data.Get("nuid")
        password = data.Get("password")
        encryptedInfo = data.Get("encryptedInfo")

        if not ((nuid or password) or encryptedInfo):
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        if encryptedInfo:
            encryptedInfo = encryptedInfo.replace(self.ENCRYPTED_PREFIX, "")
            encryptedInfo = encryptedInfo.replace("-", "=").replace(
                "_", "="
            )  # Bring string into proper format again

            decryptedInfo = b64decode(encryptedInfo).decode("utf-8")

            if pos := decryptedInfo.find("\f"):
                nuid = decryptedInfo[:pos]
                password = decryptedInfo[pos + 1 :]

        umodel = get_user_model()

        if not await umodel.objects.user_exists(nuid):
            return TransactionError(TransactionError.Code.USER_NOT_FOUND)

        user = await sync_to_async(authenticate)(nuid=nuid, password=password)

        if not user:
            # Authentication failed, invalid password
            return TransactionError(TransactionError.Code.INVALID_PASSWORD)
        else:
            # Authentication successful, check if user logged to server account and if so check if client is server

            if user.isServerAccount and self.connection.clientType != ClientType.SERVER:
                return TransactionError(TransactionError.Code.USER_NOT_FOUND)

        await sync_to_async(update_last_login)(None, user)

        if not user.isServerAccount:
            # This is normal user, check whether user is entitled an accepted latest TOS
            tosVersion = data.Get("tosVersion")

            # User sent TOS version in request, that means he has accepted latest TOS
            if tosVersion:
                await umodel.objects.accept_tos(user, tosVersion)

            _, tos_version = self.__get_tos()

            if tos_version != user.tosVersion:
                return TransactionError(TransactionError.Code.TOS_OUT_OF_DATE)

            is_entitled = await Entitlement.objects.is_entitled_for_game(
                user, self.connection.clientString
            )

            if not is_entitled:
                if not allow_unentitled:
                    return TransactionError(TransactionError.Code.NOT_ENTITLED_TO_GAME)

        active_session = cache.get(f"userSession:{user.id}")
        channel_layer = get_channel_layer()

        if active_session:
            if active_session != self.connection.channel_name:
                self.connection.logger.warning(
                    f"User {user.id} has active session, destroying it"
                )

                await channel_layer.send(
                    active_session,
                    {
                        "type": "external.send",
                        "message": {"TXN": ConnectTXN.Goodbye.value, "reason": 2},
                    },
                )

        cache.set(f"userSession:{user.id}", self.connection.channel_name, timeout=None)

        encryptedLoginInfo = None

        if data.Get("returnEncryptedInfo"):
            # Store the user name and password as a base64 encoded string and put the chunk in front of it (so we have a similar format to the original one)
            loginInfo = f"{nuid}\f{password}"
            loginInfo = self.ENCRYPTED_PREFIX + b64encode(
                loginInfo.encode("utf-8")
            ).decode("utf-8")
            loginInfo = loginInfo.replace("=", "_")

            encryptedLoginInfo = loginInfo

        user_lkey = cache.get(f"userLoginKey:{user.id}")

        if not user_lkey:
            # Generate new login key, because user doesn't have one (or previous one expired)
            user_lkey = (
                "".join(
                    random.choice(string.ascii_letters + string.digits + "-_")
                    for _ in range(27)
                )
                + "."
            )

            # Save login key that never expires (we set expiration time when user logs out)
            cache.set(f"userLoginKey:{user.id}", user_lkey, timeout=None)
        else:
            # User already has login key, so we need to delete it from cache
            cache.touch(f"userLoginKey:{user.id}", timeout=None)

        self.connection.loggedUser = user
        self.connection.loggedUserKey = user_lkey

        await login(self.connection.scope, user)
        await database_sync_to_async(self.connection.scope["session"].save)()

        return user, user_lkey, encryptedLoginInfo

    async def __handle_login(self, data):
        response_data = await self.__internal_login(data)

        if isinstance(response_data, TransactionError):
            return response_data

        # Login successful
        # This packet is kind of interesting, because "successful" login (for game at least) doesn't require any data to be sent back (except for the TXN of course)
        # But, original server sends back nuid, lkey, profileId, userId and encryptedInfo (if requested)
        # So, we are doing the same
        #
        # The game will overwrite internally all data we will send below when user will log on to the persona
        # "profileId" and "userId" are the same (just like in original server responses)
        # Additionally "profileId" is not read by the game at all in NuLogin response

        user, user_lkey, encryptedLoginInfo = response_data
        response = Packet()
        response.Set("nuid", user.nuid)
        response.Set("lkey", user_lkey)
        response.Set("profileId", user.id)
        response.Set("userId", user.id)

        if encryptedLoginInfo:
            response.Set("encryptedLoginInfo", encryptedLoginInfo)

        return response

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

    async def __handle_add_persona(self, data):
        """Add a new persona"""

        user = await get_user(self.connection.scope)
        name = data.Get("name")

        if not name:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        success = await Persona.objects.create_persona(user, name)

        if not success:
            return TransactionError(TransactionError.Code.ALREADY_REGISTERED)

        response = Packet()
        return response

    async def __handle_disable_persona(self, data):
        """Remove a persona"""

        user = await get_user(self.connection.scope)
        name = data.Get("name")

        if not name:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        success = await Persona.objects.delete_persona(user, name)

        if not success:
            return TransactionError(TransactionError.Code.TRANSACTION_DATA_NOT_FOUND)
        else:
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

        if (
            selected_country_code is not None
            and selected_country_code not in self.validCountryCodes
        ):
            raise ValueError(
                f"{selected_country_code} is not valid country code for NuGetTos."
            )

        # In theory everything shows that here we should send the TOS for the selected country code.
        # However, this doesn't seem to be the case. Original server sends the same TOS for every country code, only (game) language seems to have any effect.

        tos_content, tos_version = self.__get_tos()

        response = Packet()
        response.Set("tos", tos_content)
        response.Set("version", tos_version)

        return response

    async def __handle_login_persona(self, data):
        """Login a persona"""

        user = await get_user(self.connection.scope)
        name = data.Get("name")

        if not name:
            return TransactionError(TransactionError.Code.PARAMETERS_ERROR)

        persona = await Persona.objects.get_persona(user, name)

        if persona is None:
            return TransactionError(TransactionError.Code.USER_NOT_FOUND)

        persona_lkey = cache.get(f"personaLoginKey:{user.id}")

        if not persona_lkey:
            # Generate new login key, because user doesn't have one (or previous one expired)
            persona_lkey = (
                "".join(
                    random.choice(string.ascii_letters + string.digits + "-_")
                    for _ in range(27)
                )
                + "."
            )

            # Save login key that never expires (we set expiration time when user logs out)
            cache.set(f"personaLoginKey:{user.id}", persona_lkey, timeout=None)
            cache.set(f"lkeyMap:{persona_lkey}", persona.id, timeout=None)
        else:
            # User already has login key, so we need to delete it from cache
            cache.touch(f"personaLoginKey:{user.id}", timeout=None)
            cache.touch(f"lkeyMap:{persona_lkey}", timeout=None)

        self.connection.loggedPersona = persona
        self.connection.loggedPersonaKey = persona_lkey

        response = Packet()
        response.Set("lkey", persona_lkey)
        response.Set(
            "profileId", persona.id
        )  # Again, game doesn't seem to care about this
        response.Set("userId", user.id)

        return response

    async def __handle_get_telemetry_token(self, data):
        """Get telemetry token"""
        token = "0.0.0.0,9946,"

        locale = str(self.connection.locale.value).replace("_", "")

        if len(locale) == 2:
            locale = locale + locale.upper()

        token += locale

        # Token also have some encoded data (for telemetry)
        # We don't need it, so we just fill it with zeros

        token += (
            "\0" * 104
        )  # Token length is 104 bytes (at least that's what I've seen in original server)
        token = legacy_b64encode(token).decode("utf-8")

        response = Packet()
        response.Set("telemetryToken", token)
        response.Set(
            "enabled",
            "CA,MX,PR,US,VI,AD,AF,AG,AI,AL,AM,AN,AO,AQ,AR,AS,AW,AX,AZ,BA,BB,BD,BF,BH,BI,BJ,BM,BN,BO,BR,BS,BT,BV,BW,BY,BZ,CC,CD,CF,CG,CI,CK,CL,CM,CN,CO,CR,CU,CV,CX,DJ,DM,DO,DZ,EC,EG,EH,ER,ET,FJ,FK,FM,FO,GA,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GS,GT,GU,GW,GY,HM,HN,HT,ID,IL,IM,IN,IO,IQ,IR,IS,JE,JM,JO,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LY,MA,MC,MD,ME,MG,MH,ML,MM,MN,MO,MP,MQ,MR,MS,MU,MV,MW,MY,MZ,NA,NC,NE,NF,NG,NI,NP,NR,NU,OM,PA,PE,PF,PG,PH,PK,PM,PN,PS,PW,PY,QA,RE,RS,RW,SA,SB,SC,clntSock,SG,SH,SJ,SL,SM,SN,SO,SR,ST,SV,SY,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TT,TV,TZ,UA,UG,UM,UY,UZ,VA,VC,VE,VG,VN,VU,WF,WS,YE,YT,ZM,ZW,ZZ",
        )
        response.Set("filters", "")
        response.Set("disabled", "")

        return response

    async def __handle_get_personas(self, data):
        """Get the list of personas"""

        user = await get_user(self.connection.scope)
        personas = await Persona.objects.list_personas(user)

        response = Packet()
        response.Set("personas", personas)

        return response

    async def __handle_get_entitlements(self, data):
        """Get the list of entitlements"""

        user = await get_user(self.connection.scope)
        groupName = data.Get("groupName")

        entitlements = await Entitlement.objects.list_entitlements(user, groupName)
        entitlements_data = [
            {
                "grantDate": entitlement.grantDate,
                "groupName": entitlement.groupName,
                "userId": entitlement.account.id,
                "entitlementTag": entitlement.tag,
                "version": entitlement.version,
                "terminationDate": entitlement.terminationDate,
                "productId": entitlement.productId,
                "entitlementId": entitlement.id,
                "status": entitlement.status,
            }
            for entitlement in entitlements
        ]

        response = Packet()
        response.Set("entitlements", entitlements_data)

        return response

    async def __handle_entitle_game(self, data):
        """Entitle game (user enters game key while login)"""

        response_data = await self.__internal_login(data, allow_unentitled=True)

        if isinstance(response_data, TransactionError):
            return response_data

        user, user_lkey, encryptedLoginInfo = response_data

        key = data.Get("key")
        activation_result = await Entitlement.objects.activate_game(user, key)

        if activation_result == ActivationResult.INVALID_KEY:
            return TransactionError(TransactionError.Code.CODE_NOT_FOUND)
        elif activation_result == ActivationResult.ALREADY_USED:
            return TransactionError(TransactionError.Code.CODE_ALREADY_USED)

        response = Packet()
        response.Set("nuid", user.nuid)
        response.Set("lkey", user_lkey)
        response.Set("profileId", user.id)
        response.Set("userId", user.id)

        if encryptedLoginInfo:
            response.Set("encryptedLoginInfo", encryptedLoginInfo)

        return response
