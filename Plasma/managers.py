from datetime import datetime

from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import BaseUserManager
from django.db import models


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

    @sync_to_async
    def create_superuser(self, nuid, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(nuid, password, **extra_fields)

    @sync_to_async
    def user_exists(self, nuid):
        return self.filter(nuid=nuid).exists()

    @sync_to_async
    def accept_tos(self, user, tos_version):
        user.tosVersion = tos_version
        user.save()


class EntitlementManager(models.Manager):
    @sync_to_async
    def is_entitled_for_game(self, user, game_id):
        return self.filter(
            account=user,
            tag=game_id,
            grantDate__gte=datetime.now(),
            terminationDate__lte=datetime.now(),
            status="ACTIVE",
            isGameEntitlement=True,
        ).exists()
