from django.db.models import TextChoices


class JoinMode(TextChoices):
    CLOSED = "C"
    WAIT = "W"
    OPEN = "O"
