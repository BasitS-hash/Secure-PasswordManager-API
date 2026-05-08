"""
Secure Password Manager API - FastAPI Application
Zero-knowledge password storage with client-side encryption
"""

import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.logger import logger
from src.routes.auth import router as auth_router
from src.routes.entries import router as entries_router
from src.middleware.rate_limit import limiter

load_dotenv()

app = FastAPI(title="Secure Password Manager API", version="1.0.0")

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
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:"
    )
    return response


app.include_router(auth_router)
app.include_router(entries_router)


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if os.path.isdir("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 4000))
    logger.info(f"Starting Secure Password Manager API on port {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
