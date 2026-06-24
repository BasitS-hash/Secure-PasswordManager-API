# Secure Password Manager API

**Created by Syed Basit Sherazi**

A production-minded REST API for storing secrets using a **zero-knowledge
architecture** — the server only ever sees ciphertext. Built to demonstrate
backend security-engineering practice: AEAD encryption, Argon2id hashing,
hardened JWT auth with rotation, brute-force defences, and a CI/CD pipeline that
gates every change behind tests and security scanners.

<p>
  <img alt="CI" src="https://github.com/BasitS-hash/Secure-PasswordManager-API/actions/workflows/ci.yml/badge.svg">
  <img alt="CodeQL" src="https://github.com/BasitS-hash/Secure-PasswordManager-API/actions/workflows/codeql.yml/badge.svg">
  <img alt="Security Scan" src="https://github.com/BasitS-hash/Secure-PasswordManager-API/actions/workflows/security.yml/badge.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Coverage" src="https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen">
</p>

- Interactive API docs (Swagger UI): `/docs`
- ReDoc: `/redoc`

---

## Why zero-knowledge?

A password manager is only as trustworthy as its worst day — a database breach.
This API is designed so that even a **full database compromise leaks nothing
readable**. The encryption key is derived on the client from the user's master
password and never reaches the server; the server stores only AES-256-GCM
ciphertext, IV, and authentication tag.

```
            CLIENT (trusted)                      │            SERVER (untrusted store)
                                                  │
  master password ──┐                             │
                    ├──► Argon2id / PBKDF2 (KDF)  │
   encryption_salt ─┘            │                │
                                 ▼                │
                       AES-256 key (32 bytes)     │
                                 │                │
        plaintext entry ─► AES-256-GCM encrypt ───┼──►  { ciphertext, iv, tag }  ──► PostgreSQL
                                                  │            (cannot be decrypted here)
                                                  │
        plaintext ◄── AES-256-GCM decrypt ◄───────┼──◄  { ciphertext, iv, tag }
                                                  │
```

The full threat model and cryptographic rationale live in
**[SECURITY.md](SECURITY.md)**.

---

## Security highlights

- **AES-256-GCM** authenticated encryption (AEAD) — per-record random 96-bit
  nonce, 128-bit tag verified on every decrypt, 256-bit key enforced. No ECB, no
  unauthenticated CBC.
- **Argon2id** master-password hashing (memory-hard, constant-time verify,
  rehash-on-login when parameters strengthen).
- **Hardened JWT** — HS256 with a startup-validated secret; algorithm pinned;
  `iss`/`aud`/`exp` verified; required claims enforced. No insecure fallback
  secret (the app refuses to boot without a strong one).
- **Single-use refresh tokens**, rotated **atomically** (no race window),
  stored only as keyed HMAC-SHA256 hashes.
- **Brute-force defence** — per-IP rate limiting on auth endpoints + account
  lockout after repeated failures.
- **Enumeration resistance** — identical login responses and dummy-hash timing
  for unknown users.
- **Parameterised SQL** everywhere; **IDOR-proof** per-user scoping on all entry
  queries.
- **Security headers** (CSP, HSTS, `X-Frame-Options: DENY`, `nosniff`).
- **Supply-chain hygiene** — pinned deps, `pip-audit`, Dependabot, Trivy, Bandit,
  Gitleaks, CodeQL all wired into CI.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 15 (psycopg2, pooled) |
| Password hashing | Argon2id (`argon2-cffi`) |
| Encryption | AES-256-GCM (`cryptography`) |
| Auth | JWT (PyJWT) + rotating refresh tokens |
| Rate limiting | SlowAPI |
| Container | Docker + Docker Compose (non-root image) |
| CI/CD | GitHub Actions (CI, CodeQL, security scan, build) |

---

## Quickstart

### With Docker Compose (recommended)

```bash
git clone https://github.com/BasitS-hash/Secure-PasswordManager-API.git
cd Secure-PasswordManager-API
cp .env.production.example .env        # fill in real values (esp. JWT_SECRET)
docker-compose up --build
```

API: `http://localhost:4000` · Docs: `http://localhost:4000/docs`

### Without Docker

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # fill in DATABASE_URL and JWT_SECRET

# Generate a strong JWT secret:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Apply migrations against your PostgreSQL instance:
for f in migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done

python3 app.py
```

> The app **fails fast** at startup if `JWT_SECRET` is missing, too short, or a
> known placeholder — by design.

---

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `JWT_SECRET` | yes | — | >= 32 chars; validated at startup |
| `JWT_ISSUER` | no | `secure-password-manager-api` | |
| `JWT_AUDIENCE` | no | `secure-password-manager-clients` | |
| `ACCESS_TOKEN_EXPIRES_IN` | no | `35m` | form `<int><s\|m\|h\|d>` |
| `REFRESH_TOKEN_EXPIRES_IN` | no | `7d` | |
| `MAX_FAILED_LOGINS` | no | `5` | lockout threshold |
| `LOCKOUT_MINUTES` | no | `15` | lockout duration |
| `PORT` | no | `4000` | |
| `LOG_LEVEL` | no | `INFO` | |

See `.env.example` / `.env.production.example`.

---

## API reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | — | Liveness probe |
| `/auth/register` | POST | — | Create account (returns id) |
| `/auth/login` | POST | — | Returns `accessToken`, `refreshToken`, `encryption_salt` |
| `/auth/token` | POST | — | Rotate refresh token → new access token |
| `/auth/logout` | POST | — | Invalidate a refresh token |
| `/entries/` | POST | JWT | Store an encrypted entry |
| `/entries/` | GET | JWT | List your encrypted entries |
| `/entries/{id}` | GET | JWT | Get one entry (UUID) |
| `/entries/{id}` | PUT | JWT | Update an entry |
| `/entries/{id}` | DELETE | JWT | Delete an entry |

Auth flow: register → login → send `Authorization: Bearer <accessToken>` on
`/entries` calls → refresh via `/auth/token` when the access token expires.

Password policy: min 20 chars with upper, lower, digit, and special character.

---

## Testing

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest --cov=src --cov-report=term-missing
```

Coverage includes:

- AES-256-GCM round-trips **and** adversarial cases (tampered ciphertext/IV/tag,
  wrong key, nonce uniqueness, key-length enforcement).
- JWT hardening (forged signature, `alg=none`, expired, wrong issuer/audience,
  missing claims).
- Fail-fast secret validation.
- Full auth + entries flow against an in-memory DB: token rotation, account
  lockout, enumeration resistance, per-user isolation, input validation.
- DB-backed integration tests run against real PostgreSQL in CI.

---

## CI/CD

| Workflow | What it does |
|---|---|
| `ci.yml` | Ruff + Black + Flake8, then pytest with coverage (≥80% gate) against PostgreSQL |
| `codeql.yml` | CodeQL `security-extended` static analysis |
| `security.yml` | Bandit (SAST), pip-audit (CVEs), Gitleaks (secrets), Trivy (filesystem + image) |
| `deploy.yml` | Builds & pushes the Docker image after CI passes |
| `dependabot.yml` | Weekly pip / Actions / Docker dependency updates |

---

## Project structure

```
app.py                        # FastAPI entry point, security headers, exception handling
src/
  settings.py                 # Fail-fast secret + config loading (single source of truth)
  routes/auth.py              # Register, login, atomic token rotation, lockout
  routes/entries.py           # Per-user CRUD for encrypted entries
  middleware/auth.py          # JWT verification dependency
  middleware/audit.py         # Audit logging
  middleware/rate_limit.py    # SlowAPI limiter + auth-endpoint limit
  utils/crypto.py             # AES-256-GCM helpers
  utils/passwords.py          # Password generator + entropy
  db.py                       # Pooled PostgreSQL access, parameterised queries
migrations/                   # SQL schema (users, entries, tokens, audit, lockout)
tests/                        # Unit + security + integration tests
Dockerfile / docker-compose.yml
```

---

## License

MIT — see [LICENSE](LICENSE).
