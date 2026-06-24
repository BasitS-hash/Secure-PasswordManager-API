"""Shared pytest configuration and fixtures.

A strong JWT_SECRET is set *before* the application package is imported so that
the fail-fast secret validation in ``src.settings`` is satisfied during tests.
"""

import os

# Must run at import time, before any `from app import app` / `from src...`.
os.environ.setdefault("JWT_SECRET", "test-" + "x" * 40)
os.environ.setdefault("JWT_ISSUER", "secure-password-manager-api")
os.environ.setdefault("JWT_AUDIENCE", "secure-password-manager-clients")

import pytest  # noqa: E402  (must come after the env setup above)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the in-memory rate-limit counters around every test.

    The SlowAPI ``limiter`` is a module-global singleton shared across the whole
    test session. Without resetting it, the strict per-endpoint auth limit
    (``10/minute``) leaks across tests: a later test's register/login call gets a
    429 instead of 200 and the response has no ``accessToken``. Resetting per
    test keeps each test isolated while leaving the production limit unchanged.
    """
    from src.middleware.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()
