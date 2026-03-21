"""
Rate limiting middleware for API endpoints.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Pre-configured limiters for specific endpoints
auth_limiter = limiter.limit("10 per 15 minutes")
