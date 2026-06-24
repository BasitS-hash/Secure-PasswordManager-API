# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately. Do **not**
open a public issue.

- Use GitHub's **Private Vulnerability Reporting** (Security tab → "Report a
  vulnerability"), or
- Email the maintainer.

Please include reproduction steps, affected versions/commit, and impact. You can
expect an acknowledgement within a few days. Verified issues will be fixed and
disclosed responsibly once a patch is available.

## Supported Versions

The `main` branch receives security fixes. This is a portfolio/reference project;
pin a specific commit if you deploy it.

---

## Threat Model

### What the system protects

The protected asset is the user's stored secrets (passwords, notes). The core
guarantee is **zero-knowledge**: the server stores only ciphertext and never has
access to the key needed to decrypt it.

### In scope (defended against)

| Threat | Mitigation |
|---|---|
| Database breach / backup leak | Entries stored as AES-256-GCM ciphertext; decryption key is derived client-side and never sent to the server. |
| Credential theft from DB | Master passwords hashed with Argon2id (memory-hard). Refresh tokens stored only as keyed HMAC-SHA256 hashes. |
| JWT forgery | HS256 with a fail-fast-validated secret (>= 32 bytes); algorithm pinned; issuer, audience, and expiry verified; required claims enforced. |
| Token replay after logout / rotation | Refresh tokens are single-use and rotated atomically; the old token is invalidated in the same DB statement that issues the new one. |
| Brute-force / credential stuffing | Per-IP rate limiting on auth endpoints + account lockout after repeated failures. |
| Username enumeration | Login returns an identical response (status + body) and performs a dummy Argon2 verify for unknown users to equalise timing. |
| SQL injection | All queries use parameterised placeholders — no string interpolation. |
| IDOR (accessing others' entries) | Every entry query is scoped by the authenticated user's `sub` claim. |
| XSS / clickjacking / MIME sniffing | Security headers (CSP, `X-Frame-Options: DENY`, `nosniff`) on every response. |
| Supply-chain CVEs | Dependencies pinned and continuously scanned (pip-audit, Dependabot, Trivy). |
| Storage-amplification abuse | Size caps on entry fields and `meta`. |

### Out of scope (explicitly not defended)

- **Client-side compromise.** If the user's device is compromised, the derived
  key and plaintext are exposed. Zero-knowledge protects the server, not the
  client.
- **Weak master passwords.** The server enforces a strong password policy for
  the account login, but the strength of the client-side encryption key depends
  on the user's master password and client KDF parameters.
- **TLS termination.** Transport encryption is assumed to be handled by the
  deployment platform / reverse proxy. HSTS is set, but certificate management
  is the operator's responsibility.
- **Malicious server operator.** Zero-knowledge limits what a passive operator
  or breach can read, but a fully malicious server could serve tampered client
  code. (This is the standard limitation of any hosted zero-knowledge service.)

---

## Cryptographic Design

### Encryption of stored secrets — AES-256-GCM (client-side)

- **Algorithm:** AES-256 in GCM mode — an AEAD (authenticated encryption with
  associated data) cipher. This is chosen over ECB (no diffusion) and
  CBC-without-MAC (malleable, padding-oracle prone) because GCM provides both
  confidentiality **and** integrity in one primitive.
- **Key:** 256-bit, derived client-side from the user's master password and the
  per-account `encryption_salt`. The key never leaves the client.
- **Nonce (IV):** a fresh random 96-bit nonce per encryption. GCM is
  catastrophically broken under nonce reuse, so the helper generates a new
  `secrets.token_bytes(12)` for every operation and never reuses one.
- **Authentication tag:** the 128-bit GCM tag is stored alongside the
  ciphertext and verified on decrypt. Any tampering with ciphertext, IV, or tag
  causes decryption to fail (`InvalidTag`) rather than returning corrupted data.
- The server stores `{ciphertext, iv, tag}` as raw bytes and cannot decrypt
  them.

### Master password hashing — Argon2id

- **Algorithm:** Argon2id via `argon2-cffi` — the memory-hard, GPU/ASIC-resistant
  winner of the Password Hashing Competition, recommended by OWASP.
- Verification is constant-time. Hashes are transparently upgraded on login when
  parameters are strengthened (`check_needs_rehash`).
- Master passwords are never stored or logged in plaintext.

### Tokens

- **Access token:** short-lived JWT (HS256), with `iss`, `aud`, `iat`, `exp`,
  and `sub`. Verification pins the algorithm and requires all critical claims.
- **Refresh token:** a high-entropy random UUIDv4 returned to the client; the
  server stores only its **keyed** HMAC-SHA256 hash. Refresh tokens are
  single-use and rotated atomically.

---

## Secret Management

- No secrets are committed to the repository. `.env*` files are git-ignored
  (templates `*.example` excepted).
- `JWT_SECRET` is **required** and validated at startup: the app refuses to boot
  with a missing, too-short, or known-placeholder secret.
- Generate a secret with:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- Rotate any secret that may have been exposed.
