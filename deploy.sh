#!/bin/bash
set -e

echo "🚀 Deploying Secure Password Manager API..."

# Generate secrets if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.production .env
    
    JWT_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
    REFRESH_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
    DB_PASSWORD=$(node -e "console.log(require('crypto').randomBytes(16).toString('hex'))")
    
    sed -i.bak "s/CHANGE_ME_TO_LONG_RANDOM_STRING/$JWT_SECRET/" .env
    sed -i.bak "s/CHANGE_ME_TO_ANOTHER_RANDOM_STRING/$REFRESH_SECRET/" .env
    sed -i.bak "s/CHANGE_ME_TO_STRONG_PASSWORD/$DB_PASSWORD/" .env
    rm .env.bak
    
    echo "✅ Generated secure secrets in .env"
    echo "⚠️  Please update DOCKER_USERNAME in .env"
fi

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose pull

# Start services
echo "🐳 Starting containers..."
docker-compose up -d

# Wait for database
echo "⏳ Waiting for database..."
sleep 10

# Run migrations
echo "🔧 Running migrations..."
docker exec password-manager-db psql -U pguser -d passwords_db < migrations/001_init.sql 2>/dev/null || true
docker exec password-manager-db psql -U pguser -d passwords_db < migrations/002_refresh_audit.sql 2>/dev/null || true

# Check health
echo "🏥 Health check..."
sleep 5
curl -f http://localhost:4000/ || echo "⚠️  API not responding yet, check logs with: docker-compose logs -f api"

echo "✅ Deployment complete!"
echo "📊 View logs: docker-compose logs -f"
echo "🔍 Check status: docker-compose ps"
echo "🌐 API running at: http://localhost:4000"
