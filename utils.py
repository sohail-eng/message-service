"""Utility helpers for API key generation and hashing."""

import hashlib
import secrets


API_KEY_PREFIX = "wa_live_"


def generate_api_key() -> str:
    """Generate a secure random API key with the wa_live_ prefix."""
    # token_urlsafe(32) yields ~43 characters of high-entropy random data.
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Return a SHA-256 hex digest of the API key (never store the raw key)."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
