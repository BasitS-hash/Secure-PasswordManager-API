# 🚀 Quick Start - Go Live in 5 Minutes

## Prerequisites
- GitHub account
- Docker Hub account (free): https://hub.docker.com/signup
- A server with Docker (optional for local testing)

---

## Option 1: 🌐 Deploy to Cloud (Recommended)

### Step 1: Create GitHub Repository
```bash
# Go to https://github.com/new
# Create repository: "Secure-PasswordManager-API"
```

### Step 2: Push Your Code
```bash
cd /Users/basitsherazi/Documents/GitHub/Secure-PasswordManager-API

git add .
git commit -m "Initial commit: Secure Password Manager API with CI/CD"
git remote add origin https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git
git push -u origin main
```

### Step 3: Set Up GitHub Secrets
Go to: `https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/settings/secrets/actions`

Click "New repository secret" and add:

1. **DOCKER_USERNAME** = Your Docker Hub username
2. **DOCKER_PASSWORD** = Your Docker Hub password/token
3. **DEPLOY_HOST** = Your server IP (e.g., `123.45.67.89`)
4. **DEPLOY_USER** = SSH username (e.g., `ubuntu` or `root`)
5. **DEPLOY_SSH_KEY** = Your private SSH key content

### Step 4: Set Up Your Server
```bash
# SSH into your server
ssh user@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Create directory
mkdir -p /opt/password-manager-api
cd /opt/password-manager-api

# Clone your repo
git clone https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git .

# Create .env file
cp .env.production .env
nano .env  # Edit DOCKER_USERNAME and generate secrets
```

### Step 5: Push and Go Live! 🎉
```bash
# Every time you push to main, it auto-deploys!
git push origin main

# GitHub Actions will:
# ✅ Run tests
# ✅ Build Docker image
# ✅ Push to Docker Hub
# ✅ Deploy to your server
```

**Your API is live at:** `http://your-server-ip` or `https://api.yourdomain.com`

---

## Option 2: 💻 Local Testing with Docker

```bash
cd /Users/basitsherazi/Documents/GitHub/Secure-PasswordManager-API

# Run automated deployment
./deploy.sh

# Your API will be running at http://localhost:4000
```

Test it:
```bash
curl http://localhost:4000
```

---

## Option 3: 🖥️ Development Mode (Without Docker)

### Requirements:
- Node.js 18+
- PostgreSQL 15+

```bash
# Install Node.js
brew install node

# Install PostgreSQL
brew install postgresql
brew services start postgresql
createdb passwords_db

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Run migrations
psql passwords_db < migrations/001_init.sql
psql passwords_db < migrations/002_refresh_audit.sql

# Run tests
npm test

# Start development server
npm run dev
```

---

## 🎯 What Happens When You "Go Live"?

```
Push to GitHub main branch
         ↓
   GitHub Actions
         ↓
    Run Tests ✅
         ↓
   Build Docker 🐳
         ↓
  Push to Docker Hub 📦
         ↓
   SSH to Server 🖥️
         ↓
  Pull & Restart 🔄
         ↓
    🎉 LIVE! 🎉
```

---

## 🧪 Test Your Live API

```bash
# Health check
curl http://your-server-ip/

# Register user
curl -X POST http://your-server-ip/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecurePass123!"}'

# Login
curl -X POST http://your-server-ip/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecurePass123!"}'
```

---

## 🔐 Security Checklist Before Going Public

- [ ] Change all default secrets in `.env`
- [ ] Set up HTTPS with Let's Encrypt (see DEPLOYMENT.md)
- [ ] Configure firewall: `sudo ufw allow 80,443/tcp`
- [ ] Set up automated backups
- [ ] Enable monitoring/alerts
- [ ] Use strong database passwords
- [ ] Rotate JWT secrets regularly

---

## 📚 Next Steps

- **Full Deployment Guide**: See `DEPLOYMENT.md`
- **API Documentation**: See `SETUP.md`
- **Setup SSL/HTTPS**: See `DEPLOYMENT.md` → "DNS & SSL Setup"
- **Monitor Logs**: `docker-compose logs -f`

---

## 🆘 Troubleshooting

**GitHub Actions failing?**
- Check Actions tab in your GitHub repo
- Verify all secrets are set correctly

**Can't access API?**
```bash
# Check if running
docker-compose ps

# View logs
docker-compose logs -f api

# Restart
docker-compose restart
```

**Database issues?**
```bash
# Check database logs
docker-compose logs postgres

# Run migrations manually
docker exec -i password-manager-db psql -U pguser -d passwords_db < migrations/001_init.sql
```

---

## ✅ You're Ready!

Choose your deployment option above and go live! 🚀

For detailed instructions, see **DEPLOYMENT.md**.
