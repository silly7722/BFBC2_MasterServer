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

    async def activate_game(self, user, key):
        from Plasma.models import SerialKey

        valid_keys = await sync_to_async(SerialKey.objects.filter)(
            key=key, is_game_key=True
        )
        game_targets = []

        if await sync_to_async(valid_keys.exists)():
            key = await sync_to_async(SerialKey.objects.get)(key=key)
            game_targets = key.targets.split(";")
        else:
            return ActivationResult.INVALID_KEY

        if key.is_used:
            return ActivationResult.ALREADY_USED

        for game in game_targets:
            if await self.is_entitled_for_game(user, game):
                continue

            await sync_to_async(self.create)(
                account=user,
                tag=game,
                grantDate=timezone.now(),
                isGameEntitlement=True,
            )

        if not key.is_permanent:
            key.is_used = True
            key.used_at = timezone.now()
            key.used_by = user
            await sync_to_async(key.save)()

        return ActivationResult.SUCCESS
