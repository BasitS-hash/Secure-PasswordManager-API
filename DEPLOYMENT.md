# 🚀 Deployment Guide - GitHub Actions CI/CD

This project includes automated deployment using **GitHub Actions**. When you push to the `main` branch, it automatically:
1. ✅ Runs tests
2. 🐳 Builds Docker image
3. 📦 Pushes to Docker Hub
4. 🚀 Deploys to your server

## 📋 Prerequisites

You need:
- A GitHub repository for this project
- A Docker Hub account
- A server with Docker installed (VPS, AWS EC2, DigitalOcean, etc.)

---

## 🔧 Setup Instructions

### Step 1: Push to GitHub

```bash
cd /Users/basitsherazi/Documents/GitHub/Secure-PasswordManager-API

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Secure Password Manager API"

# Add your GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git
git branch -M main
git push -u origin main
```

### Step 2: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

#### Required Secrets:

1. **DOCKER_USERNAME**
   - Your Docker Hub username
   - Example: `johndoe`

2. **DOCKER_PASSWORD**
   - Your Docker Hub password or access token
   - Generate token at: https://hub.docker.com/settings/security

3. **DEPLOY_HOST**
   - Your server IP address or domain
   - Example: `123.45.67.89` or `api.yourdomain.com`

4. **DEPLOY_USER**
   - SSH username for your server
   - Example: `ubuntu` or `root`

5. **DEPLOY_SSH_KEY**
   - Your private SSH key for server access
   - Generate with: `ssh-keygen -t ed25519 -C "github-actions"`
   - Copy the **private key** content (file: `~/.ssh/id_ed25519`)
   - Add the **public key** to your server: `~/.ssh/authorized_keys`

### Step 3: Set Up Your Server

SSH into your server and run:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Create deployment directory
sudo mkdir -p /opt/password-manager-api
sudo chown $USER:$USER /opt/password-manager-api
cd /opt/password-manager-api

# Copy files from your repo
# You can manually copy or use git clone
git clone https://github.com/YOUR_USERNAME/Secure-PasswordManager-API.git .

# Create production .env file
cp .env.production .env
nano .env  # Edit with your real values
```

Edit `.env` with real values:
```bash
DOCKER_USERNAME=your_dockerhub_username
DB_USER=pguser
DB_PASSWORD=your_strong_database_password_here
JWT_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
REFRESH_TOKEN_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
```

### Step 4: Initial Server Setup

On your server, start the services:

```bash
cd /opt/password-manager-api

# Build locally first time (or wait for GitHub Actions)
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify it's running
curl http://localhost:4000
```

### Step 5: Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 🎯 How It Works

### Automatic Deployment Flow:

```
1. You push code to GitHub (main branch)
   ↓
2. GitHub Actions triggers
   ↓
3. Runs tests with PostgreSQL
   ↓
4. Builds Docker image
   ↓
5. Pushes image to Docker Hub
   ↓
6. SSHs into your server
   ↓
7. Pulls new image
   ↓
8. Restarts containers
   ↓
9. ✅ Your API is live!
```

### Workflow File Location:
`.github/workflows/deploy.yml`

---

## 🌐 DNS & SSL Setup (Optional but Recommended)

### Configure DNS:
1. Point your domain A record to your server IP
   - Example: `api.yourdomain.com` → `123.45.67.89`

2. Wait for DNS propagation (5-30 minutes)

### Add SSL Certificate (Let's Encrypt):

```bash
# On your server
cd /opt/password-manager-api

# Install certbot
sudo apt-get install -y certbot

# Get certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Copy certificates
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ssl/key.pem
sudo chown -R $USER:$USER ssl

# Update nginx.conf to enable HTTPS (uncomment the HTTPS server block)
nano nginx.conf

# Restart nginx
docker-compose restart nginx
```

---

## 🔄 Manual Deployment Commands

If you want to deploy manually without GitHub Actions:

```bash
# On your local machine
docker build -t yourusername/secure-password-manager-api:latest .
docker push yourusername/secure-password-manager-api:latest

# On your server
cd /opt/password-manager-api
docker-compose pull
docker-compose up -d --force-recreate
```

---

## 📊 Monitoring & Logs

### View logs:
```bash
# All services
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just database
docker-compose logs -f postgres
```

### Check service status:
```bash
docker-compose ps
```

### View audit logs:
```bash
# Connect to database
docker exec -it password-manager-db psql -U pguser -d passwords_db

# Query audit logs
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 20;
```

---

## 🔐 Security Best Practices

### 1. Rotate Secrets Regularly
```bash
# Generate new secrets
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Update .env on server
# Update GitHub secrets
```

### 2. Enable HTTPS (Required for production!)
- Follow SSL setup above
- Never run production API over HTTP

### 3. Set Up Monitoring
- Consider adding: Prometheus, Grafana, or cloud monitoring
- Set up alerts for downtime

### 4. Backup Database
```bash
# Automated daily backups
docker exec password-manager-db pg_dump -U pguser passwords_db > backup_$(date +%Y%m%d).sql

# Add to crontab
0 2 * * * cd /opt/password-manager-api && docker exec password-manager-db pg_dump -U pguser passwords_db > backups/backup_$(date +\%Y\%m\%d).sql
```

---

## 🧪 Testing the Deployment

Once deployed, test your API:

```bash
# Health check
curl http://your-server-ip/

# Register a user
curl -X POST http://your-server-ip/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!@#"}'

# Login
curl -X POST http://your-server-ip/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!@#"}'
```

---

## 🆘 Troubleshooting

### GitHub Actions fails:
- Check GitHub Actions logs in your repository
- Verify all secrets are set correctly
- Ensure SSH key has proper permissions on server

### Container won't start:
```bash
docker-compose logs api
# Check for environment variable errors or database connection issues
```

### Can't connect to API:
```bash
# Check if containers are running
docker-compose ps

# Check if port is open
sudo netstat -tlnp | grep 4000

# Check firewall
sudo ufw status
```

### Database migration errors:
```bash
# Run migrations manually
docker exec -i password-manager-db psql -U pguser -d passwords_db < migrations/001_init.sql
docker exec -i password-manager-db psql -U pguser -d passwords_db < migrations/002_refresh_audit.sql
```

---

## 📈 Scaling Options

### Option 1: Horizontal Scaling (Multiple Servers)
- Add load balancer (nginx, HAProxy)
- Share PostgreSQL database
- Use Redis for session storage

### Option 2: Managed Services
- **Database**: AWS RDS, DigitalOcean Managed PostgreSQL
- **Container**: AWS ECS, Google Cloud Run, Azure Container Instances
- **Load Balancer**: AWS ALB, Cloudflare

### Option 3: Kubernetes
- Convert docker-compose to k8s manifests
- Use Helm charts
- Auto-scaling based on load

---

## ✅ Post-Deployment Checklist

- [ ] GitHub Actions workflow runs successfully
- [ ] API responds at http://your-server-ip
- [ ] Database migrations applied
- [ ] SSL certificate installed (for production)
- [ ] Firewall configured
- [ ] Backup system in place
- [ ] Monitoring/alerting configured
- [ ] Documentation updated with your domain

---

## 🎉 You're Live!

Every time you push to `main`, your changes will automatically deploy!

```bash
# Make changes
git add .
git commit -m "Add new feature"
git push origin main

# GitHub Actions will automatically:
# ✅ Test
# ✅ Build
# ✅ Deploy
```

Your API will be live at: `http://your-server-ip` or `https://api.yourdomain.com`

For questions or issues, check the GitHub Actions logs or server logs.
