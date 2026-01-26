# 🚀 Command Cheat Sheet

## Initial Setup Commands

### 1️⃣ Push to GitHub (First Time)
```bash
cd /Users/basitsherazi/Documents/GitHub/Secure-PasswordManager-API

# Stage all files
git add .

# Commit
git commit -m "Initial commit: Secure Password Manager API with CI/CD"

# Add your GitHub repository (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git

# Push to GitHub
git push -u origin main
```

### 2️⃣ Set GitHub Secrets
Go to: `https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/settings/secrets/actions`

Add these 5 secrets:
```
DOCKER_USERNAME       = Your Docker Hub username
DOCKER_PASSWORD       = Your Docker Hub password/token
DEPLOY_HOST          = Your server IP (e.g., 123.45.67.89)
DEPLOY_USER          = SSH username (e.g., ubuntu)
DEPLOY_SSH_KEY       = Your private SSH key content
```

### 3️⃣ Generate SSH Key (if needed)
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy"
cat ~/.ssh/id_ed25519      # Private key (add to DEPLOY_SSH_KEY secret)
cat ~/.ssh/id_ed25519.pub  # Public key (add to server ~/.ssh/authorized_keys)
```

---

## Development Commands

### Local Development (No Docker)
```bash
# Install dependencies
npm install

# Set up environment
cp .env.example .env
nano .env  # Edit DATABASE_URL and secrets

# Run tests
npm test

# Start development server (auto-reload)
npm run dev

# Start production server
npm start
```

---

## Docker Commands

### Local Docker Deployment
```bash
# One-command deploy (auto-generates secrets)
./deploy.sh

# Or manually:
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart
docker-compose restart

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Build & Push Docker Image
```bash
# Build image
docker build -t yourusername/secure-password-manager-api:latest .

# Push to Docker Hub
docker push yourusername/secure-password-manager-api:latest

# Pull image
docker pull yourusername/secure-password-manager-api:latest
```

---

## Server Setup Commands

### Initial Server Setup
```bash
# SSH into server
ssh user@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Create directory
sudo mkdir -p /opt/password-manager-api
sudo chown $USER:$USER /opt/password-manager-api
cd /opt/password-manager-api

# Clone repository
git clone https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git .

# Create environment file
cp .env.production .env
nano .env  # Edit with real values

# Generate secrets
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Start services
docker-compose up -d
```

### Server Management
```bash
# View logs
docker-compose logs -f
docker-compose logs -f api
docker-compose logs -f postgres

# Check status
docker-compose ps

# Restart services
docker-compose restart
docker-compose restart api

# Update to latest version
git pull
docker-compose pull
docker-compose up -d --force-recreate

# Clean up old images
docker image prune -f
```

---

## Database Commands

### Run Migrations
```bash
# Local PostgreSQL
psql $DATABASE_URL -f migrations/001_init.sql
psql $DATABASE_URL -f migrations/002_refresh_audit.sql

# Docker container
docker exec -i password-manager-db psql -U pguser -d passwords_db < migrations/001_init.sql
docker exec -i password-manager-db psql -U pguser -d passwords_db < migrations/002_refresh_audit.sql
```

### Database Access
```bash
# Connect to database
docker exec -it password-manager-db psql -U pguser -d passwords_db

# Run SQL queries
SELECT * FROM users;
SELECT * FROM password_entries;
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;

# Backup database
docker exec password-manager-db pg_dump -U pguser passwords_db > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i password-manager-db psql -U pguser -d passwords_db < backup_20260126.sql
```

---

## Testing Commands

### Run Tests
```bash
# All tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm test -- --coverage

# Specific test file
npm test tests/crypto.test.js
```

### Manual API Testing
```bash
# Health check
curl http://localhost:4000/

# Register user
curl -X POST http://localhost:4000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}'

# Login
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}'

# List entries (replace TOKEN with JWT from login)
curl http://localhost:4000/api/entries \
  -H "Authorization: Bearer TOKEN"
```

---

## Git Commands

### Daily Development
```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "Add feature: description"

# Push to GitHub (triggers auto-deploy!)
git push origin main

# View commit history
git log --oneline

# Create feature branch
git checkout -b feature/new-feature

# Merge to main
git checkout main
git merge feature/new-feature
```

---

## Monitoring Commands

### Check GitHub Actions
```bash
# View in browser
open https://github.com/YOUR_USERNAME/Secure-PasswordManager-API/actions
```

### Server Monitoring
```bash
# CPU and memory usage
docker stats

# Disk usage
df -h
docker system df

# Network connections
ss -tulpn | grep 4000

# Recent logs
docker-compose logs --tail=100

# Follow logs in real-time
docker-compose logs -f api
```

---

## Security Commands

### Generate Secrets
```bash
# JWT secrets
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Random password
node -e "console.log(require('crypto').randomBytes(16).toString('base64'))"
```

### SSL Setup (Let's Encrypt)
```bash
# Install certbot
sudo apt-get install -y certbot

# Get certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Copy to project
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*

# Restart nginx
docker-compose restart nginx
```

### Firewall Setup
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

---

## Troubleshooting Commands

### Check Logs
```bash
# All services
docker-compose logs

# API only
docker-compose logs api

# Database only
docker-compose logs postgres

# Last 50 lines
docker-compose logs --tail=50 api
```

### Debug Container
```bash
# Get shell in API container
docker exec -it password-manager-api sh

# Get shell in database container
docker exec -it password-manager-db bash

# Inspect container
docker inspect password-manager-api
```

### Network Debugging
```bash
# Test API from server
curl http://localhost:4000

# Test database connection
docker exec password-manager-api nc -zv postgres 5432

# Check open ports
sudo netstat -tlnp | grep -E '4000|5432'
```

### Reset Everything
```bash
# Stop and remove all containers, volumes, images
docker-compose down -v
docker system prune -a -f

# Start fresh
docker-compose up -d
```

---

## Quick Reference

```bash
# Deploy locally
./deploy.sh

# Deploy to production (via GitHub)
git push origin main

# View logs
docker-compose logs -f

# Restart API
docker-compose restart api

# Run tests
npm test

# Check status
docker-compose ps

# Database backup
docker exec password-manager-db pg_dump -U pguser passwords_db > backup.sql
```

---

## 📚 See Also

- **QUICKSTART.md** - 5-minute deployment guide
- **DEPLOYMENT.md** - Full CI/CD setup
- **SETUP.md** - API documentation
- **README.md** - Project overview

---

**Tip**: Add these to your shell aliases for faster access!

```bash
# Add to ~/.zshrc or ~/.bashrc
alias pm-logs="docker-compose logs -f"
alias pm-restart="docker-compose restart api"
alias pm-deploy="git add . && git commit -m 'Update' && git push origin main"
```
