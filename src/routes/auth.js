const express = require('express');
const router = express.Router();
const argon2 = require('argon2');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const db = require('../db');
const { auditLog } = require('../middleware/audit');
const logger = require('../logger');
const dotenv = require('dotenv');
dotenv.config();

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

router.post('/register', async (req, res) => {
  const { username, password } = req.body || {};
  const ip = req.ip;
  if (!username || !password) return res.status(400).json({ error: 'username and password required' });
  try {
    const passwordHash = await argon2.hash(password, { type: argon2.argon2id });
    const encryption_salt = crypto.randomBytes(16).toString('hex');
    const result = await db.query(
      'INSERT INTO users(username, password_hash, encryption_salt) VALUES($1,$2,$3) RETURNING id, username, encryption_salt',
      [username, passwordHash, encryption_salt]
    );
    const user = result.rows[0];
    await auditLog({ user_id: user.id, action: 'register', ip, success: true });
    res.status(201).json({ id: user.id, username: user.username });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ action: 'register', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Registration failed' });
  }
});

router.post('/login', async (req, res) => {
  const { username, password } = req.body || {};
  const ip = req.ip;
  if (!username || !password) return res.status(400).json({ error: 'username and password required' });
  try {
    const result = await db.query('SELECT id, password_hash, encryption_salt FROM users WHERE username=$1', [username]);
    if (result.rowCount === 0) {
      await auditLog({ action: 'login', ip, success: false, message: 'user not found' });
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    const user = result.rows[0];
    const valid = await argon2.verify(user.password_hash, password);
    if (!valid) {
      await auditLog({ user_id: user.id, action: 'login', ip, success: false, message: 'invalid password' });
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const accessToken = jwt.sign({ sub: user.id, username }, process.env.JWT_SECRET, { expiresIn: process.env.ACCESS_TOKEN_EXPIRES_IN || '15m' });
    const refreshToken = uuidv4();
    const tokenHash = hashToken(refreshToken);
    const expiresAt = new Date(Date.now() + (parseExpiry(process.env.REFRESH_TOKEN_EXPIRES_IN || '7d')));
    await db.query('INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES($1,$2,$3)', [user.id, tokenHash, expiresAt]);
    await auditLog({ user_id: user.id, action: 'login', ip, success: true });
    // Return encryption_salt so client can derive encryption key for zero-knowledge
    res.json({ accessToken, refreshToken, encryption_salt: user.encryption_salt });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ action: 'login', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Login failed' });
  }
});

function parseExpiry(str) {
  // simple parser for 7d, 15m, etc.
  if (!str) return 0;
  const match = /^([0-9]+)([smhd])$/.exec(str);
  if (!match) return 0;
  const n = Number(match[1]);
  const unit = match[2];
  const multipliers = { s: 1000, m: 60 * 1000, h: 3600 * 1000, d: 24 * 3600 * 1000 };
  return n * (multipliers[unit] || 0);
}

router.post('/token', async (req, res) => {
  // exchange refresh token for new access token
  const { refreshToken } = req.body || {};
  const ip = req.ip;
  if (!refreshToken) return res.status(400).json({ error: 'refreshToken required' });
  try {
    const tokenHash = hashToken(refreshToken);
    const row = await db.query('SELECT user_id, expires_at FROM refresh_tokens WHERE token_hash=$1', [tokenHash]);
    if (row.rowCount === 0) return res.status(403).json({ error: 'Invalid refresh token' });
    const record = row.rows[0];
    if (new Date(record.expires_at) < new Date()) return res.status(403).json({ error: 'Refresh token expired' });
    const userRow = await db.query('SELECT username FROM users WHERE id=$1', [record.user_id]);
    const username = userRow.rows[0].username;
    const accessToken = jwt.sign({ sub: record.user_id, username }, process.env.JWT_SECRET, { expiresIn: process.env.ACCESS_TOKEN_EXPIRES_IN || '15m' });
    await auditLog({ user_id: record.user_id, action: 'refresh_token', ip, success: true });
    res.json({ accessToken });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ action: 'refresh_token', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Token exchange failed' });
  }
});

router.post('/logout', async (req, res) => {
  const { refreshToken } = req.body || {};
  const ip = req.ip;
  if (!refreshToken) return res.status(400).json({ error: 'refreshToken required' });
  try {
    const tokenHash = hashToken(refreshToken);
    await db.query('DELETE FROM refresh_tokens WHERE token_hash=$1', [tokenHash]);
    await auditLog({ action: 'logout', ip, success: true });
    res.json({ ok: true });
  } catch (err) {
    logger.error(err.message);
    await auditLog({ action: 'logout', ip, success: false, message: err.message });
    res.status(500).json({ error: 'Logout failed' });
  }
});

module.exports = router;
