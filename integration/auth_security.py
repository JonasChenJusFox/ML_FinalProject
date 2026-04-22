"""
integration/auth_security.py

Shared helpers for hashing and verifying passwords and one-time codes.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16


def hash_secret(
    secret: str,
    *,
    salt_hex: str | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations,
    )
    return digest.hex(), salt.hex()


def verify_secret(
    secret: str,
    expected_hash: str,
    salt_hex: str,
    *,
    iterations: int = PBKDF2_ITERATIONS,
) -> bool:
    actual_hash, _ = hash_secret(secret, salt_hex=salt_hex, iterations=iterations)
    return hmac.compare_digest(actual_hash, expected_hash)
