const crypto = require('crypto');

function generatePassword({ length = 16, upper = true, lower = true, digits = true, symbols = true } = {}) {
  const sets = [];
  if (upper) sets.push('ABCDEFGHIJKLMNOPQRSTUVWXYZ');
  if (lower) sets.push('abcdefghijklmnopqrstuvwxyz');
  if (digits) sets.push('0123456789');
  if (symbols) sets.push('!@#$%^&*()-_=+[]{}|;:,.<>?');
  if (sets.length === 0) throw new Error('At least one character set required');
  const all = sets.join('');
  const bytes = crypto.randomBytes(length);
  let out = '';
  for (let i = 0; i < length; i++) {
    out += all[bytes[i] % all.length];
  }
  return out;
}

function entropyBits(password) {
  // estimate entropy by log2(possibleSymbols^length) where possibleSymbols is count of used charsets
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigits = /[0-9]/.test(password);
  const hasSymbols = /[^A-Za-z0-9]/.test(password);
  let pool = 0;
  if (hasUpper) pool += 26;
  if (hasLower) pool += 26;
  if (hasDigits) pool += 10;
  if (hasSymbols) pool += 32; // approximate symbol count
  if (pool === 0) return 0;
  return Math.log2(Math.pow(pool, password.length));
}

module.exports = { generatePassword, entropyBits };
