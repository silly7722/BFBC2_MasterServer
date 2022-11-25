from enum import Enum


class ActivationResult(Enum):
    SUCCESS = 0
    ALREADY_USED = 1  # Key has already been used
    INVALID_KEY = 2  # Key is invalid
