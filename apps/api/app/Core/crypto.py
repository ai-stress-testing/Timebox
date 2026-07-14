"""All cryptography lives here — no inline crypto anywhere else.

Key hierarchy (constitution Article I):
  key file secret (user-held, 32 bytes)
    ├── verifier  = HMAC-SHA256(secret, "timebox-verifier-v1")   → persisted
    └── data key  = HKDF-SHA256(secret, info="timebox-data-v1")  → session memory only

Field encryption: AES-256-GCM, random 96-bit nonce, payload "v1:<b64 nonce>:<b64 ct>".
"""
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_VERIFIER_CONTEXT = b"timebox-verifier-v1"
_DATA_KEY_INFO = b"timebox-data-v1"
_FIELD_VERSION = "v1"
SECRET_BYTES = 32


class FieldDecryptError(Exception):
    """Raised when an encrypted field cannot be authenticated/decoded."""


def generate_secret() -> str:
    return base64.urlsafe_b64encode(os.urandom(SECRET_BYTES)).decode()


def decode_secret(secret_b64: str) -> bytes:
    raw = base64.urlsafe_b64decode(secret_b64.encode())
    if len(raw) != SECRET_BYTES:
        raise ValueError("secret must decode to exactly 32 bytes")
    return raw


def compute_verifier(secret: bytes) -> str:
    return hmac.new(secret, _VERIFIER_CONTEXT, hashlib.sha256).hexdigest()


def verifier_matches(secret: bytes, stored_verifier: str) -> bool:
    candidate = compute_verifier(secret)
    return hmac.compare_digest(candidate, stored_verifier)


def derive_data_key(secret: bytes) -> bytes:
    kdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_DATA_KEY_INFO)
    return kdf.derive(secret)


def encrypt_field(data_key: bytes, plaintext: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode(), None)
    nonce_b64 = base64.b64encode(nonce).decode()
    ct_b64 = base64.b64encode(ciphertext).decode()
    return f"{_FIELD_VERSION}:{nonce_b64}:{ct_b64}"


def decrypt_field(data_key: bytes, payload: str) -> str:
    try:
        version, nonce_b64, ct_b64 = payload.split(":", 2)
        if version != _FIELD_VERSION:
            raise FieldDecryptError(f"unknown field version {version}")
        nonce = base64.b64decode(nonce_b64)
        plaintext = AESGCM(data_key).decrypt(nonce, base64.b64decode(ct_b64), None)
        return plaintext.decode()
    except FieldDecryptError:
        raise
    except Exception as exc:
        raise FieldDecryptError("field decryption failed") from exc


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
