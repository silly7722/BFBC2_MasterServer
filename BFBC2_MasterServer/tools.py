import binascii
import os
from typing import MutableMapping


def flatten(d, parent_key="", sep="."):
    items = []

    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k

        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def legacy_b64encode(s, altchars=None):
    """Encode the bytes-like object s using Base64 and return a bytes object.
    Optional altchars should be a byte string of length 2 which specifies an
    alternative alphabet for the '+' and '/' characters.  This allows an
    application to e.g. generate url or filesystem safe Base64 strings.
    """
    encoded = binascii.b2a_base64(s.encode(), newline=False)
    if altchars is not None:
        assert len(altchars) == 2, repr(altchars)
        return encoded.translate(bytes.maketrans(b"+/", altchars))
    return encoded


def __get_config(key, keystore, default):
    config_path = f"/run/{keystore}/{key.lower()}"

    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    return os.getenv(key, default)


def get_config(key, default=None):
    return __get_config(key, "configs", default)


def get_secrets(key, default=None):
    return __get_config(key, "secrets", default)
