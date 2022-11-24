from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from Plasma.models import Account

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


admin.site.register(Account, AccountAdmin)
