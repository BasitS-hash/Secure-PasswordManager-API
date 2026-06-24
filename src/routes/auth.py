import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import db
from src.logger import logger
from src.middleware.audit import audit_log
from src.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from src.settings import (
    ACCESS_TOKEN_EXPIRES_IN,
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_SECRET,
    LOCKOUT_MINUTES,
    MAX_FAILED_LOGINS,
    REFRESH_TOKEN_EXPIRES_IN,
)

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()

EXPIRY_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}

# Pre-computed Argon2 hash of a throwaway value. Verifying against this when a
# username does not exist keeps login response time roughly constant, defeating
# username-enumeration via timing or response differences.
_DUMMY_HASH = ph.hash("enumeration-resistance-dummy-value")

# Password policy.
MIN_PASSWORD_LENGTH = 20


class RegisterRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "basit_dev",
                "password": "SecurePass1@3$5678XX",
            }
        }
    }


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "basit_dev",
                "password": "SecurePass1@3$5678XX",
            }
        }
    }


class RefreshRequest(BaseModel):
    refreshToken: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {"refreshToken": "550e8400-e29b-41d4-a716-446655440000"}
        }
    }


class LogoutRequest(BaseModel):
    refreshToken: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {"refreshToken": "550e8400-e29b-41d4-a716-446655440000"}
        }
    }


# Server-side key for hashing refresh tokens. Deriving it from JWT_SECRET keeps
# the keyed HMAC without introducing another required environment variable: even
# if the refresh_tokens table is exfiltrated, an attacker cannot verify guessed
# tokens offline without also knowing the server secret.
_TOKEN_HMAC_KEY = hashlib.sha256(("refresh-token-hmac:" + JWT_SECRET).encode()).digest()


def hash_token(token: str) -> str:
    """Keyed-hash an opaque refresh token for storage (never store the raw token)."""
    return hmac.new(_TOKEN_HMAC_KEY, token.encode(), hashlib.sha256).hexdigest()


def parse_expiry(expiry_str: Optional[str], *, label: str = "") -> timedelta:
    match = re.match(r"^(\d+)([smhd])$", expiry_str or "")
    if not match:
        raise RuntimeError(
            f"Invalid token-expiry value{f' for {label}' if label else ''}: "
            f"{expiry_str!r}. Use a form like '35m', '7d', '1h'."
        )
    value, unit = int(match.group(1)), match.group(2)
    return timedelta(**{EXPIRY_UNITS[unit]: value})


def validate_username(username: str) -> tuple[bool, str]:
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
        return (
            False,
            "Username must be 3-30 characters (letters, digits, underscore only)",
        )
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit (e.g. 1, 3, 5)"
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]", password):
        return False, "Password must contain at least one special character (e.g. @, $)"
    return True, ""


# Validate token lifetimes once, at import time, so a misconfigured value fails
# fast instead of silently issuing wrong-lifetime tokens at runtime.
ACCESS_TOKEN_TTL = parse_expiry(
    ACCESS_TOKEN_EXPIRES_IN, label="ACCESS_TOKEN_EXPIRES_IN"
)
REFRESH_TOKEN_TTL = parse_expiry(
    REFRESH_TOKEN_EXPIRES_IN, label="REFRESH_TOKEN_EXPIRES_IN"
)


def make_access_token(user_id, username: str, now: datetime) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "exp": now + ACCESS_TOKEN_TTL,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _is_locked(user: dict, now: datetime) -> bool:
    locked_until = user.get("locked_until")
    if not locked_until:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > now


def _register_failed_login(user_id, now: datetime) -> None:
    """Increment the failed-login counter and lock the account if over the cap."""
    db.execute(
        """UPDATE users
           SET failed_login_attempts = failed_login_attempts + 1,
               locked_until = CASE
                   WHEN failed_login_attempts + 1 >= %s THEN %s
                   ELSE locked_until
               END
           WHERE id = %s""",
        (MAX_FAILED_LOGINS, now + timedelta(minutes=LOCKOUT_MINUTES), user_id),
    )


def _reset_failed_login(user_id) -> None:
    db.execute(
        "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = %s",
        (user_id,),
    )


@router.post("/register", status_code=201)
@limiter.limit(AUTH_RATE_LIMIT)
def register(body: RegisterRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.username or not body.password:
        audit_log(
            action="register", ip=ip, success=False, message="missing credentials"
        )
        raise HTTPException(status_code=400, detail="username and password required")

    valid, msg = validate_username(body.username)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    valid, msg = validate_password(body.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    try:
        result = db.query(
            """INSERT INTO users(username, password_hash, encryption_salt)
               VALUES(%s, %s, %s)
               RETURNING id, username""",
            # 32-byte (256-bit) salt, aligned with the AES-256 key the client
            # derives from it.
            (body.username, ph.hash(body.password), os.urandom(32).hex()),
        )
        user = result[0]
        audit_log(user_id=user["id"], action="register", ip=ip, success=True)
        return {"id": user["id"], "username": user["username"]}

    except Exception as err:
        # Full detail stays in the server log; the audit row gets a generic
        # message so raw SQL/driver text never lands in shipped audit data.
        logger.error(f"Registration error: {err}")
        audit_log(
            action="register", ip=ip, success=False, message="registration failed"
        )
        raise HTTPException(status_code=409, detail="Username already taken")


@router.post("/login")
@limiter.limit(AUTH_RATE_LIMIT)
def login(body: LoginRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.username or not body.password:
        audit_log(action="login", ip=ip, success=False, message="missing credentials")
        raise HTTPException(status_code=400, detail="username and password required")

    try:
        result = db.query(
            """SELECT id, password_hash, encryption_salt,
                      failed_login_attempts, locked_until
               FROM users WHERE username=%s""",
            (body.username,),
        )

        now = datetime.now(timezone.utc)

        if not result:
            # No such user. Still perform a verify against a dummy hash so the
            # response time does not reveal whether the username exists.
            try:
                ph.verify(_DUMMY_HASH, body.password)
            except VerifyMismatchError:
                pass
            audit_log(action="login", ip=ip, success=False, message="user not found")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = result[0]

        if _is_locked(user, now):
            audit_log(
                user_id=user["id"],
                action="login",
                ip=ip,
                success=False,
                message="account locked",
            )
            raise HTTPException(
                status_code=429,
                detail="Account temporarily locked due to repeated failed logins",
            )

        try:
            ph.verify(user["password_hash"], body.password)
        except VerifyMismatchError:
            _register_failed_login(user["id"], now)
            audit_log(
                user_id=user["id"],
                action="login",
                ip=ip,
                success=False,
                message="invalid password",
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Successful login: clear lockout state.
        _reset_failed_login(user["id"])

        # Transparently upgrade the stored hash if Argon2 parameters have been
        # strengthened since this password was last hashed.
        try:
            if ph.check_needs_rehash(user["password_hash"]):
                db.execute(
                    "UPDATE users SET password_hash=%s WHERE id=%s",
                    (ph.hash(body.password), user["id"]),
                )
        except Exception as rehash_err:  # never fail a valid login over a rehash
            logger.warning(f"Password rehash skipped: {rehash_err}")

        access_token = make_access_token(user["id"], body.username, now)

        refresh_token = str(uuid.uuid4())
        expires_at = now + REFRESH_TOKEN_TTL
        db.execute(
            "INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES(%s, %s, %s)",
            (user["id"], hash_token(refresh_token), expires_at),
        )

        audit_log(user_id=user["id"], action="login", ip=ip, success=True)
        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "encryption_salt": user["encryption_salt"],
        }

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Login error: {err}")
        audit_log(action="login", ip=ip, success=False, message="login error")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/token")
@limiter.limit(AUTH_RATE_LIMIT)
def refresh_token(body: RefreshRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.refreshToken:
        audit_log(
            action="refresh_token",
            ip=ip,
            success=False,
            message="missing refresh token",
        )
        raise HTTPException(status_code=400, detail="refreshToken required")

    try:
        now = datetime.now(timezone.utc)
        new_refresh_token = str(uuid.uuid4())

        # Atomic rotation: a single statement deletes the presented token (only
        # if it exists and has not expired) and inserts the replacement. Because
        # the DELETE acquires a row lock, two concurrent requests presenting the
        # same token cannot both succeed — the second sees zero deleted rows.
        rotated = db.query(
            """WITH old AS (
                   DELETE FROM refresh_tokens
                   WHERE token_hash = %s AND expires_at > %s
                   RETURNING user_id
               )
               INSERT INTO refresh_tokens(user_id, token_hash, expires_at)
               SELECT user_id, %s, %s FROM old
               RETURNING user_id""",
            (
                hash_token(body.refreshToken),
                now,
                hash_token(new_refresh_token),
                now + REFRESH_TOKEN_TTL,
            ),
        )
        if not rotated:
            raise HTTPException(
                status_code=403, detail="Invalid or expired refresh token"
            )

        user_id = rotated[0]["user_id"]
        user = db.query("SELECT username FROM users WHERE id=%s", (user_id,))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token = make_access_token(user_id, user[0]["username"], now)
        audit_log(user_id=user_id, action="refresh_token", ip=ip, success=True)
        return {"accessToken": access_token, "refreshToken": new_refresh_token}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Token refresh error: {err}")
        audit_log(action="refresh_token", ip=ip, success=False, message="refresh error")
        raise HTTPException(status_code=500, detail="Token exchange failed")


@router.post("/logout")
@limiter.limit(AUTH_RATE_LIMIT)
def logout(body: LogoutRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.refreshToken:
        audit_log(
            action="logout", ip=ip, success=False, message="missing refresh token"
        )
        raise HTTPException(status_code=400, detail="refreshToken required")

    try:
        db.execute(
            "DELETE FROM refresh_tokens WHERE token_hash=%s",
            (hash_token(body.refreshToken),),
        )
        audit_log(action="logout", ip=ip, success=True)
        return {"ok": True}

    except Exception as err:
        logger.error(f"Logout error: {err}")
        audit_log(action="logout", ip=ip, success=False, message="logout error")
        raise HTTPException(status_code=500, detail="Logout failed")
