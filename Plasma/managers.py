import json
from base64 import b64decode
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.db.models import F
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber
from django.utils import timezone

from Plasma.enumerators.ActivationResult import ActivationResult


class UserManager(BaseUserManager):
    @sync_to_async
    def create_user(self, nuid, password, **extra_fields):
        if not nuid or not password:
            raise ValueError(
                "Users must have at least valid email address and password"
            )

        nuid = self.normalize_email(nuid)

        user = self.model(nuid=nuid, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, nuid, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        user = self.model(nuid=nuid, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    @sync_to_async
    def user_exists(self, nuid):
        return self.filter(nuid=nuid).exists()

    @sync_to_async
    def accept_tos(self, user, tos_version):
        user.tosVersion = tos_version
        user.save()

    @sync_to_async
    def get_user_by_nuid(self, nuid):
        return self.filter(nuid=nuid).first()

    @sync_to_async
    def get_user_by_id(self, id):
        return self.filter(id=id).first()


class EntitlementManager(models.Manager):
    async def is_entitled_for_game(self, user, game_id):
        filtered_entitlement = await sync_to_async(self.filter)(
            account=user,
            tag=game_id,
            grantDate__lt=timezone.now(),
            isGameEntitlement=True,
        )

        never_expires = await sync_to_async(filtered_entitlement.filter)(
            terminationDate=None
        )

        if await sync_to_async(never_expires.exists)():
            return True
        else:
            timed_entitlements = await sync_to_async(filtered_entitlement.filter)(
                terminationDate__gt=timezone.now()
            )

            return await sync_to_async(timed_entitlements.exists)()

    @sync_to_async
    def list_entitlements(self, user, groupName=None, entitlementTag=None):
        filtered_entitlements = self.filter(
            account=user,
            grantDate__lt=timezone.now(),
            isGameEntitlement=False,
        )

        if groupName:
            filtered_entitlements = filtered_entitlements.filter(groupName=groupName)

        if entitlementTag:
            filtered_entitlements = filtered_entitlements.filter(tag=entitlementTag)

        never_expires = filtered_entitlements.filter(terminationDate=None)
        entitlements = []

        if never_expires.exists():
            entitlements = [entitlement for entitlement in never_expires]

        timed_entitlements = filtered_entitlements.filter(
            terminationDate__gt=timezone.now()
        )

        if timed_entitlements.exists():
            entitlements.extend([entitlement for entitlement in timed_entitlements])

        return [
            {
                "grantDate": entitlement.grantDate,
                "groupName": entitlement.groupName,
                "userId": entitlement.account.id,
                "entitlementTag": entitlement.tag,
                "version": entitlement.version,
                "terminationDate": entitlement.terminationDate,
                "productId": entitlement.productId,
                "entitlementId": entitlement.id,
                "status": "ACTIVE",
            }
            for entitlement in entitlements
        ]
    
    @sync_to_async
    def get_key_targets(self, key):
        return list(key.targets.all())

    async def activate_key(self, user, key):
        from Plasma.models import SerialKey

        valid_key = await sync_to_async(SerialKey.objects.filter)(key=key)

        if not await sync_to_async(valid_key.exists)():
            return ActivationResult.INVALID_KEY, []

        key = await sync_to_async(SerialKey.objects.get)(key=key)

        if key.is_used:
            return ActivationResult.ALREADY_USED, []

        targets = await self.get_key_targets(key)
        activated_list = []

        for target in targets:
            current_entitlements = await self.list_entitlements(
                user, target.group
            )
            already_entitled = False

            for entitlement in current_entitlements:
                if entitlement["entitlementTag"] == target.tag:
                    already_entitled = True
                    break

            if already_entitled:
                continue

            duration = target.duration

            if duration:
                duration = timezone.now() + timezone.timedelta(
                    seconds=duration
                )

            activated_entitlement = await sync_to_async(self.create)(
                account=user,
                tag=target.tag,
                groupName=target.group,
                productId=target.product,
                grantDate=timezone.now(),
                terminationDate=duration,
                isGameEntitlement=target.game,
            )

            activated_list.append(activated_entitlement)

        if not key.is_permanent:
            key.is_used = True
            key.used_at = timezone.now()
            key.used_by = user
            await sync_to_async(key.save)()

        return ActivationResult.SUCCESS, activated_list

    @sync_to_async
    def count_entitlements(self, user, filters):
        user_entitlements = self.filter(
            account=user,
            isGameEntitlement=False,
        )

        for filterName in filters:
            if filters[filterName] is None:
                continue

            filterValue = filters[filterName]

            match filterName:
                case "entitlementId":
                    user_entitlements = user_entitlements.filter(id=filterValue)
                case "entitlementTag":
                    user_entitlements = user_entitlements.filter(tag=filterValue)
                case "groupName":
                    user_entitlements = user_entitlements.filter(groupName=filterValue)
                case "productId":
                    user_entitlements = user_entitlements.filter(productId=filterValue)
                case "grantStartDate":
                    user_entitlements = user_entitlements.filter(
                        grantDate__gte=filterValue
                    )
                case "grantEndDate":
                    user_entitlements = user_entitlements.filter(
                        grantDate__lte=filterValue
                    )
                case "projectId":
                    user_entitlements = user_entitlements.filter(projectId=filterValue)

        return user_entitlements.count()

    @sync_to_async
    def add_entitlement(self, user, **kwargs):
        return self.create(account=user, **kwargs)


class PersonaManager(models.Manager):
    @sync_to_async
    def list_personas(self, account):
        personas_list = self.filter(account=account)
        return [persona.name for persona in personas_list]

    @sync_to_async
    def create_persona(self, account, name):
        # Check if persona name is already taken first
        if self.filter(account=account, name=name).exists():
            return False

        persona = self.model(account=account, name=name)
        persona.save()

        return True

    @sync_to_async
    def delete_persona(self, account, name):
        persona = self.filter(account=account, name=name).first()

        if persona is None:
            return False

        persona.delete()
        return True

    @sync_to_async
    def get_persona(self, account, name):
        return self.filter(account=account, name=name).first()

    @sync_to_async
    def get_persona_by_id(self, persona_id):
        persona = self.filter(id=persona_id).first()
        return {"name": persona.name, "id": persona.id, "type": 0}

    @sync_to_async
    def get_user_id_by_persona_id(self, pid):
        persona = self.filter(id=pid).first()
        return persona.account.id

    @sync_to_async
    def search_personas(self, account, name):
        filtered_personas = self.filter(name__search=name).exclude(account=account)
        return [
            {"name": owner.name, "id": owner.id, "type": 1}
            for owner in filtered_personas
        ]

    @sync_to_async
    def suggest_personas(self, account, keywords, max_results):
        filtered_personas = self.filter(name__icontains__in=keywords)[
            :max_results
        ].exclude(account=account)
        return [persona.name for persona in filtered_personas]

    @sync_to_async
    def get_user_info(self, name):
        persona = self.filter(name=name).first()

        if persona is None:
            return None

        return {
            "userName": persona.name,
            "namespace": "battlefield",
            "userId": persona.id,
            "masterUserId": persona.account.id,
        }


class AssocationManager(models.Manager):
    def __get_user_assocations(self, persona, type):
        usrAssocations, created = self.get_or_create(owner=persona, type=type)

        if created:
            usrAssocations.save()

        return usrAssocations

    @sync_to_async
    def get_user_assocations(self, persona, type):
        return self.__get_user_assocations(persona, type)

    @sync_to_async
    def get_user_assocations_count(self, persona, type):
        return self.__get_user_assocations(persona, type).associationmember_set.count()

    @sync_to_async
    def get_user_assocations_dict(self, persona, type):
        assocations = self.__get_user_assocations(
            persona, type
        ).associationmember_set.all()

        return [
            {
                "id": assocation.persona.id,
                "name": assocation.persona.name,
                "type": 1,
                "created": assocation.created_at,
                "modified": assocation.updated_at,
            }
            for assocation in assocations
        ]

    @sync_to_async
    def add_assocation(self, persona, type, target_id):
        from Plasma.models import Persona

        usrAssocations = self.__get_user_assocations(persona, type)

        try:
            target_persona = Persona.objects.get(id=target_id)
        except Persona.DoesNotExist:
            return None

        usrAssocations.members.add(target_persona)
        usrAssocations.save()

        assocation = usrAssocations.associationmember_set.get(persona=target_persona)

        return {
            "id": target_persona.id,
            "name": target_persona.name,
            "type": 1,
            "created": assocation.created_at.strftime("%b-%d-%Y %H:%M:%S UTC"),
            "modified": assocation.updated_at.strftime("%b-%d-%Y %H:%M:%S UTC"),
        }

    @sync_to_async
    def remove_assocation(self, persona, type, target_id):
        from Plasma.models import Persona

        usrAssocations = self.__get_user_assocations(persona, type)

        try:
            target_persona = Persona.objects.get(id=target_id)
        except Persona.DoesNotExist:
            return False

        targetAssocations = self.__get_user_assocations(target_persona, type)
        targetAssocations.members.remove(persona)

        assocation = usrAssocations.associationmember_set.get(persona=target_persona)

        usrAssocations.members.remove(target_persona)
        usrAssocations.save()

        return {
            "id": target_persona.id,
            "name": target_persona.name,
            "type": 1,
            "created": assocation.created_at.strftime("%b-%d-%Y %H:%M:%S UTC"),
            "modified": assocation.updated_at.strftime("%b-%d-%Y %H:%M:%S UTC"),
        }


class MessageManager(models.Manager):
    def __get_message_data(self, message_id, attachmentTypes=None):
        from Plasma.models import Attachment

        message_obj = self.get(id=message_id)

        attachments = []
        receivers = []

        for attachment in Attachment.objects.filter(message=message_obj):
            attachment_data = {
                "key": attachment.key,
                "type": attachment.type,
                "data": attachment.data,
            }

            if attachmentTypes is None or attachment.type in attachmentTypes:
                attachments.append(attachment_data)

        for receiver in message_obj.receivers.all():
            receiver_data = {"name": receiver.name, "id": receiver.id, "type": 1}

            receivers.append(receiver_data)

        message_data = {
            "attachments": attachments,
            "deliveryType": message_obj.delivery_type,
            "messageId": message_obj.id,
            "messageType": message_obj.message_type,
            "purgeStrategy": message_obj.purge_strategy,
            "from": {
                "name": message_obj.sender.name,
                "id": message_obj.sender.id,
                "type": 1,
            },
            "to": receivers,
            "timeSent": message_obj.created_at,
            "expiration": int(
                (message_obj.expires_at - timezone.now()).total_seconds()
            ),
        }

        return message_data

    @sync_to_async
    def send_message(self, persona, data):
        from Plasma.models import Attachment, Persona

        attachments_raw = data.Get("attachments")
        to = data.Get("to")

        if attachments_raw is None or to is None:
            return [], None

        receivers = []

        for receiver_id in to:
            try:
                receiver = Persona.objects.get(id=receiver_id)
                receivers.append(receiver)
            except Persona.DoesNotExist:
                return [], None

        expires_second = data.Get("expires")

        if expires_second is None:
            return [], None

        expiration_date = timezone.now() + timedelta(seconds=expires_second)

        deliveryType = data.Get("deliveryType")
        messageType = data.Get("messageType")
        purgeStrategy = data.Get("purgeStrategy")

        message = self.create(
            sender=persona,
            delivery_type=deliveryType,
            message_type=messageType,
            purge_strategy=purgeStrategy,
            expires_at=expiration_date,
        )

        attachments = []

        for attachment in attachments_raw:
            attachment_obj = Attachment.objects.create(
                message=message,
                key=attachment.get("key"),
                type=attachment.get("type"),
                data=attachment.get("data"),
            )

            attachments.append(attachment_obj)

        message.receivers.add(*receivers)
        message.save()

        return receivers, message.id

    @sync_to_async
    def get_messages(self, persona, attachmentTypes):
        message_objects = self.filter(
            receivers__id=persona.id, expires_at__gte=timezone.now()
        )
        message_list = []

        for message_obj in message_objects:
            message_data = self.__get_message_data(message_obj.id)
            message_list.append(message_data)

        return message_list

    @sync_to_async
    def get_message(self, message_id):
        return self.__get_message_data(message_id)

    @sync_to_async
    def get_sender_id_from_message(self, message):
        return message.sender.id

    @sync_to_async
    def delete_message(self, message_id):
        self.get(id=message_id).delete()


class RankingManager(models.Manager):
    @sync_to_async
    def get_stat(self, persona, key):
        from Plasma.models import Ranking

        try:
            return self.get(persona=persona, key=key).value
        except Ranking.DoesNotExist:
            return 0.0

    @sync_to_async
    def get_stat_by_id(self, persona_id, key):
        from Plasma.models import Ranking

        try:
            return self.get(persona__id=persona_id, key=key).value
        except Ranking.DoesNotExist:
            return 0.0

    @sync_to_async
    def get_ranked_stat(self, persona, key):
        from Plasma.models import Ranking

        filtered = self.filter(key=key)
        ranked = filtered.annotate(
            rank=Window(expression=RowNumber(), order_by=F("value").desc())
        )

        try:
            stat = ranked.get(persona=persona)
        except Ranking.DoesNotExist:
            return 0.0, 250001

        return stat.value, stat.rank

    @sync_to_async
    def get_ranked_stat_by_id(self, persona_id, key):
        from Plasma.models import Ranking

        filtered = self.filter(key=key)
        ranked = filtered.annotate(
            rank=Window(expression=RowNumber(), order_by=F("value").desc())
        )

        try:
            stat = ranked.get(persona__id=persona_id)
        except Ranking.DoesNotExist:
            return 0.0, 250001

        return stat.value, stat.rank

    @sync_to_async
    def get_leaderboard_users(self, baseKey, minRank, maxRank, excludePersona=None):
        filtered = self.filter(key=baseKey).exclude(persona=excludePersona)
        ranked = filtered.annotate(
            rank=Window(expression=RowNumber(), order_by=F("value").desc())
        )

        ranked_personas = ranked[minRank - 1 : maxRank + 1]
        personas = []

        for stat in ranked_personas:
            personas.append(
                {
                    "owner": stat.persona.id,
                    "name": stat.persona.name,
                    "rank": stat.rank,
                }
            )

        return personas

    @sync_to_async
    def update_stat(self, personaId, key, value):
        from Plasma.models import Persona

        persona = Persona.objects.get(id=personaId)
        self.update_or_create(persona=persona, key=key, value=value)


class RecordManager(models.Manager):
    @sync_to_async
    def add_records(self, persona, name, key, value):
        self.create(persona=persona, name=name, key=key, value=value)

    @sync_to_async
    def update_records(self, persona, name, key, value):
        record = self.get(persona=persona, name=name, key=key)
        record.value = value
        record.save()

    @sync_to_async
    def get_records(self, persona, name):
        records = self.filter(persona=persona, name=name).order_by("-updated_at")

        return [
            {
                "key": record.key,
                "value": record.value,
                "updated_at": record.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            }
            for record in records
        ]
