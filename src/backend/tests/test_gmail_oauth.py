import base64
import hashlib

from app.services.gmail_oauth import _code_challenge


def test_code_challenge_is_s256_base64url_without_padding():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert _code_challenge(verifier) == expected
    assert "=" not in _code_challenge(verifier)
