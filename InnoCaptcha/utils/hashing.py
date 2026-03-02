"""
captcha_lib.utils.hashing
~~~~~~~~~~~~~~~~~~~~~~~~~~
HMAC-based signing, verification, and secure answer hashing.

These utilities underpin the token-based validation system.  All
operations use the standard-library ``hmac`` and ``hashlib`` modules;
no third-party cryptography dependencies are required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Secret key management
# ---------------------------------------------------------------------------


def generate_secret_key(nbytes: int = 32) -> str:
    """Generate a cryptographically-random hex secret key.

    Args:
        nbytes: Number of random bytes (default 32 → 64 hex chars).

    Returns:
        A URL-safe hex string suitable for use as an HMAC key.
    """
    return secrets.token_hex(nbytes)


# ---------------------------------------------------------------------------
# HMAC signing & verification
# ---------------------------------------------------------------------------


def hmac_sign(data: str, key: str, algorithm: str = "sha256") -> str:
    """Produce an HMAC signature for *data* using *key*.

    Args:
        data:      The payload string to sign.
        key:       The secret key (hex or arbitrary string).
        algorithm: Hash algorithm name (default ``"sha256"``).

    Returns:
        Lowercase hex HMAC digest string.
    """
    mac = hmac.new(
        key.encode("utf-8"),
        data.encode("utf-8"),
        digestmod=algorithm,
    )
    return mac.hexdigest()


def hmac_verify(data: str, signature: str, key: str, algorithm: str = "sha256") -> bool:
    """Verify that *signature* matches the HMAC of *data* with *key*.

    Uses :func:`hmac.compare_digest` to prevent timing attacks.

    Args:
        data:      Original payload string.
        signature: Expected HMAC hex digest.
        key:       Secret key used during signing.
        algorithm: Hash algorithm (must match signing call).

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    expected = hmac_sign(data, key, algorithm)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Answer hashing
# ---------------------------------------------------------------------------


def hash_answer(answer: str, case_sensitive: bool = False) -> str:
    """Hash a captcha answer for safe storage and comparison.

    Args:
        answer:         Raw user or generated answer string.
        case_sensitive: If ``False`` (default), converts to lower-case first.

    Returns:
        Hex SHA-256 digest of the (normalised) answer.
    """
    normalised = answer if case_sensitive else answer.lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def answers_match(user_answer: str, stored_hash: str, case_sensitive: bool = False) -> bool:
    """Compare a user-supplied answer against a stored hash.

    Args:
        user_answer:    Raw string typed by the user.
        stored_hash:    SHA-256 hex digest produced by :func:`hash_answer`.
        case_sensitive: Must match the value used when hashing.

    Returns:
        ``True`` if the answer matches.
    """
    candidate_hash = hash_answer(user_answer, case_sensitive)
    return hmac.compare_digest(candidate_hash, stored_hash)


# ---------------------------------------------------------------------------
# Token building / parsing
# ---------------------------------------------------------------------------


def build_token_payload(
    answer_hash: str,
    expires_at: float,
    captcha_id: str,
    extra: Dict[str, Any] | None = None,
) -> str:
    """Serialise a token payload to a canonical JSON string.

    The string is deterministic so that HMAC signatures are reproducible.

    Args:
        answer_hash: SHA-256 hash of the correct answer.
        expires_at:  Unix timestamp at which the token expires.
        captcha_id:  Unique ID for this captcha instance.
        extra:       Optional additional fields (must be JSON-serialisable).

    Returns:
        Compact JSON string with sorted keys.
    """
    payload: Dict[str, Any] = {
        "answer_hash": answer_hash,
        "captcha_id": captcha_id,
        "expires_at": expires_at,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def create_signed_token(
    answer_hash: str,
    captcha_id: str,
    secret_key: str,
    expiry_seconds: int = 300,
) -> str:
    """Create a compact signed token encoding the answer hash and expiry.

    Token format::

        <base64url(payload_json)>.<hmac_hex>

    Args:
        answer_hash:    SHA-256 hash of the correct answer.
        captcha_id:     Unique captcha instance ID.
        secret_key:     HMAC secret key.
        expiry_seconds: Token validity window in seconds.

    Returns:
        A ``"payload.signature"`` token string.
    """
    import base64

    expires_at = time.time() + expiry_seconds
    payload_json = build_token_payload(answer_hash, expires_at, captcha_id)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    signature = hmac_sign(payload_b64, secret_key)
    return f"{payload_b64}.{signature}"


def decode_signed_token(
    token: str,
    secret_key: str,
) -> Dict[str, Any]:
    """Decode and verify a signed token produced by :func:`create_signed_token`.

    Args:
        token:      The token string to decode.
        secret_key: HMAC secret key (must match the one used during creation).

    Returns:
        The decoded payload dictionary.

    Raises:
        ValueError: If the token is malformed or the signature is invalid.
        KeyError:   If required payload fields are missing.
    """
    import base64

    try:
        payload_b64, signature = token.rsplit(".", 1)
    except ValueError:
        raise ValueError("Malformed token: expected '<payload>.<signature>' format.")

    if not hmac_verify(payload_b64, signature, secret_key):
        raise ValueError("Token signature verification failed.")

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload: Dict[str, Any] = json.loads(payload_json)
    except Exception as exc:
        raise ValueError(f"Failed to decode token payload: {exc}") from exc

    return payload
