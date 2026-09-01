"""Password hashing and JWTs.

Both are deliberately kept byte-compatible with the Express backend:

  * bcrypt at cost 10. Hashes written by bcryptjs (`$2a$10$…`) verify here
    unchanged, so existing accounts keep working across the migration.
  * HS256 tokens with the same secret and the same `sub` claim, so a token
    issued by the old backend is still accepted by this one.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

SALT_ROUNDS = 10

# bcrypt only ever looks at the first 72 bytes of a password. bcryptjs truncates
# silently; the Python library raises instead, so truncate here to keep the two
# implementations agreeing on what a long password hashes to.
_MAX_PASSWORD_BYTES = 72


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt(SALT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode_password(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed hash is not an authentication success.
        return False


# Used when the email is unknown, so a failed login costs the same time whether
# or not the account exists.
DUMMY_HASH = hash_password("credit-book-dummy-password")


def dummy_verify(password: str) -> None:
    verify_password(password, DUMMY_HASH)


def sign_token(user_id: int) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


class TokenExpired(Exception):
    pass


class TokenInvalid(Exception):
    pass


def read_token(token: str) -> int:
    """Returns the user id carried by the token, or raises."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired() from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalid() from exc

    try:
        user_id = int(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise TokenInvalid() from exc

    if user_id < 1:
        raise TokenInvalid()
    return user_id
