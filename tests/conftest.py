"""Shared pytest configuration and fixtures.

A strong JWT_SECRET is set *before* the application package is imported so that
the fail-fast secret validation in ``src.settings`` is satisfied during tests.
"""

import os

# Must run at import time, before any `from app import app` / `from src...`.
os.environ.setdefault("JWT_SECRET", "test-" + "x" * 40)
os.environ.setdefault("JWT_ISSUER", "secure-password-manager-api")
os.environ.setdefault("JWT_AUDIENCE", "secure-password-manager-clients")
