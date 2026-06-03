import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-ci-only")
# Disable rate limiting in tests — validation tests reuse the same client IP
os.environ.setdefault("TESTING", "true")
