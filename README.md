# 🔐 Secure Password Manager API

[![Deploy](https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/actions)

A production-ready REST API **with beautiful web interface** for securely storing and managing passwords with **zero-knowledge architecture** and industry-standard encryption.

## ✨ Features

- 🌐 **Beautiful Web Interface** - Modern landing page + interactive password manager
- 🔒 **Zero-Knowledge Storage** - Server never sees plaintext passwords
- 🛡️ **Argon2id Hashing** - Memory-hard, GPU-resistant master password protection
- 🔐 **AES-256-GCM Encryption** - Client-side authenticated encryption
- 🎫 **JWT Authentication** - Secure access + refresh token system
- 🚦 **Rate Limiting** - Built-in brute force protection
- 📊 **Audit Logging** - Complete access history with IP tracking
- 🎲 **Password Generator** - Cryptographically secure random passwords
- 📈 **Entropy Analyzer** - Password strength estimation
- 🐳 **Docker Ready** - One-command deployment
- 🚀 **CI/CD Pipeline** - Auto-deploy on push to main

## 🌐 Live Demo Features

When deployed, users get:
- **Landing Page** - Professional introduction to features
- **Web App** - Full password manager in the browser
- **Register/Login** - User account management
- **Password Vault** - Store & manage encrypted passwords
- **API Docs** - Complete endpoint reference

## 🚀 Quick Start

### Option 1: Deploy to Cloud (Recommended)
```bash
# Push to GitHub
git push origin main

# GitHub Actions automatically:
# ✅ Tests → 🐳 Builds → 📦 Deploys
```
**See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup!**

### Option 2: Run Locally with Docker
```bash
./deploy.sh
# Visit http://localhost:4000
```

### Option 3: Development Mode
```bash
npm install
cp .env.example .env
npm run dev
# Visit http://localhost:4000
```

## 📚 Documentation

- **[WEBSITE.md](WEBSITE.md)** - Website features & how it works
- **[QUICKSTART.md](QUICKSTART.md)** - Go live in 5 minutes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full CI/CD setup guide
- **[SETUP.md](SETUP.md)** - Detailed API usage & architecture
- **[COMMANDS.md](COMMANDS.md)** - Command reference

## 🏗️ Tech Stack

- **Backend**: Node.js 20 + Express 4.18
- **Database**: PostgreSQL 15 with encrypted fields
- **Security**: Argon2id, AES-256-GCM, JWT, Helmet
- **Testing**: Jest + Supertest
- **Deployment**: Docker + GitHub Actions
- **Proxy**: Nginx with rate limiting

## 🔐 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | ❌ | Register new user |
| `/api/auth/login` | POST | ❌ | Login (returns JWT + salt) |
| `/api/auth/token` | POST | ❌ | Refresh access token |
| `/api/auth/logout` | POST | ❌ | Invalidate refresh token |
| `/api/entries` | POST | ✅ | Create password entry |
| `/api/entries` | GET | ✅ | List password entries |

## 🔒 Zero-Knowledge Architecture

```
Master Password + Salt → [Argon2id] → Encryption Key (32 bytes)
                                            ↓
Password Entry → [AES-256-GCM] → Ciphertext + IV + Tag
                                            ↓
                                    Store in Database
```

**Server never sees plaintext!** All encryption/decryption happens client-side.

## 🧪 Testing

```bash
npm test  # Run all tests
```

Tests include:
- ✅ AES-GCM encryption/decryption roundtrip
- ✅ Password generator validation
- ✅ Entropy calculation
- ✅ API endpoint smoke tests

## 📦 Project Structure

```
├── .github/workflows/deploy.yml  # CI/CD pipeline
├── client/crypto_demo.js         # Zero-knowledge helpers
├── migrations/                   # Database schema
├── src/
│   ├── routes/                   # Auth & entries endpoints
│   ├── middleware/               # JWT, rate limiting, audit
│   └── utils/                    # Crypto & password tools
├── tests/                        # Jest test suite
├── docker-compose.yml            # Multi-container setup
├── nginx.conf                    # Reverse proxy config
└── deploy.sh                     # One-command deployment
```

## 🌐 Environment Variables

```env
DATABASE_URL=postgres://user:pass@localhost:5432/passwords_db
PORT=4000
JWT_SECRET=your_32_byte_random_secret
REFRESH_TOKEN_SECRET=another_32_byte_random_secret
ACCESS_TOKEN_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
```

Generate secrets:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🆘 Support

- 📖 [Full Documentation](SETUP.md)
- 🚀 [Deployment Guide](DEPLOYMENT.md)
- ⚡ [Quick Start](QUICKSTART.md)
- 🐛 [Report Issues](https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/issues)

---

**Built with ❤️ for cybersecurity professionals**
