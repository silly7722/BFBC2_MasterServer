import json
from base64 import b64decode

from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
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
    def list_entitlements(self, user, groupName):
        filtered_entitlements = self.filter(
            account=user,
            groupName=groupName,
            grantDate__lt=timezone.now(),
            isGameEntitlement=False,
        )

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

    async def activate_key(self, user, key):
        from Plasma.models import SerialKey

        valid_key = await sync_to_async(SerialKey.objects.filter)(key=key)

        if not await sync_to_async(valid_key.exists)():
            return ActivationResult.INVALID_KEY, []

        key = await sync_to_async(SerialKey.objects.get)(key=key)

        if key.is_used:
            return ActivationResult.ALREADY_USED, []

        encoded_targets = key.targets.split(";")
        activated_list = []

        for target in encoded_targets:
            decoded_target = b64decode(target).decode("utf-8")
            target = json.loads(decoded_target)

            current_entitlements = await self.list_entitlements(
                user, target.get("group")
            )
            already_entitled = False

            for entitlement in current_entitlements:
                if entitlement["entitlementTag"] == target.get("tag"):
                    already_entitled = True
                    break

            if already_entitled:
                continue

            terminationDate = target.get("terminateAfter")

            if terminationDate:
                terminationDate = timezone.now() + timezone.timedelta(
                    seconds=terminationDate
                )

            activated_entitlement = await sync_to_async(self.create)(
                account=user,
                tag=target.get("tag"),
                groupName=target.get("group"),
                productId=target.get("product"),
                grantDate=timezone.now(),
                terminationDate=terminationDate,
                isGameEntitlement=target.get("game", False),
            )

            activated_list.append(activated_entitlement)

        return ActivationResult.SUCCESS, activated_entitlement

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
    def search_personas(self, account, name):
        name = name.replace("_*", "")
        filtered_personas = self.filter(name__icontains=name).exclude(account=account)
        return [
            {"name": owner.name, "id": owner.id, "type": 1}
            for owner in filtered_personas
        ]
