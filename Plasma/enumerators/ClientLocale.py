from django.db.models import TextChoices


class ClientLocale(TextChoices):
    English = "en_US"
    French = "fr_FR"
    German = "de"
    Spanish = "es"
    Italian = "it"
    Japanese = "ja"
    Russian = "ru"
    Polish = "pl"
