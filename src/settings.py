"""
Centralised, fail-fast application settings.

This is the single source of truth for security-sensitive configuration
(JWT secret, token lifetimes, JWT issuer/audience). Importing this module
validates the environment at startup so the application refuses to run with
an insecure default secret rather than silently falling back to one.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Values that must never be accepted as a real JWT secret. A leftover
# placeholder in the environment is treated the same as a missing secret.
_FORBIDDEN_SECRETS = frozenset(
    {
        "",
        "your-secret-key-change-me",
        "change-me-in-production",
        "changeme",
        "secret",
        "CHANGE_ME_TO_LONG_RANDOM_STRING",
    }
)

# Minimum acceptable JWT secret length (bytes). 32 bytes = 256 bits, matching
# the HS256 output size so the secret is not the weakest link.
MIN_JWT_SECRET_LENGTH = 32

JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER", "secure-password-manager-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "secure-password-manager-clients")

# Token lifetimes (parsed as "<int><s|m|h|d>" elsewhere).
ACCESS_TOKEN_EXPIRES_IN = os.getenv("ACCESS_TOKEN_EXPIRES_IN", "35m")
REFRESH_TOKEN_EXPIRES_IN = os.getenv("REFRESH_TOKEN_EXPIRES_IN", "7d")

# Brute-force protection.
MAX_FAILED_LOGINS = int(os.getenv("MAX_FAILED_LOGINS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))


def _load_jwt_secret() -> str:
    """Return a validated JWT secret or raise at import time.

    Raising here means the process cannot start with a forgeable token secret,
    which is the whole security guarantee of the JWT layer.
    """
    secret = os.getenv("JWT_SECRET", "")

    if secret in _FORBIDDEN_SECRETS:
        raise RuntimeError(
            "JWT_SECRET is not set or uses a known insecure placeholder. "
            'Generate one with: python3 -c "import secrets; '
            'print(secrets.token_hex(32))" and set it in the environment.'
        )

    if len(secret) < MIN_JWT_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters; "
            f"got {len(secret)}. Generate one with: python3 -c "
            '"import secrets; print(secrets.token_hex(32))".'
        )

    return secret


JWT_SECRET = _load_jwt_secret()
