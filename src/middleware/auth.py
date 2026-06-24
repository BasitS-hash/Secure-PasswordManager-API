from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.settings import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Validate the bearer token and return its claims.

    The token is verified for signature, expiry, issuer, and audience. The
    algorithm is pinned to a single symmetric algorithm so an attacker cannot
    downgrade to ``none`` or confuse HS/RS algorithms.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")
