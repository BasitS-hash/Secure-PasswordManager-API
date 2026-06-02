from datetime import datetime, timezone
from src import db
from src.logger import logger


def audit_log(user_id=None, action=None, ip=None, success=True, message=None, meta=None):
    try:
        db.execute(
            "INSERT INTO audit_logs(user_id, action, ip, success, message, meta, created_at) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s)",
            (user_id, action, ip, success, message, meta, datetime.now(timezone.utc)),
        )
    except Exception as err:
        logger.error(f"Failed to write audit log: {err}")
