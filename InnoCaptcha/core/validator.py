"""
captcha_lib.core.validator
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Token creation and validation for secure CAPTCHA verification.

The :class:`TokenValidator` signs answer hashes with HMAC-SHA256, enforces
expiry windows, tracks attempt counts, and prevents replay attacks by
invalidating tokens after successful verification.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Dict, Optional

from ..core.exceptions import (
    CaptchaAlreadyUsedError,
    CaptchaExpiredError,
    CaptchaInvalidError,
    CaptchaMaxAttemptsError,
)
from ..utils.hashing import (
    answers_match,
    create_signed_token,
    decode_signed_token,
    generate_secret_key,
    hash_answer,
)

logger = logging.getLogger(__name__)


class TokenValidator:
    """Creates and validates HMAC-signed CAPTCHA tokens.

    The token encodes:
    - The SHA-256 hash of the correct answer
    - An expiry timestamp
    - A unique captcha ID

    Once issued, the validator can verify a user's answer without storing
    the plaintext answer anywhere.

    Args:
        secret_key:     HMAC key (auto-generated if ``None``).
        expiry_seconds: Token validity window in seconds.
        max_attempts:   Maximum allowed verification attempts.
        case_sensitive: Whether answer comparison is case-sensitive.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        expiry_seconds: int = 300,
        max_attempts: int = 3,
        case_sensitive: bool = False,
    ) -> None:
        self._secret_key:     str  = secret_key or generate_secret_key()
        self._expiry_seconds: int  = expiry_seconds
        self._max_attempts:   int  = max_attempts
        self._case_sensitive: bool = case_sensitive

        # Replay protection: set of invalidated token IDs
        self._used_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Token creation
    # ------------------------------------------------------------------

    def issue_token(self, answer: str, captcha_id: Optional[str] = None) -> str:
        """Create a signed token for the given *answer*.

        Args:
            answer:     The correct CAPTCHA answer (plaintext).
            captcha_id: Unique ID; auto-generated as a 16-char hex string if omitted.

        Returns:
            A ``"<payload_b64>.<hmac_signature>"`` token string.
        """
        captcha_id = captcha_id or secrets.token_hex(16)
        answer_hash = hash_answer(answer, self._case_sensitive)
        token = create_signed_token(
            answer_hash=answer_hash,
            captcha_id=captcha_id,
            secret_key=self._secret_key,
            expiry_seconds=self._expiry_seconds,
        )
        logger.debug("Issued token for captcha_id=%s", captcha_id)
        return token

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    def validate(
        self,
        token: str,
        user_answer: str,
        attempt_counter: Optional[Dict[str, int]] = None,
    ) -> bool:
        """Verify *user_answer* against the signed *token*.

        Args:
            token:           The token string previously issued by :meth:`issue_token`.
            user_answer:     Raw answer string supplied by the user.
            attempt_counter: Optional mutable dict ``{captcha_id: int}`` used to
                             track attempt counts externally.  If ``None``, replay
                             protection within this validator instance is used.

        Returns:
            ``True`` if the answer is correct and the token is valid.

        Raises:
            CaptchaInvalidError:     If the signature or format is bad.
            CaptchaExpiredError:     If the token has passed its expiry.
            CaptchaMaxAttemptsError: If attempt limit is exceeded.
            CaptchaAlreadyUsedError: If the token was already successfully verified.
        """
        # --- Decode & verify signature ---
        try:
            payload: Dict[str, Any] = decode_signed_token(token, self._secret_key)
        except ValueError as exc:
            logger.warning("Token decode failed: %s", exc)
            raise CaptchaInvalidError(f"Token is invalid: {exc}") from exc

        captcha_id: str  = payload["captcha_id"]
        answer_hash: str = payload["answer_hash"]
        expires_at: float = float(payload["expires_at"])

        # --- Replay attack prevention ---
        if captcha_id in self._used_ids:
            raise CaptchaAlreadyUsedError()

        # --- Expiry check ---
        if time.time() > expires_at:
            logger.info("Token expired for captcha_id=%s", captcha_id)
            raise CaptchaExpiredError()

        # --- Attempt count ---
        if attempt_counter is not None:
            count = attempt_counter.get(captcha_id, 0) + 1
            attempt_counter[captcha_id] = count
            if count > self._max_attempts:
                raise CaptchaMaxAttemptsError(self._max_attempts)

        # --- Answer comparison ---
        if answers_match(user_answer, answer_hash, self._case_sensitive):
            self._used_ids.add(captcha_id)
            logger.info("Captcha verified successfully: captcha_id=%s", captcha_id)
            return True

        logger.debug("Incorrect answer for captcha_id=%s", captcha_id)
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def extract_id(self, token: str) -> Optional[str]:
        """Extract the ``captcha_id`` from a token without full validation.

        Args:
            token: A token string.

        Returns:
            The captcha ID string, or ``None`` if the token is malformed.
        """
        try:
            payload = decode_signed_token(token, self._secret_key)
            return payload.get("captcha_id")
        except ValueError:
            return None

    def invalidate(self, captcha_id: str) -> None:
        """Manually mark a captcha ID as used (e.g. after storage expiry).

        Args:
            captcha_id: The ID to invalidate.
        """
        self._used_ids.add(captcha_id)

    def __repr__(self) -> str:
        return (
            f"<TokenValidator expiry={self._expiry_seconds}s "
            f"max_attempts={self._max_attempts}>"
        )
