"""SlowAPI rate limiter configuration.

A global default protects every endpoint; auth endpoints get a much tighter
per-endpoint limit (applied via decorators) because they are the prime target
for credential-stuffing and brute-force attacks.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Tighter limit for authentication endpoints (login/register/token).
AUTH_RATE_LIMIT = "10/minute"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
)
