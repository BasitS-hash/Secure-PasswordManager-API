# Secure Password Manager API - Setup Guide

## Prerequisites

You need Node.js installed (v18+ recommended). Install from:
- **macOS**: `brew install node` or download from https://nodejs.org/
- **Linux**: `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs`
- **Windows**: Download installer from https://nodejs.org/

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Set up PostgreSQL Database

You need a PostgreSQL database running. Options:

**Option A: Local PostgreSQL**
```bash
# macOS
brew install postgresql
brew services start postgresql
createdb passwords_db

# Linux
sudo apt-get install postgresql
sudo systemctl start postgresql
sudo -u postgres createdb passwords_db
```

**Option B: Docker PostgreSQL**
```bash
docker run --name postgres-pwd \
  -e POSTGRES_PASSWORD=mysecret \
  -e POSTGRES_DB=passwords_db \
  -p 5432:5432 \
  -d postgres:15-alpine
```

### 3. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and update:
```env
DATABASE_URL=postgres://user:password@localhost:5432/passwords_db
PORT=4000
JWT_SECRET=your_long_random_secret_here_at_least_32_chars
REFRESH_TOKEN_SECRET=another_long_random_secret_different_from_jwt
ACCESS_TOKEN_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
```

Generate secure secrets:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 4. Run Migrations

Connect to your database and run the migration files:
```bash
psql $DATABASE_URL -f migrations/001_init.sql
psql $DATABASE_URL -f migrations/002_refresh_audit.sql
```

Or from Docker:
```bash
docker exec -i postgres-pwd psql -U postgres -d passwords_db < migrations/001_init.sql
docker exec -i postgres-pwd psql -U postgres -d passwords_db < migrations/002_refresh_audit.sql
```

### 5. Run Tests
```bash
npm test
```

### 6. Start the Server
```bash
# Development (with auto-reload)
npm run dev

# Production
npm start
```

Server will run on http://localhost:4000

## Docker Deployment

Build and run the app container:
```bash
docker build -t password-manager-api .
docker run -p 4000:4000 \
  -e DATABASE_URL=postgres://user:pass@host.docker.internal:5432/passwords_db \
  -e JWT_SECRET=your_secret \
  -e REFRESH_TOKEN_SECRET=your_refresh_secret \
  password-manager-api
```

## API Usage Examples

### 1. Register a User
```bash
curl -X POST http://localhost:4000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"myMasterPassword123!"}'
```

Response:
```json
{"id":"uuid","username":"alice"}
```

### 2. Login
```bash
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"myMasterPassword123!"}'
```

Response:
```json
{
  "accessToken":"jwt_token_here",
  "refreshToken":"refresh_uuid",
  "encryption_salt":"hex_salt_for_key_derivation"
}
```

**Important**: Save the `encryption_salt` - the client must use this with the master password to derive the encryption key for zero-knowledge encryption.

### 3. Client-Side Encryption (Zero-Knowledge)

Using the client demo helper:
```javascript
const { deriveEncryptionKey, encryptPassword } = require('./client/crypto_demo');

// Derive key from master password and salt from login
const key = await deriveEncryptionKey('myMasterPassword123!', encryption_salt);

// Encrypt a password entry
const encrypted = encryptPassword('my_secret_website_password', key);
// encrypted = { ciphertext: 'base64...', iv: 'base64...', tag: 'base64...' }
```

### 4. Store Encrypted Entry
```bash
curl -X POST http://localhost:4000/api/entries \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name":"Gmail",
    "ciphertext":"base64_encrypted_data",
    "iv":"base64_iv",
    "tag":"base64_auth_tag",
    "meta":{"url":"https://gmail.com"}
  }'
```

### 5. List Entries
```bash
curl http://localhost:4000/api/entries \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "entries": [
    {
      "id":"uuid",
      "name":"Gmail",
      "ciphertext":"base64...",
      "iv":"base64...",
      "tag":"base64...",
      "meta":{"url":"https://gmail.com"},
      "created_at":"2026-01-26T..."
    }
  ]
}
```

Client must decrypt each entry using the derived key.

### 6. Refresh Access Token
```bash
curl -X POST http://localhost:4000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"your_refresh_token"}'
```

### 7. Logout
```bash
curl -X POST http://localhost:4000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"your_refresh_token"}'
```

## Security Features Implemented

✅ **Master Password Hashing**: Argon2id (memory-hard, GPU-resistant)  
✅ **Zero-Knowledge Storage**: Server stores only ciphertext, never plaintext  
✅ **AES-256-GCM Encryption**: Authenticated encryption with additional data  
✅ **JWT Authentication**: Short-lived access tokens (15min) + refresh tokens  
✅ **Rate Limiting**: 10 requests per 15min window on auth endpoints  
✅ **Brute Force Protection**: Rate limiting + audit logging  
✅ **Security Headers**: helmet.js for HTTP security headers  
✅ **Audit Logging**: All access attempts logged with IP, timestamp, success/failure  
✅ **Password Generator**: Cryptographically secure random password generation  
✅ **Entropy Analyzer**: Password strength estimation  

## Project Structure

```
.
├── client/
│   └── crypto_demo.js          # Client-side crypto helpers (zero-knowledge demo)
├── migrations/
│   ├── 001_init.sql            # Users and password_entries tables
│   └── 002_refresh_audit.sql   # Refresh tokens and audit logs
├── src/
│   ├── db/
│   │   └── index.js            # PostgreSQL connection pool
│   ├── middleware/
│   │   ├── auth.js             # JWT authentication middleware
│   │   ├── audit.js            # Audit logging helper
│   │   └── rateLimit.js        # Rate limiter for auth routes
│   ├── routes/
│   │   ├── auth.js             # Register, login, token refresh, logout
│   │   └── entries.js          # Create and list password entries
│   ├── utils/
│   │   ├── crypto.js           # AES-GCM encryption helpers
│   │   └── passwords.js        # Password generator and entropy calculator
│   ├── app.js                  # Express app entry point
│   └── logger.js               # Winston logger
├── tests/
│   ├── api.test.js             # API endpoint smoke tests
│   └── crypto.test.js          # Crypto utility tests
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── jest.config.js
├── package.json
└── README.md
```

## Testing

Run all tests:
```bash
npm test
```

The test suite includes:
- AES-GCM encryption/decryption roundtrip tests
- Password generator validation
- Entropy calculation tests
- API endpoint smoke tests (auth, entries)

## Notes on Zero-Knowledge Architecture

This implementation demonstrates a **zero-knowledge storage model**:

1. **Server never sees plaintext**: The API only stores encrypted ciphertext, IV, and auth tag
2. **Client-side key derivation**: Clients derive encryption keys from the master password + salt using Argon2id
3. **Per-user salt**: Each user has a unique `encryption_salt` for key derivation
4. **No key storage**: Encryption keys are derived on-demand and never stored
5. **Master password hashing**: Separate Argon2id hash for authentication (stored in DB)

### Key Derivation Flow
```
Master Password + User Salt --[Argon2id]--> Encryption Key (32 bytes)
                                                    |
                                                    v
Entry Plaintext --[AES-256-GCM + Random IV]--> Ciphertext + IV + Tag
                                                    |
                                                    v
                                              Store in Database
```

### Decryption Flow
```
User logs in --> Receives encryption_salt
Master Password + Salt --[Argon2id]--> Encryption Key
                                           |
                                           v
Fetch entries (ciphertext, iv, tag) --[AES-256-GCM decrypt]--> Plaintext
```

## Production Considerations

For production deployment, additionally implement:

- HTTPS/TLS termination (e.g., nginx, cloudflare)
- Database connection pooling tuning
- Redis for session storage and rate limiting
- Monitoring (Prometheus, Grafana)
- Backup strategy for PostgreSQL
- Secrets management (HashiCorp Vault, AWS Secrets Manager)
- Input validation library (joi, express-validator)
- CORS configuration if serving browser clients
- Database migrations tool (knex, sequelize)

## License

MIT
