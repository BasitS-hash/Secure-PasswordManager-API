# Secure Password Manager API

**Created by Syed Basit Sherazi**

A production-ready REST API for securely storing and managing passwords using a **zero-knowledge architecture** — the server never sees your plaintext passwords.

- Live API: `https://secure-passwordmanager-api-production.up.railway.app`
- Interactive Docs: `https://secure-passwordmanager-api-production.up.railway.app/docs`

---

## Features

- **Zero-Knowledge Storage** — passwords are encrypted client-side before being sent
- **Argon2id Hashing** — memory-hard, GPU-resistant master password protection
- **AES-256-GCM Encryption** — authenticated client-side encryption
- **JWT Authentication** — access token (35 min) + refresh token (7 days) with rotation
- **Rate Limiting** — brute force protection on all endpoints
- **Audit Logging** — every action logged with IP and timestamp
- **Password Generator** — cryptographically secure random passwords
- **Auto-generated Docs** — interactive Swagger UI at `/docs`
- **Docker Ready** — one-command local deployment
- **CI/CD** — auto-deploys to Railway on every push to main

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 15 |
| Password Hashing | Argon2id |
| Encryption | AES-256-GCM (cryptography library) |
| Authentication | JWT (PyJWT) |
| Web Server | Uvicorn |
| Rate Limiting | SlowAPI |
| Deployment | Railway |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | No | Health check |
| `/auth/register` | POST | No | Create account |
| `/auth/login` | POST | No | Login, get tokens + salt |
| `/auth/token` | POST | No | Refresh access token |
| `/auth/logout` | POST | No | Invalidate session |
| `/entries/` | POST | JWT | Store encrypted entry |
| `/entries/` | GET | JWT | List all encrypted entries |
| `/entries/{id}` | GET | JWT | Get single entry |
| `/entries/{id}` | PUT | JWT | Update entry |
| `/entries/{id}` | DELETE | JWT | Delete entry |

Full interactive docs at `/docs`.

---

## Zero-Knowledge Architecture

```
Master Password + Salt
        │
        ▼ (client-side only)
   Argon2id / PBKDF2
        │
        ▼
  AES-256 Key (32 bytes)
        │
        ▼
  AES-256-GCM Encrypt(password entry)
        │
        ▼
  { ciphertext, iv, tag }  ──► sent to server ──► stored in DB
```

The server only ever stores encrypted blobs. Even a full database breach exposes nothing readable.

---

## Run Locally with Docker

```bash
git clone https://github.com/BasitS-hash/Secure-PasswordManager-API.git
cd Secure-PasswordManager-API
docker-compose up --build
```

API runs at `http://localhost:4000` and docs at `http://localhost:4000/docs`

---

## Run Without Docker

```bash
pip3 install -r requirements.txt
cp .env.example .env   # fill in your values
python3 app.py
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/passwords_db
PORT=4000
JWT_SECRET=your_32_byte_random_secret
ACCESS_TOKEN_EXPIRES_IN=35m
REFRESH_TOKEN_EXPIRES_IN=7d
```

Generate a secret:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testing

```bash
python3 -m pytest tests/ -v
```

Tests cover:
- AES-GCM encrypt/decrypt roundtrip
- Password generator (length, charsets, entropy)
- API endpoint auth checks (no DB required)
- Full CRUD flow with real DB (runs in CI against PostgreSQL)

---

## Project Structure

```
app.py                        # FastAPI entry point
src/
  routes/auth.py              # Register, login, token, logout
  routes/entries.py           # Full CRUD for encrypted entries
  middleware/auth.py          # JWT verification (FastAPI Depends)
  middleware/audit.py         # Audit logging
  middleware/rate_limit.py    # SlowAPI rate limiter setup
  utils/crypto.py             # AES-256-GCM helpers
  utils/passwords.py          # Password generator + entropy
  db.py                       # PostgreSQL connection + queries
migrations/
  001_init.sql                # users + password_entries tables
  002_refresh_audit.sql       # refresh_tokens + audit_logs tables
tests/
  test_api.py                 # API integration tests
  test_crypto.py              # Crypto + password unit tests
docker-compose.yml
Dockerfile
```

---

## License

MIT
