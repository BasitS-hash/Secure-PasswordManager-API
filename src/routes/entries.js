const express = require('express');
const router = express.Router();
const db = require('../db');
const { authenticateToken } = require('../middleware/auth');
const { auditLog } = require('../middleware/audit');
const logger = require('../logger');

// Create a password entry (expects ciphertext, iv, tag from client-side encryption)
router.post('/', authenticateToken, async (req, res) => {
  const { name, ciphertext, iv, tag, meta } = req.body || {};
  const userId = req.user && req.user.sub;
  const ip = req.ip;
  if (!name || !ciphertext || !iv || !tag) return res.status(400).json({ error: 'name, ciphertext, iv and tag are required' });
  try {
    await db.query(
      'INSERT INTO password_entries(user_id, name, ciphertext, iv, tag, meta) VALUES($1,$2,$3,$4,$5,$6)',
      [userId, name, Buffer.from(ciphertext, 'base64'), Buffer.from(iv, 'base64'), Buffer.from(tag, 'base64'), meta || null]
    );
    await auditLog({ user_id: userId, action: 'create_entry', ip, success: true });
    res.status(201).json({ ok: true });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ user_id: userId, action: 'create_entry', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Failed to create entry' });
  }
});

// List entries (returns ciphertext blobs only)
router.get('/', authenticateToken, async (req, res) => {
  const userId = req.user && req.user.sub;
  const ip = req.ip;
  try {
    const result = await db.query('SELECT id, name, encode(ciphertext,\'base64\') AS ciphertext, encode(iv,\'base64\') AS iv, encode(tag,\'base64\') AS tag, meta, created_at FROM password_entries WHERE user_id=$1', [userId]);
    await auditLog({ user_id: userId, action: 'list_entries', ip, success: true });
    res.json({ entries: result.rows });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ user_id: userId, action: 'list_entries', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Failed to list entries' });
  }
});

module.exports = router;
