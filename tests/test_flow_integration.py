"""Full auth + entries flow tests against an in-memory fake DB.

These verify the security-critical behaviour end to end without PostgreSQL:
token rotation, account lockout, enumeration-resistant login, and strict
per-user entry isolation. The real PostgreSQL-backed suite still runs in CI.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from app import app
from src.middleware import audit as audit_module
from src.middleware.rate_limit import limiter
from src.routes import auth as auth_module
from src.routes import entries as entries_module
from tests.fake_db import FakeDB

VALID_PASSWORD = "TestPass1@3$5678XX90"
WRONG_PASSWORD = "WrongPass1@3$5678XX90"

CIPHERTEXT = base64.b64encode(b"x" * 32).decode()
IV = base64.b64encode(b"y" * 12).decode()
TAG = base64.b64encode(b"z" * 16).decode()


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    # Route modules and audit reference db.query / db.execute via the imported
    # module object, so patching those attributes redirects every call.
    for mod in (auth_module.db, entries_module.db, audit_module.db):
        monkeypatch.setattr(mod, "query", db.query)
        monkeypatch.setattr(mod, "execute", db.execute)
    return db


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-memory rate-limit counters so tests do not interfere."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client(fake_db):
    with TestClient(app) as c:
        yield c


def _register(client, username):
    return client.post(
        "/auth/register", json={"username": username, "password": VALID_PASSWORD}
    )


def _login(client, username, password=VALID_PASSWORD):
    return client.post("/auth/login", json={"username": username, "password": password})


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuthFlow:
    def test_register_then_login_returns_tokens_and_salt(self, client):
        assert _register(client, "alice_user").status_code == 201
        resp = _login(client, "alice_user")
        assert resp.status_code == 200
        body = resp.json()
        assert body["accessToken"]
        assert body["refreshToken"]
        assert body["encryption_salt"]

    def test_duplicate_registration_conflicts(self, client):
        _register(client, "dup_user")
        assert _register(client, "dup_user").status_code == 409

    def test_login_unknown_user_is_401_not_404(self, client):
        # Enumeration resistance: same status/message as a wrong password.
        resp = _login(client, "ghost_user")
        assert resp.status_code == 401
        assert resp.json()["error"] == "Invalid credentials"

    def test_login_wrong_password_is_401(self, client):
        _register(client, "bob_user")
        resp = _login(client, "bob_user", WRONG_PASSWORD)
        assert resp.status_code == 401

    def test_refresh_token_rotation_invalidates_old_token(self, client):
        _register(client, "rot_user")
        refresh = _login(client, "rot_user").json()["refreshToken"]

        first = client.post("/auth/token", json={"refreshToken": refresh})
        assert first.status_code == 200

        # The original token must no longer work after rotation.
        reuse = client.post("/auth/token", json={"refreshToken": refresh})
        assert reuse.status_code == 403

    def test_logout_invalidates_refresh_token(self, client):
        _register(client, "out_user")
        refresh = _login(client, "out_user").json()["refreshToken"]
        assert (
            client.post("/auth/logout", json={"refreshToken": refresh}).status_code
            == 200
        )
        assert (
            client.post("/auth/token", json={"refreshToken": refresh}).status_code
            == 403
        )


class TestAccountLockout:
    def test_account_locks_after_repeated_failures(self, client):
        _register(client, "lock_user")
        # Default MAX_FAILED_LOGINS is 5.
        for _ in range(5):
            assert _login(client, "lock_user", WRONG_PASSWORD).status_code == 401
        # 6th attempt — even with the CORRECT password — is locked out.
        locked = _login(client, "lock_user", VALID_PASSWORD)
        assert locked.status_code == 429

    def test_successful_login_resets_failure_counter(self, client):
        _register(client, "reset_user")
        _login(client, "reset_user", WRONG_PASSWORD)
        _login(client, "reset_user", WRONG_PASSWORD)
        assert _login(client, "reset_user", VALID_PASSWORD).status_code == 200
        # Counter reset, so a fresh wrong attempt does not immediately lock.
        assert _login(client, "reset_user", WRONG_PASSWORD).status_code == 401


class TestEntryIsolation:
    def test_full_entry_crud(self, client):
        _register(client, "crud_user")
        token = _login(client, "crud_user").json()["accessToken"]
        h = _auth_headers(token)

        created = client.post(
            "/entries/",
            headers=h,
            json={"name": "GitHub", "ciphertext": CIPHERTEXT, "iv": IV, "tag": TAG},
        )
        assert created.status_code == 201

        listed = client.get("/entries/", headers=h)
        assert listed.status_code == 200
        entries = listed.json()["entries"]
        assert len(entries) == 1
        entry_id = entries[0]["id"]

        updated = client.put(
            f"/entries/{entry_id}",
            headers=h,
            json={"name": "GitHub2", "ciphertext": CIPHERTEXT, "iv": IV, "tag": TAG},
        )
        assert updated.status_code == 200

        deleted = client.delete(f"/entries/{entry_id}", headers=h)
        assert deleted.status_code == 200
        assert client.get("/entries/", headers=h).json()["entries"] == []

    def test_user_cannot_read_another_users_entry(self, client):
        _register(client, "owner_user")
        _register(client, "intruder_user")
        owner_token = _login(client, "owner_user").json()["accessToken"]
        intruder_token = _login(client, "intruder_user").json()["accessToken"]

        client.post(
            "/entries/",
            headers=_auth_headers(owner_token),
            json={"name": "Secret", "ciphertext": CIPHERTEXT, "iv": IV, "tag": TAG},
        )
        entry_id = client.get("/entries/", headers=_auth_headers(owner_token)).json()[
            "entries"
        ][0]["id"]

        # Intruder must get 404 (not the data, not a 403 that confirms existence).
        resp = client.get(f"/entries/{entry_id}", headers=_auth_headers(intruder_token))
        assert resp.status_code == 404

    def test_entry_server_never_sees_plaintext(self, client, fake_db):
        """Zero-knowledge: only ciphertext/iv/tag are persisted."""
        _register(client, "zk_user")
        token = _login(client, "zk_user").json()["accessToken"]
        client.post(
            "/entries/",
            headers=_auth_headers(token),
            json={"name": "Bank", "ciphertext": CIPHERTEXT, "iv": IV, "tag": TAG},
        )
        stored = next(iter(fake_db.entries.values()))
        # Stored bytes equal the supplied ciphertext, not any plaintext.
        assert stored["ciphertext"] == base64.b64decode(CIPHERTEXT)
        assert "plaintext" not in stored


class TestEntryInputValidation:
    def _token(self, client, name):
        _register(client, name)
        return _login(client, name).json()["accessToken"]

    def test_malformed_base64_is_rejected_with_400(self, client):
        token = self._token(client, "b64_user")
        resp = client.post(
            "/entries/",
            headers=_auth_headers(token),
            json={"name": "X", "ciphertext": "not!base64!", "iv": IV, "tag": TAG},
        )
        assert resp.status_code == 400

    def test_oversized_meta_is_rejected(self, client):
        token = self._token(client, "meta_user")
        big_meta = {"blob": "A" * 5000}  # exceeds MAX_META_BYTES
        resp = client.post(
            "/entries/",
            headers=_auth_headers(token),
            json={
                "name": "X",
                "ciphertext": CIPHERTEXT,
                "iv": IV,
                "tag": TAG,
                "meta": big_meta,
            },
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_non_uuid_entry_id_is_rejected_with_422(self, client):
        token = self._token(client, "uuid_user")
        resp = client.get("/entries/not-a-uuid", headers=_auth_headers(token))
        assert resp.status_code == 422
