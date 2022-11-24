from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
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

        return self.create_user(nuid, password, **extra_fields)

    def user_exists(self, nuid):
        return self.filter(nuid=nuid).exists()
