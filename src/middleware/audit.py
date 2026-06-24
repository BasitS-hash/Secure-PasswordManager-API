"""Audit logging: record security-relevant user actions to the database.

Failures to write an audit record must never break the request flow, so write
errors are logged and swallowed here (this is the one deliberate exception to
the no-silent-failure rule, scoped narrowly to audit persistence).
"""

from src import db
from src.logger import logger


def audit_log(
    user_id=None, action=None, ip=None, success=True, message=None, meta=None
):
    """Insert an audit event.

    Args:
        user_id: ID of the user performing the action (may be None pre-auth).
        action: Action name, e.g. ``login`` or ``create_entry``.
        ip: Client IP address.
        success: Whether the action succeeded.
        message: Optional human-readable detail.
        meta: Optional JSON-serialisable metadata.
    """
    try:
        # created_at is set by the column default (now()) in the schema.
        db.execute(
            """INSERT INTO audit_logs(user_id, action, ip, success, message, meta)
               VALUES(%s, %s, %s, %s, %s, %s)""",
            (user_id, action, ip, success, message, meta),
        )
    except Exception as err:
        logger.error(f"Failed to write audit log: {err}")
