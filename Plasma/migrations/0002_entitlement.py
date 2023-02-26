# Generated by Django 4.1.3 on 2022-11-25 18:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Plasma", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Entitlement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tag",
                    models.CharField(max_length=255, verbose_name="Entitlement Tag"),
                ),
                (
                    "grantDate",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Date when this entitlement was (or will be) granted.",
                        verbose_name="Grant Date",
                    ),
                ),
                (
                    "terminationDate",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date when this entitlement will be terminated.",
                        null=True,
                        verbose_name="Termination Date",
                    ),
                ),
                (
                    "groupName",
                    models.CharField(
                        blank=True,
                        help_text="Name of the group this entitlement grants access to.",
                        max_length=255,
                        null=True,
                        verbose_name="Group Name",
                    ),
                ),
                (
                    "productId",
                    models.CharField(
                        blank=True,
                        help_text="ID of the product this entitlement grants access to.",
                        max_length=255,
                        null=True,
                        verbose_name="Product ID",
                    ),
                ),
                (
                    "version",
                    models.IntegerField(
                        default=0,
                        help_text="Version of the entitlement.",
                        verbose_name="Version",
                    ),
                ),
                (
                    "isGameEntitlement",
                    models.BooleanField(
                        default=False,
                        help_text="Is this entitlement a game entitlement?",
                        verbose_name="Game Entitlement",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Entitlement",
                "verbose_name_plural": "Entitlements",
                "ordering": ("id",),
            },
        ),
    ]
