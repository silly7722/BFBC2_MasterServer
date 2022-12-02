from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from Plasma.managers import (
    AssocationManager,
    EntitlementManager,
    PersonaManager,
    UserManager,
)


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


class Entitlement(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    tag = models.CharField(max_length=255, verbose_name="Entitlement Tag")

    grantDate = models.DateTimeField(
        verbose_name="Grant Date",
        help_text="Date when this entitlement was (or will be) granted.",
        auto_now_add=True,
    )
    terminationDate = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Termination Date",
        help_text="Date when this entitlement will be terminated.",
    )

    groupName = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Group Name",
        help_text="Name of the group this entitlement grants access to.",
    )
    productId = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Product ID",
        help_text="ID of the product this entitlement grants access to.",
    )

    version = models.IntegerField(
        default=0, verbose_name="Version", help_text="Version of the entitlement."
    )

    isGameEntitlement = models.BooleanField(
        default=False,
        verbose_name="Game Entitlement",
        help_text="Is this entitlement a game entitlement?",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = EntitlementManager()

    def __str__(self):
        return f"{self.account} - {self.tag}"

    class Meta:
        verbose_name = "Entitlement"
        verbose_name_plural = "Entitlements"
        ordering = ("id",)


class SerialKey(models.Model):
    key = models.CharField(max_length=255, verbose_name="Serial Key", unique=True)
    targets = models.TextField(
        verbose_name="Targets",
        help_text="What this key activates. (Semicolon seperated)",
    )

    is_used = models.BooleanField(
        default=False, verbose_name="Is Used", help_text="Is this key already used?"
    )
    is_permanent = models.BooleanField(
        default=False,
        verbose_name="Is Permanent",
        help_text="Is this key permanent? (Will not expire after usage)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "Serial Key"
        verbose_name_plural = "Serial Keys"
        ordering = ("id",)


class Persona(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=16, verbose_name="Soldier Name", unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = PersonaManager()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ("id",)


class AssociationType(models.IntegerChoices):
    UNKNOWN = 0
    MUTE = 1
    BLOCK = 2
    FRIENDS = 3
    RECENT_PLAYERS = 4


class Assocation(models.Model):
    owner = models.ForeignKey(Persona, on_delete=models.CASCADE)

    type = models.IntegerField(default=0, choices=AssociationType.choices)
    members = models.ManyToManyField(
        Persona, related_name="association_members", through="AssociationMember"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AssocationManager()

    class Meta:
        verbose_name = "Association"
        verbose_name_plural = "Associations"
        ordering = ("id",)


class AssociationMember(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    target = models.ForeignKey(Assocation, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
