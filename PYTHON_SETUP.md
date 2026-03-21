# Python Setup Guide

This project has been converted from Node.js/Express to Python/Flask.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip

## Installation

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/password_manager
JWT_SECRET=your-super-secret-jwt-key-change-this
PORT=4000
DEBUG=false
ACCESS_TOKEN_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
```

### 4. Database Setup

Initialize the PostgreSQL database:

```bash
psql -U postgres -d password_manager -f migrations/001_init.sql
psql -U postgres -d password_manager -f migrations/002_refresh_audit.sql
```

## Running the Application

### Development Mode

```bash
python app.py
```

The API will be available at `http://localhost:4000`

### Run with Flask Development Server

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_crypto.py

# Run with coverage
pytest --cov=src tests/
```

## Project Structure

```
app.py                          # Main Flask application entry point
requirements.txt                # Python dependencies
pytest.ini                      # Pytest configuration
src/
  app.py                        # Flask app factory (MOVED to root)
  logger.py                     # Logging configuration
  db.py                         # Database connection utilities
  middleware/
    auth.py                     # JWT authentication decorator
    audit.py                    # Audit logging middleware
    rate_limit.py              # Rate limiting configuration
  routes/
    auth.py                    # Authentication endpoints
    entries.py                 # Password entry endpoints
  utils/
    crypto.py                  # AES-256-GCM encryption utilities
    passwords.py               # Password generation utilities
tests/
  test_api.py                  # API endpoint tests
  test_crypto.py              # Cryptographic utility tests
migrations/
  001_init.sql                 # Initial database schema
  002_refresh_audit.sql        # Audit log table schema
public/
  index.html                   # Frontend HTML
  app.js                       # Client-side application
  docs.html                    # API documentation
```

## Key Differences from Node.js Version

1. **Framework**: Express.js → Flask
2. **Async/Await**: Python async/await (native)
3. **Password Hashing**: `argon2` npm → `argon2-cffi` pip
4. **JWT**: `jsonwebtoken` → `PyJWT`
5. **Database**: `pg` → `psycopg2`
6. **Testing**: Jest → Pytest
7. **Dependency Management**: npm → pip
8. **Rate Limiting**: `express-rate-limit` → `Flask-Limiter`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/token` - Refresh access token
- `POST /auth/logout` - Logout user

### Password Entries
- `POST /entries/` - Create new password entry
- `GET /entries/` - List all password entries

### Health
- `GET /health` - Health check endpoint

## Security Features

- **Argon2ID** password hashing
- **AES-256-GCM** encryption
- **JWT** tokens with configurable expiry
- **Rate limiting** on auth endpoints
- **Audit logging** of all actions
- **CORS headers** and security policies
- **Zero-knowledge architecture** (encryption happens client-side)

## Testing

The test suite includes:

- Cryptographic function tests
- Password generation and entropy tests
- API endpoint tests
- Authentication tests
- Error handling tests

## Troubleshooting

### Import Errors
If you see import errors, ensure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### Database Connection Issues
Check your DATABASE_URL in the .env file and ensure PostgreSQL is running:
```bash
psql -U postgres -c "SELECT 1"
```

### Port Already in Use
Change the PORT in .env or run on a different port:
```bash
export PORT=5000
python app.py
```

## Migration from Node.js

If you were previously running the Node.js version, here's what changed:

1. Replace `npm install` with `pip install -r requirements.txt`
2. Replace `npm start` with `python app.py`
3. Replace `npm test` with `pytest`
4. Database schemas remain the same (same migrations)
5. Frontend (public/) and migrations remain unchanged

## Performance Notes

- Flask is running in debug mode by default for development
- For production, use a WSGI server like Gunicorn:
  ```bash
  pip install gunicorn
  gunicorn -w 4 app:app
  ```

- Rate limiting is configured for 10 requests per 15 minutes on auth endpoints
- Database connection pooling can be configured in `src/db.py` if needed

## License

MIT
