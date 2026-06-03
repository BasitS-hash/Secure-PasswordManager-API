import os
from slowapi import Limiter
from slowapi.util import get_remote_address

_testing = os.getenv("TESTING", "false").lower() == "true"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
    enabled=not _testing,
)
