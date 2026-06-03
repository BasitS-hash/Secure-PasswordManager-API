import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt

from src import db
from src.logger import logger
from src.middleware.audit import audit_log
from src.middleware.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise EnvironmentError("JWT_SECRET environment variable is required")

# Dummy hash used to make login timing constant whether the username exists or not.
# Computed once at startup so it doesn't add per-request overhead.
_DUMMY_HASH = ph.hash("dummy-timing-constant-value-never-valid")

EXPIRY_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


class RegisterRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "basit_dev",
                "password": "SecurePass1@3$5678XX"
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
                "password": "SecurePass1@3$5678XX"
            }
        }
    }


class RefreshRequest(BaseModel):
    refreshToken: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "refreshToken": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    }


class LogoutRequest(BaseModel):
    refreshToken: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "refreshToken": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    }


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def parse_expiry(expiry_str: Optional[str]) -> timedelta:
    match = re.match(r"^(\d+)([smhd])$", expiry_str or "")
    if not match:
        return timedelta(hours=1)
    value, unit = int(match.group(1)), match.group(2)
    return timedelta(**{EXPIRY_UNITS[unit]: value})


def validate_username(username: str):
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
        return False, "Username must be 3-30 characters (letters, digits, underscore only)"
    return True, ""


def validate_password(password: str):
    if len(password) < 20:
        return False, "Password must be at least 20 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit (e.g. 1, 3, 5)"
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]", password):
        return False, "Password must contain at least one special character (e.g. @, $)"
    return True, ""


def make_access_token(user_id, username: str, now: datetime) -> str:
    expires = parse_expiry(os.getenv("ACCESS_TOKEN_EXPIRES_IN", "35m"))
    return jwt.encode(
        {"sub": user_id, "username": username, "exp": now + expires},
        JWT_SECRET,
        algorithm="HS256",
    )


@router.post("/register", status_code=201)
@limiter.limit("3/minute;10/hour")
def register(body: RegisterRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.username or not body.password:
        audit_log(action="register", ip=ip, success=False, message="missing credentials")
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
            (body.username, ph.hash(body.password), os.urandom(32).hex()),
        )
        user = result[0]
        audit_log(user_id=user["id"], action="register", ip=ip, success=True)
        return {"id": user["id"], "username": user["username"]}

    except Exception as err:
        logger.error(f"Registration error: {err}")
        audit_log(action="register", ip=ip, success=False, message=str(err))
        raise HTTPException(status_code=409, detail="Username already taken")


@router.post("/login")
@limiter.limit("5/minute;20/hour")
def login(body: LoginRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.username or not body.password:
        audit_log(action="login", ip=ip, success=False, message="missing credentials")
        raise HTTPException(status_code=400, detail="username and password required")

    try:
        result = db.query(
            "SELECT id, password_hash, encryption_salt FROM users WHERE username=%s",
            (body.username,),
        )

        # Always run argon2 verify — even for unknown usernames — so response time
        # is constant whether the username exists or not (prevents timing enumeration).
        if not result:
            try:
                ph.verify(_DUMMY_HASH, body.password)
            except Exception:
                pass
            audit_log(action="login", ip=ip, success=False, message="user not found")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = result[0]

        try:
            ph.verify(user["password_hash"], body.password)
        except VerifyMismatchError:
            audit_log(user_id=user["id"], action="login", ip=ip, success=False,
                      message="invalid password")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        now = datetime.now(timezone.utc)
        access_token = make_access_token(user["id"], body.username, now)

        refresh_token = secrets.token_urlsafe(32)
        expires_at = now + parse_expiry(os.getenv("REFRESH_TOKEN_EXPIRES_IN", "7d"))
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
        audit_log(action="login", ip=ip, success=False, message=str(err))
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/token")
def refresh_token(body: RefreshRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.refreshToken:
        audit_log(action="refresh_token", ip=ip, success=False, message="missing refresh token")
        raise HTTPException(status_code=400, detail="refreshToken required")

    try:
        result = db.query(
            "SELECT user_id, expires_at FROM refresh_tokens WHERE token_hash=%s",
            (hash_token(body.refreshToken),),
        )
        if not result:
            raise HTTPException(status_code=403, detail="Invalid refresh token")

        record = result[0]
        now = datetime.now(timezone.utc)
        expires_at = record["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=403, detail="Refresh token expired")

        user = db.query("SELECT username FROM users WHERE id=%s", (record["user_id"],))
        if not user:
            raise HTTPException(status_code=403, detail="Invalid refresh token")

        db.execute("DELETE FROM refresh_tokens WHERE token_hash=%s",
                   (hash_token(body.refreshToken),))
        new_refresh_token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES(%s, %s, %s)",
            (record["user_id"], hash_token(new_refresh_token),
             now + parse_expiry(os.getenv("REFRESH_TOKEN_EXPIRES_IN", "7d"))),
        )

        access_token = make_access_token(record["user_id"], user[0]["username"], now)
        audit_log(user_id=record["user_id"], action="refresh_token", ip=ip, success=True)
        return {"accessToken": access_token, "refreshToken": new_refresh_token}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Token refresh error: {err}")
        audit_log(action="refresh_token", ip=ip, success=False, message=str(err))
        raise HTTPException(status_code=500, detail="Token exchange failed")


@router.post("/logout")
def logout(body: LogoutRequest, request: Request):
    ip = request.client.host if request.client else None

    if not body.refreshToken:
        audit_log(action="logout", ip=ip, success=False, message="missing refresh token")
        raise HTTPException(status_code=400, detail="refreshToken required")

    try:
        db.execute("DELETE FROM refresh_tokens WHERE token_hash=%s",
                   (hash_token(body.refreshToken),))
        audit_log(action="logout", ip=ip, success=True)
        return {"ok": True}

    except Exception as err:
        logger.error(f"Logout error: {err}")
        audit_log(action="logout", ip=ip, success=False, message=str(err))
        raise HTTPException(status_code=500, detail="Logout failed")
