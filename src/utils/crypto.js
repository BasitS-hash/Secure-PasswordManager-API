const crypto = require('crypto');

// AES-256-GCM helpers. These are provided for testing and client demos.
// For zero-knowledge, perform encryption/decryption client-side using derived key.

function randomBytes(size = 16) {
  return crypto.randomBytes(size);
}

function encryptAESGCM(plaintextBuffer, key) {
  if (!Buffer.isBuffer(plaintextBuffer)) plaintextBuffer = Buffer.from(plaintextBuffer, 'utf8');
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintextBuffer), cipher.final()]);
  const tag = cipher.getAuthTag();
  return { ciphertext, iv, tag };
}

function decryptAESGCM(ciphertext, key, iv, tag) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return decrypted;
}

module.exports = { encryptAESGCM, decryptAESGCM, randomBytes };
