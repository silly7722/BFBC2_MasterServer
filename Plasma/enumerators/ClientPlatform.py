from django.db.models import TextChoices


class ClientPlatform(TextChoices):
    XBOX360 = "xenon"
    PS3 = "ps3"
    PC = "PC"
