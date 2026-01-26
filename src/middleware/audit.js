const db = require('../db');
const logger = require('../logger');

async function auditLog({ user_id = null, action, ip = null, success = true, message = null, meta = null }) {
  try {
    await db.query(
      'INSERT INTO audit_logs(user_id, action, ip, success, message, meta) VALUES($1,$2,$3,$4,$5,$6)',
      [user_id, action, ip, success, message, meta]
    );
  } catch (err) {
    logger.error(`Failed to write audit log: ${err.message}`);
  }
}

module.exports = { auditLog };
