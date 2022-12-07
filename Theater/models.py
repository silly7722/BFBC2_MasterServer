from django.db import models

from Plasma.enumerators.ClientLocale import ClientLocale


# Create your models here.
class Lobby(models.Model):
    name = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Lobby Name",
        help_text="Name of the lobby",
    )
    locale = models.CharField(
        max_length=5,
        verbose_name="Locale",
        help_text="Locale of the lobby",
        choices=ClientLocale.choices,
    )
    maxGames = models.IntegerField(
        default=10000,
        verbose_name="Max Games",
        help_text="Maximum number of games in the lobby",
    )
