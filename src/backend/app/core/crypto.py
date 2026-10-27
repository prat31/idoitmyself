from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().token_encryption_key.get_secret_value().encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def encrypt_bytes(plaintext: bytes) -> str:
    return _fernet().encrypt(plaintext).decode()


def decrypt_bytes(ciphertext: str) -> bytes:
    return _fernet().decrypt(ciphertext.encode())
