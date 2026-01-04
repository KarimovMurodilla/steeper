import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.main.config import config


def _get_fernet() -> Fernet:
    """
    Generates a Fernet key based on the application's secret key.
    This makes encryption deterministic for the same SECRET_KEY.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=config.app.ENCRYPTION_LENGTH,
        salt=config.app.ENCRYPTION_SALT.encode(),
        iterations=config.app.ENCRYPTION_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(config.app.PROJECT_SECRET_KEY.encode()))
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """Encrypts the token for storage in the database."""
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypts the token for use in API calls."""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()
