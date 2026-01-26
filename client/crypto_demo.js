// Client-side crypto demo for zero-knowledge architecture
// In production, this would run in browser or native app

const crypto = require('crypto');
const argon2 = require('argon2');

/**
 * Derive a 32-byte encryption key from master password and salt using Argon2id
 * @param {string} masterPassword - User's master password
 * @param {string} saltHex - Hex-encoded salt from server (user.encryption_salt)
 * @returns {Promise<Buffer>} 32-byte key for AES-256
 */
async function deriveEncryptionKey(masterPassword, saltHex) {
  const salt = Buffer.from(saltHex, 'hex');
  const hash = await argon2.hash(masterPassword, {
    type: argon2.argon2id,
    salt,
    hashLength: 32,
    raw: true, // return raw bytes instead of encoded string
  });
  return hash;
}

/**
 * Encrypt plaintext password with AES-256-GCM
 * @param {string} plaintext - The password to encrypt
 * @param {Buffer} key - 32-byte encryption key
 * @returns {Object} { ciphertext, iv, tag } all base64-encoded for API
 */
function encryptPassword(plaintext, key) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return {
    ciphertext: ciphertext.toString('base64'),
    iv: iv.toString('base64'),
    tag: tag.toString('base64'),
  };
}

/**
 * Decrypt ciphertext from server
 * @param {string} ciphertextB64 - Base64 ciphertext
 * @param {string} ivB64 - Base64 IV
 * @param {string} tagB64 - Base64 auth tag
 * @param {Buffer} key - 32-byte encryption key
 * @returns {string} plaintext password
 */
function decryptPassword(ciphertextB64, ivB64, tagB64, key) {
  const ciphertext = Buffer.from(ciphertextB64, 'base64');
  const iv = Buffer.from(ivB64, 'base64');
  const tag = Buffer.from(tagB64, 'base64');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return decrypted.toString('utf8');
}

module.exports = { deriveEncryptionKey, encryptPassword, decryptPassword };
