"""
Audit logging middleware to record all user actions.
"""

from datetime import datetime
from src import db
from src.logger import logger


async def audit_log(user_id=None, action=None, ip=None, success=True, message=None, meta=None):
    """
    Log an audit event to the database.
    
    Args:
        user_id: ID of the user performing the action
        action: Action being performed (e.g., 'login', 'create_entry')
        ip: IP address of the request
        success: Whether the action succeeded
        message: Optional message with additional details
        meta: Optional metadata JSON
    """
    try:
        db.execute(
            '''INSERT INTO audit_logs(user_id, action, ip, success, message, meta, created_at)
               VALUES(%s, %s, %s, %s, %s, %s, %s)''',
            (user_id, action, ip, success, message, meta, datetime.now())
        )
    except Exception as err:
        logger.error(f'Failed to write audit log: {err}')
