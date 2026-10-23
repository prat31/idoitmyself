import os

from cryptography.fernet import Fernet

# Unit tests must not need real infrastructure or secrets: provide harmless defaults.
for key, value in {
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test",
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/v1/email/gmail/callback",
    "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
}.items():
    os.environ.setdefault(key, value)
