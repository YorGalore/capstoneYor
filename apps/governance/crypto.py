"""Symmetric encryption for secrets stored in the database (Runtime Settings and
Apify tokens). The key is derived from Django's SECRET_KEY so no separate key
material is required for the demo; a production deployment should back this with
a dedicated secrets manager (SRS §8.4).
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext):
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token):
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def mask(value, visible=4):
    """Return a masked representation revealing only the last ``visible`` chars."""
    if not value:
        return ""
    if len(value) <= visible:
        return "•" * len(value)
    return "•" * 8 + value[-visible:]
