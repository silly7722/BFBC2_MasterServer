# Generated by Django 4.1.3 on 2022-12-06 11:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Plasma", "0006_message_attachment"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ranking",
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
                        help_text="Key of the ranking.",
                        max_length=255,
                        verbose_name="Key",
                    ),
                ),
                (
                    "value",
                    models.FloatField(
                        help_text="Value of the ranking.", verbose_name="Value"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "persona",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="Plasma.persona"
                    ),
                ),
            ],
        ),
    ]
