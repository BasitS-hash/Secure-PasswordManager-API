# Python Conversion Reference Guide

Quick reference for using the Python version of Secure Password Manager API.

## Installation & Setup

### One-Time Setup
```bash
# 1. Run the setup script
bash setup.sh

# 2. Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Initialize database
psql -U postgres -d password_manager -f migrations/001_init.sql
psql -U postgres -d password_manager -f migrations/002_refresh_audit.sql
```

## Running the Application

### Development
```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python app.py
# API available at http://localhost:4000
```

### Production
```bash
# Using Gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:4000 app:app
```

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src tests/

# Run specific test file
pytest tests/test_crypto.py

# Run specific test
pytest tests/test_api.py::TestAuthEndpoints::test_login_requires_username_and_password
```

## API Usage Examples

### Register
```bash
curl -X POST http://localhost:4000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"SecurePassword123!"}'
```

### Login
```bash
curl -X POST http://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"SecurePassword123!"}'
```

### Create Password Entry
```bash
curl -X POST http://localhost:4000/entries/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Gmail",
    "ciphertext": "base64-encoded-ciphertext",
    "iv": "base64-encoded-iv",
    "tag": "base64-encoded-tag"
  }'
```

### List Password Entries
```bash
curl -X GET http://localhost:4000/entries/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Refresh Token
```bash
curl -X POST http://localhost:4000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"YOUR_REFRESH_TOKEN"}'
```

### Logout
```bash
curl -X POST http://localhost:4000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"YOUR_REFRESH_TOKEN"}'
```

## Project Files

### Core Application
- `app.py` - Flask application entry point
- `config.py` - Configuration management
- `.env` - Environment variables (create from .env.example)

### Source Code (`src/`)
- `db.py` - Database utilities
- `logger.py` - Logging configuration
- `routes/auth.py` - Authentication endpoints
- `routes/entries.py` - Password entry endpoints
- `middleware/auth.py` - JWT authentication
- `middleware/audit.py` - Audit logging
- `middleware/rate_limit.py` - Rate limiting
- `utils/crypto.py` - Encryption utilities
- `utils/passwords.py` - Password generation

### Tests (`tests/`)
- `test_api.py` - API endpoint tests
- `test_crypto.py` - Cryptography utility tests

### Database (`migrations/`)
- `001_init.sql` - Initial schema
- `002_refresh_audit.sql` - Audit tables

### Frontend (`public/`)
- `index.html` - Main page
- `app.js` - Client-side application
- `docs.html` - API documentation

## Common Issues & Solutions

### Issue: "No module named 'flask'"
**Solution:** Ensure virtual environment is activated
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "could not connect to database"
**Solution:** Check DATABASE_URL in .env
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: "Address already in use"
**Solution:** Change PORT in .env or kill existing process
```bash
export PORT=5000
python app.py
```

### Issue: "permission denied" on setup.sh
**Solution:** Make script executable
```bash
chmod +x setup.sh
./setup.sh
```

## Configuration

### .env Variables
```
DATABASE_URL              - PostgreSQL connection string
JWT_SECRET               - Secret for JWT tokens (CHANGE THIS!)
PORT                     - Server port (default: 4000)
DEBUG                    - Enable debug mode (true/false)
ACCESS_TOKEN_EXPIRES_IN  - How long access tokens last (e.g., "15m")
REFRESH_TOKEN_EXPIRES_IN - How long refresh tokens last (e.g., "7d")
LOG_LEVEL                - Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Code Configuration (config.py)
```python
from config import get_config

config = get_config()  # Returns config for current FLASK_ENV
config.DATABASE_URL
config.JWT_SECRET
config.PORT
config.DEBUG
```

## Database

### Schema Management
```bash
# Initialize database
psql -U postgres -d password_manager -f migrations/001_init.sql
psql -U postgres -d password_manager -f migrations/002_refresh_audit.sql

# Reset database (⚠️ deletes all data)
dropdb password_manager
createdb password_manager
psql -U postgres -d password_manager -f migrations/001_init.sql
psql -U postgres -d password_manager -f migrations/002_refresh_audit.sql
```

### Query Examples
```bash
# Connect to database
psql $DATABASE_URL

# View users
SELECT id, username, created_at FROM users;

# View audit logs
SELECT user_id, action, success, created_at FROM audit_logs ORDER BY created_at DESC;

# View password entries count
SELECT COUNT(*) FROM password_entries;
```

## Development Workflow

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env File
```bash
cp .env.example .env
# Edit with your settings
```

### 3. Initialize Database
```bash
psql -U postgres -d password_manager -f migrations/001_init.sql
```

### 4. Run Tests
```bash
pytest
```

### 5. Start Development Server
```bash
python app.py
```

### 6. Access Application
- API: http://localhost:4000
- Frontend: http://localhost:4000/

## Docker Setup (Optional)

### Build Image
```bash
docker build -t password-manager-api .
```

### Run Container
```bash
docker run -p 4000:4000 \
  -e DATABASE_URL="postgresql://..." \
  -e JWT_SECRET="your-secret" \
  password-manager-api
```

### Using Docker Compose
```bash
docker-compose up -d
```

## Security Notes

- **JWT_SECRET**: Change this to a random, secure value in production
- **Database Password**: Use a strong password
- **SSL/TLS**: Use HTTPS in production
- **Rate Limiting**: Currently 10 requests per 15 minutes on auth endpoints
- **Encryption**: All passwords are encrypted client-side before sending to server
- **Hashing**: Server-side passwords use Argon2ID with default parameters

## Performance Tuning

### Development
```python
# Auto-reload on file changes
DEBUG = true
```

### Production
```bash
# Use Gunicorn with multiple workers
gunicorn -w 4 -b 0.0.0.0:4000 --timeout 120 app:app
```

## Deployment Checklist

- [ ] Change JWT_SECRET in .env
- [ ] Set DEBUG=false in .env
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure rate limiting appropriately
- [ ] Set up monitoring and alerting
- [ ] Use Gunicorn or similar WSGI server
- [ ] Put behind Nginx reverse proxy
- [ ] Configure logging to file or centralized service

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install new package
pip install package_name

# Save current dependencies
pip freeze > requirements.txt

# Check Python version
python --version

# Run specific test
pytest tests/test_api.py::TestAuthEndpoints

# Run tests with coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# View logs
tail -f logs/app.log

# Test database connection
python -c "import psycopg2; conn = psycopg2.connect('DATABASE_URL'); print('Connected!')"
```

## Debugging

### Enable Verbose Logging
```python
# In .env
LOG_LEVEL=DEBUG
DEBUG=true
```

### Print Debug Info
```python
# In route handlers
from src.logger import logger
logger.debug(f"Variable: {variable}")
```

### Connect to Database Directly
```bash
psql $DATABASE_URL
```

### Check Server Status
```bash
curl http://localhost:4000/health
```

## Documentation

- `PYTHON_SETUP.md` - Detailed setup guide
- `NODE_TO_PYTHON_MAPPING.md` - Conversion details
- `PYTHON_CONVERSION_COMPLETE.md` - Conversion summary
- `config.py` - Configuration options
- Source code docstrings - Implementation details

## Getting Help

1. Check the documentation files listed above
2. Review test files for usage examples
3. Check existing issues or logs
4. Review Python Secure Password Manager API documentation

---

**Version:** Python 3.8+  
**Framework:** Flask 3.0.0  
**Database:** PostgreSQL 12+  
**Last Updated:** March 21, 2026
