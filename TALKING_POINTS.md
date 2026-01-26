# 🎤 Interview Talking Points - Quick Reference

## 30-Second Elevator Pitch
"I built a production-ready password manager with zero-knowledge encryption—meaning the server never sees plaintext passwords. It uses Argon2id for hashing, AES-256-GCM for client-side encryption, and JWT for authentication. The full stack includes Node.js/Express, PostgreSQL, Docker, and automated CI/CD with GitHub Actions. Key security features include rate limiting, audit logging, and proper error handling."

---

## Key Technical Highlights (Memorize These)

### 1. Zero-Knowledge Architecture
- **What**: Server only stores encrypted data
- **Why**: Even if database is breached, passwords stay secure
- **How**: Client derives key with PBKDF2(masterPassword + salt, 100k iterations)

### 2. Argon2id Password Hashing
- **What**: Memory-hard hashing algorithm
- **Why**: Beats bcrypt (4KB vs megabytes of RAM required)
- **Stat**: 1000x more expensive to crack than bcrypt

### 3. AES-256-GCM Encryption
- **What**: Authenticated encryption
- **Why**: Encrypts AND verifies integrity
- **How**: Random 12-byte IV per entry

### 4. JWT + Refresh Tokens
- **Access token**: 15 minutes (short-lived)
- **Refresh token**: 7 days (hashed in DB with SHA-256)
- **Why**: Balance security and UX

### 5. Rate Limiting
- **What**: 10 requests per 15 minutes on auth endpoints
- **Why**: Prevents brute-force attacks
- **Production**: Would use Redis for distributed rate limiting

---

## Architecture Flow (Draw This)

```
┌─────────────┐
│   Browser   │
│  (Web App)  │
└──────┬──────┘
       │ HTTPS
       ↓
┌─────────────┐
│    nginx    │ ← Rate limiting
│ (Reverse    │
│   Proxy)    │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Node.js    │ ← Express API
│  (Docker)   │   JWT Auth
└──────┬──────┘   Helmet
       │
       ↓
┌─────────────┐
│ PostgreSQL  │ ← Encrypted data
│  (Docker)   │   Audit logs
└─────────────┘
```

---

## Login Flow (Know This Cold)

1. Client → `POST /api/auth/login` with username + password
2. Server validates with Argon2.verify() (~500ms)
3. Server generates JWT + refresh token
4. Server returns tokens + **encryption_salt**
5. Client derives key: PBKDF2(password, salt, 100k iterations)
6. Client stores tokens in sessionStorage (NOT localStorage)
7. Future requests include `Authorization: Bearer <token>`

---

## Encryption Flow

**Storing a password:**
```javascript
// Client-side only
key = PBKDF2(masterPassword, salt, 100k)
{ciphertext, iv, tag} = AES-GCM-encrypt(password, key)
→ Send to server → Store in DB
```

**Retrieving a password:**
```javascript
// Fetch from server
{ciphertext, iv, tag} = fetch('/api/entries')
// Decrypt client-side
password = AES-GCM-decrypt(ciphertext, key, iv, tag)
```

---

## Tech Stack (One-Liner Each)

| Tech | Why I Chose It |
|------|----------------|
| **Node.js** | Great for I/O-bound API operations |
| **Express** | Minimal, flexible framework for custom security |
| **PostgreSQL** | ACID compliance + BYTEA for binary encrypted data |
| **Argon2** | Industry-standard, memory-hard hashing |
| **JWT** | Stateless authentication, easy to scale |
| **Docker** | Consistent environments, easy deployment |
| **GitHub Actions** | Built-in CI/CD, free for public repos |
| **nginx** | Efficient reverse proxy + rate limiting |

---

## Database Schema (High Level)

```sql
users
├── id (UUID)
├── username (UNIQUE)
├── password_hash (Argon2id)
└── encryption_salt (hex string)

password_entries
├── id (UUID)
├── user_id (FK)
├── name (text)
├── ciphertext (BYTEA)
├── iv (BYTEA)
└── tag (BYTEA)
```

---

## Security Features Checklist

✅ Argon2id hashing (memory-hard)
✅ AES-256-GCM encryption (authenticated)
✅ Zero-knowledge architecture
✅ JWT with refresh tokens
✅ Rate limiting (10/15min)
✅ Helmet.js security headers
✅ Audit logging (all access tracked)
✅ Input validation
✅ HTTPS ready
✅ No secret keys in code (env variables)

---

## Common Interview Questions (Quick Answers)

### "What's zero-knowledge mean?"
"Server never sees plaintext. Client encrypts before sending. Even with database access, attacker gets useless ciphertext."

### "Why Argon2 over bcrypt?"
"Memory-hard (uses MBs vs KBs). Won Password Hashing Competition 2015. 1000x harder to crack with GPUs."

### "How do you prevent brute force?"
"Rate limiting: 10 attempts per 15 minutes. Argon2 is intentionally slow (~500ms). Audit logging tracks all attempts."

### "What if user forgets master password?"
"No recovery by design—zero-knowledge means we can't decrypt their data. That's the security trade-off."

### "How would you scale this?"
"Horizontally scale API (stateless). Add read replicas for PostgreSQL. Move rate limiting to Redis. Use CDN for static files."

### "Biggest security risk?"
"XSS attacks on the client. Mitigated with CSP headers, input sanitization, and Web Crypto API (native, not JS libraries)."

---

## Demo Talking Points

### Show the website:
"This is the landing page—responsive design, modern UI. Users can register, login, and manage passwords entirely in the browser."

### Show the code:
"Here's the encryption logic—using Web Crypto API, which is native browser crypto, more secure than JS libraries."

### Show the deployment:
"Here's the CI/CD pipeline—on every push, it runs tests, builds Docker images, and auto-deploys. Zero downtime."

---

## Metrics & Numbers

- **15 minutes**: Access token expiry
- **7 days**: Refresh token expiry
- **100,000**: PBKDF2 iterations
- **256-bit**: AES key length
- **12 bytes**: IV length (GCM standard)
- **10 requests/15min**: Rate limit
- **~500ms**: Argon2 hashing time (intentional)

---

## What You'd Improve (Always Have This Ready)

1. **Add 2FA/TOTP** - Time-based one-time passwords
2. **Have I Been Pwned integration** - Check passwords against breaches
3. **More test coverage** - End-to-end tests with Playwright
4. **Redis caching** - For rate limiting and sessions
5. **WebAuthn** - Hardware key / biometric support
6. **Session management UI** - Show/revoke active sessions
7. **Monitoring** - Prometheus + Grafana dashboards
8. **Better key derivation** - Argon2 in browser (when available)

---

## Red Flags to Avoid

❌ "It's unhackable" → No system is unhackable
❌ "I didn't have time to add tests" → Shows lack of priorities
❌ "Security wasn't a priority" → For a password manager?!
❌ "I just followed a tutorial" → Shows no deep understanding

## Green Flags to Show

✅ "I chose X because of trade-off Y"
✅ "In production, I'd add Z"
✅ "I validated this against OWASP guidelines"
✅ "Similar to how 1Password does it"
✅ Show enthusiasm and curiosity

---

## One-Minute Project Walkthrough Script

"This is a full-stack password manager I built from scratch. The key innovation is zero-knowledge encryption—users' passwords are encrypted in the browser before ever reaching my server, so even if my database is compromised, the data is useless.

I used Argon2id for password hashing—it's memory-hard and resistant to GPU attacks. For encryption, I used AES-256-GCM, which not only encrypts but also authenticates data integrity.

The backend is Node.js with Express, PostgreSQL for data storage, and JWT for authentication with a refresh token strategy. I implemented rate limiting to prevent brute-force attacks and comprehensive audit logging for security monitoring.

For deployment, everything is containerized with Docker and deployed via GitHub Actions CI/CD. When I push code, tests run automatically, Docker images build, and the new version deploys—usually live in under 5 minutes.

The frontend is vanilla JavaScript using the Web Crypto API for native browser cryptography. Users can register, login, store passwords, and generate secure random passwords—all with client-side encryption.

It demonstrates security engineering, full-stack development, DevOps practices, and an understanding of cryptographic principles. I'd be happy to dive deeper into any aspect."

---

## Handling Tough Questions

### "What don't you know about this?"
"I'm not an expert in formal cryptographic proofs—I rely on vetted algorithms like Argon2 and AES. I also haven't implemented advanced features like hardware key support or social recovery, but I understand the concepts."

### "What would a security audit find?"
"Potentially XSS vulnerabilities in the client code, timing attacks on password comparison (though Argon2 handles this), and maybe insufficient rate limiting granularity. I'd love to have a professional pentest done."

### "Why not use Auth0 or AWS Cognito?"
"Great question—for a real product, I might. But building auth from scratch demonstrates understanding of JWT, refresh tokens, and session management. Plus, for a password manager, zero-knowledge architecture requires custom crypto anyway."

---

## Resources You "Used"

- OWASP Top 10
- NIST Password Guidelines
- Argon2 RFC 9106
- Node.js Security Best Practices
- Let's Encrypt for SSL
- Docker Documentation

---

## Final Prep Checklist

Before the interview:
- [ ] Can explain zero-knowledge in 30 seconds
- [ ] Can draw the architecture diagram
- [ ] Can walk through login flow step-by-step
- [ ] Know why Argon2 > bcrypt
- [ ] Know why AES-GCM (authenticated encryption)
- [ ] Have 3 improvements ready
- [ ] Practiced the 1-minute walkthrough
- [ ] Reviewed the actual code

---

**Print this out and review before your interview! 🚀**
