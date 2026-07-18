"""Password, JWT and AES helpers."""
from __future__ import annotations
import os
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets as _secrets

JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def _get_aes_key() -> bytes:
    raw = os.environ.get("NFC_AES_KEY", "frota_nfc_default_aes_key_32byte!")
    # Derive a 32-byte key deterministically
    return hashlib.sha256(raw.encode("utf-8")).digest()


# ---------------- Password ----------------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------- JWT ----------------
def create_access_token(user_id: str, email: str, role: str, hours: int = 12) -> str:
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])


# ---------------- AES-GCM ----------------
def aes_encrypt(plaintext: str) -> str:
    """AES-256-GCM encrypt. Output = base64(iv || ciphertext || tag)."""
    key = _get_aes_key()
    iv = _secrets.token_bytes(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    enc = cipher.encryptor()
    ct = enc.update(plaintext.encode("utf-8")) + enc.finalize()
    return base64.b64encode(iv + ct + enc.tag).decode("utf-8")


def aes_decrypt(token: str) -> str:
    """AES-256-GCM decrypt."""
    key = _get_aes_key()
    raw = base64.b64decode(token)
    iv, ct, tag = raw[:12], raw[12:-16], raw[-16:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    dec = cipher.decryptor()
    pt = dec.update(ct) + dec.finalize()
    return pt.decode("utf-8")


def generate_nfc_card_number() -> str:
    """Generate a random 12-char hex card number (unique enough for demo)."""
    return _secrets.token_hex(6).upper()


def generate_nfc_token(target_id: str, card_number: str) -> str:
    """Generate the encrypted token that would be written to the NFC card."""
    payload = f"{target_id}:{card_number}:{_secrets.token_hex(8)}"
    return aes_encrypt(payload)
