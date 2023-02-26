# Generated by Django 4.1.3 on 2022-11-27 19:38

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Plasma", "0002_entitlement"),
    ]

    operations = [
        migrations.CreateModel(
            name="SerialKey",
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
                    "key",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Serial Key"
                    ),
                ),
                (
                    "targets",
                    models.TextField(
                        help_text="What this key activates. (Semicolon seperated)",
                        verbose_name="Targets",
                    ),
                ),
                (
                    "is_used",
                    models.BooleanField(
                        default=False,
                        help_text="Is this key already used?",
                        verbose_name="Is Used",
                    ),
                ),
                (
                    "is_permanent",
                    models.BooleanField(
                        default=False,
                        help_text="Is this key permanent? (Will not expire after usage)",
                        verbose_name="Is Permanent",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "used_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Serial Key",
                "verbose_name_plural": "Serial Keys",
                "ordering": ("id",),
            },
        ),
    ]
