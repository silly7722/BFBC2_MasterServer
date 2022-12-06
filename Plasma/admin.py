from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from Plasma.models import (
    Account,
    Assocation,
    Attachment,
    Entitlement,
    Message,
    Persona,
    Ranking,
    SerialKey,
)

# Register your models here.


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    class Meta:
        model = Account
        fields = ("nuid",)

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = Account
        fields = ("nuid",)


class AccountAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm

    add_fieldsets = (
        (
            "Login Information",
            {
                "fields": (
                    "nuid",
                    "password",
                )
            },
        ),
    )

    fieldsets = (
        (
            "Login Information",
            {
                "fields": (
                    "nuid",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "firstName",
                    "lastName",
                    "gender",
                    "dateOfBirth",
                    "parentalEmail",
                    "address",
                    "address2",
                    "city",
                    "state",
                    "zipCode",
                    "country",
                    "language",
                )
            },
        ),
        (
            "Email Opt-Ins",
            {
                "fields": (
                    "globalOptin",
                    "thirdPartyOptin",
                )
            },
        ),
        (
            "Miscellaneous",
            {
                "fields": (
                    "tosVersion",
                    "isServerAccount",
                )
            },
        ),
    )

    ordering = ("id",)
    list_display = ["id", "nuid", "created_at", "updated_at", "last_login", "is_staff"]
    list_filter = ("nuid",)


class EntitlementAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "account",
        "tag",
        "groupName",
        "productId",
        "grantDate",
        "terminationDate",
        "version",
        "isGameEntitlement",
    ]
    list_filter = (
        "account",
        "tag",
        "groupName",
        "productId",
        "grantDate",
        "terminationDate",
        "isGameEntitlement",
    )


class SerialKeyAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "key",
        "is_used",
        "is_permanent",
        "created_at",
        "updated_at",
        "used_at",
        "used_by",
    ]
    list_filter = ("key", "is_used", "is_permanent")


class PersonaAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "name", "created_at"]
    list_filter = (
        "account",
        "name",
    )


class AssocationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "owner",
        "type",
        "assocations",
    ]
    list_filter = (
        "owner",
        "type",
    )

    def assocations(self, obj):
        return [",".join([str(member) for member in obj.associationmember_set.all()])]


class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "sender",
        "delivery_type",
        "message_type",
        "purge_strategy",
    ]
    list_filter = (
        "sender",
        "receivers",
        "delivery_type",
        "message_type",
        "purge_strategy",
    )


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "key", "type", "data"]
    list_filter = (
        "key",
        "type",
    )


class RankingAdmin(admin.ModelAdmin):
    list_display = ["id", "persona", "key", "value"]
    list_filter = ("persona", "key")


admin.site.register(Account, AccountAdmin)
admin.site.register(Entitlement, EntitlementAdmin)
admin.site.register(SerialKey, SerialKeyAdmin)
admin.site.register(Persona, PersonaAdmin)
admin.site.register(Assocation, AssocationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(Ranking, RankingAdmin)
