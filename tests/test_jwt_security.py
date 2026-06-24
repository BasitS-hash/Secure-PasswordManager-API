"""Tests for JWT issuance and verification hardening."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.middleware.auth import get_current_user
from src.routes.auth import make_access_token
from src.settings import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestJwtVerification:
    def test_valid_token_is_accepted(self):
        now = datetime.now(timezone.utc)
        token = make_access_token("user-123", "alice", now)
        claims = get_current_user(_creds(token))
        assert claims["sub"] == "user-123"
        assert claims["iss"] == JWT_ISSUER
        assert claims["aud"] == JWT_AUDIENCE

    def test_missing_credentials_returns_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_user(None)
        assert exc.value.status_code == 401

    def test_token_signed_with_wrong_secret_is_rejected(self):
        now = datetime.now(timezone.utc)
        forged = jwt.encode(
            {
                "sub": "attacker",
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            "attacker-controlled-secret-which-is-also-long-enough-32",
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            get_current_user(_creds(forged))
        assert exc.value.status_code == 403

    def test_none_algorithm_token_is_rejected(self):
        # Classic alg=none downgrade attempt.
        forged = jwt.encode(
            {"sub": "attacker", "iss": JWT_ISSUER, "aud": JWT_AUDIENCE},
            key="",
            algorithm="none",
        )
        with pytest.raises(HTTPException):
            get_current_user(_creds(forged))

    def test_expired_token_is_rejected(self):
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        expired = jwt.encode(
            {
                "sub": "user",
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "iat": past,
                "exp": past + timedelta(minutes=5),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            get_current_user(_creds(expired))
        assert exc.value.status_code == 403

    def test_wrong_issuer_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "user",
                "iss": "evil-issuer",
                "aud": JWT_AUDIENCE,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException):
            get_current_user(_creds(token))

    def test_wrong_audience_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "user",
                "iss": JWT_ISSUER,
                "aud": "some-other-app",
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException):
            get_current_user(_creds(token))

    def test_token_missing_required_claims_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {"iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "exp": now + timedelta(minutes=5)},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )  # no "sub"
        with pytest.raises(HTTPException):
            get_current_user(_creds(token))
