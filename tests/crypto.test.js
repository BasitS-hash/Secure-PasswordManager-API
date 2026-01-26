const { encryptAESGCM, decryptAESGCM } = require('../src/utils/crypto');
const { generatePassword, entropyBits } = require('../src/utils/passwords');
const crypto = require('crypto');

describe('Crypto utils', () => {
  test('AES-GCM encrypt/decrypt roundtrip', () => {
    const key = crypto.randomBytes(32);
    const plaintext = 'my_secret_password';
    const { ciphertext, iv, tag } = encryptAESGCM(plaintext, key);
    const decrypted = decryptAESGCM(ciphertext, key, iv, tag);
    expect(decrypted.toString('utf8')).toBe(plaintext);
  });

  test('generatePassword creates correct length', () => {
    const pw = generatePassword({ length: 20 });
    expect(pw.length).toBe(20);
  });

  test('generatePassword includes all character types', () => {
    const pw = generatePassword({ length: 32, upper: true, lower: true, digits: true, symbols: true });
    expect(/[A-Z]/.test(pw) || /[a-z]/.test(pw) || /[0-9]/.test(pw)).toBe(true);
  });

  test('entropyBits returns reasonable value', () => {
    const pw = 'Abc123!@#';
    const entropy = entropyBits(pw);
    expect(entropy).toBeGreaterThan(0);
    expect(entropy).toBeLessThan(200);
  });
});
