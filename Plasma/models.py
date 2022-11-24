from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from Plasma.managers import UserManager


# Create your models here.
class Account(AbstractBaseUser, PermissionsMixin):

    nuid = models.EmailField(max_length=32, unique=True, verbose_name="Email Address")

    globalOptin = models.BooleanField(
        default=False,
        verbose_name="Global Opt-In",
        help_text="Send emails about EA games, products, news and events to this user.",
    )

    thirdPartyOptin = models.BooleanField(
        default=False,
        verbose_name="Third Party Opt-In",
        help_text="Allow to share information about this user to selected EA Partners.",
    )

    parentalEmail = models.EmailField(
        null=True,
        verbose_name="Parental Email Address",
        help_text="Email address of the parent or guardian of this user.",
    )

    dateOfBirth = models.DateField(null=True, verbose_name="Date of Birth")

    firstName = models.CharField(
        max_length=32,
        null=True,
        verbose_name="First Name",
    )

    lastName = models.CharField(
        max_length=32,
        null=True,
        verbose_name="Last Name",
    )

    gender = models.CharField(
        max_length=1,
        null=True,
        verbose_name="Gender",
        help_text="Gender of this user ([F]emale or [M]ale).",
    )

    address = models.CharField(
        max_length=255,
        null=True,
        verbose_name="Address Line 1",
    )

    address2 = models.CharField(
        max_length=255,
        null=True,
        verbose_name="Address Line 2",
    )

    city = models.CharField(max_length=255, null=True, verbose_name="City")

    state = models.CharField(max_length=255, null=True, verbose_name="State")

    zipCode = models.CharField(
        max_length=5,
        null=True,
        verbose_name="Zip/Postal Code",
    )

    country = models.CharField(
        max_length=3,
        null=True,
        verbose_name="Country",
        help_text="ISO Code of user's country.",
    )

    language = models.CharField(
        max_length=2,
        null=True,
        verbose_name="Language",
        help_text="Language of this user.",
    )

    tosVersion = models.CharField(
        max_length=255,
        null=True,
        verbose_name="Terms of Service Version",
        help_text="Version of the Terms of Service accepted by this user.",
    )

    isServerAccount = models.BooleanField(
        default=False,
        verbose_name="Server Account",
        help_text="Is this account a server account?",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "nuid"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_staff(self):
        return self.is_superuser

    def __str__(self):
        return self.nuid

    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        ordering = ("id",)
