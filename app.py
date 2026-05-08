"""
Secure Password Manager API - FastAPI Application
Zero-knowledge password storage with client-side encryption
"""

import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.logger import logger
from src.routes.auth import router as auth_router
from src.routes.entries import router as entries_router
from src.middleware.rate_limit import limiter

load_dotenv()

description = """
**Created by Syed Basit Sherazi**

A secure, zero-knowledge password manager API with client-side AES-256-GCM encryption.

## Purpose

This project demonstrates secure API design principles including JWT authentication with token rotation,
zero-knowledge architecture, AES-256-GCM encryption, audit logging, and rate limiting —
built as a portfolio project to showcase backend security engineering skills.

---

## How to Authenticate

1. **Register** — `POST /auth/register` with a `username` and `password` (min 20 chars, must include uppercase, lowercase, digit, and special character)
2. **Login** — `POST /auth/login` — returns an `accessToken`, `refreshToken`, and `encryption_salt`
3. **Authorize** — click the **Authorize** button at the top of this page, enter `Bearer <your accessToken>`
4. All `/entries` endpoints are now unlocked

Access tokens expire in 35 minutes. Use `POST /auth/token` with your `refreshToken` to get a new one.

---

## How Zero-Knowledge Encryption Works

Your passwords are **never stored in plaintext** — not even on the server.

1. When you log in, the server returns an `encryption_salt` unique to your account
2. Your client combines your master password + salt to derive a 256-bit AES key (this never leaves your device)
3. Each password entry is encrypted with AES-256-GCM **before** being sent to the API
4. The server stores only the encrypted `ciphertext`, `iv`, and `tag` — it cannot decrypt them
5. Decryption happens on your device using the same derived key

This means even if the database is compromised, your passwords are safe.
"""

app = FastAPI(
    title="Secure Password Manager API",
    version="1.0.0",
    description=description,
    contact={"name": "Syed Basit Sherazi"},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:"
    )
    return response


app.include_router(auth_router)
app.include_router(entries_router)


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 4000))
    logger.info(f"Starting Secure Password Manager API on port {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
