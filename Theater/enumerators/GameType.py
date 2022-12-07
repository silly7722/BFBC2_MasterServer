from django.db.models import TextChoices


class GameType(TextChoices):
    GAME = "G"
    PLAYGROUP = "P"
