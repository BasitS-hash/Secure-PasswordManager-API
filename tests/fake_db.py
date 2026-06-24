"""An in-memory stand-in for src.db used by integration tests.

It implements just enough of the query/execute contract that the auth and
entries routes rely on, so the full security-relevant flow (registration,
login, token rotation, account lockout, per-user entry isolation) can be
exercised without a real PostgreSQL instance. The real DB-backed tests still
run against PostgreSQL in CI.
"""

import uuid
from datetime import datetime, timezone


class FakeDB:
    def __init__(self):
        self.users = {}  # id -> dict
        self.users_by_name = {}  # username -> id
        self.refresh_tokens = {}  # token_hash -> dict
        self.entries = {}  # id -> dict
        self.audit = []

    # --- helpers -----------------------------------------------------------
    def _now(self):
        return datetime.now(timezone.utc)

    # --- query/execute -----------------------------------------------------
    def query(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())

        if s.startswith("INSERT INTO users") and "RETURNING" in s:
            username, password_hash, salt = params
            if username in self.users_by_name:
                raise Exception("duplicate username")
            uid = str(uuid.uuid4())
            self.users[uid] = {
                "id": uid,
                "username": username,
                "password_hash": password_hash,
                "encryption_salt": salt,
                "failed_login_attempts": 0,
                "locked_until": None,
            }
            self.users_by_name[username] = uid
            return [{"id": uid, "username": username}]

        if s.startswith("SELECT id, password_hash, encryption_salt"):
            (username,) = params
            uid = self.users_by_name.get(username)
            if not uid:
                return []
            u = self.users[uid]
            return [dict(u)]

        if s.startswith("SELECT user_id, expires_at FROM refresh_tokens"):
            (token_hash,) = params
            rec = self.refresh_tokens.get(token_hash)
            return [dict(rec)] if rec else []

        # Atomic refresh-token rotation (DELETE old + INSERT new in one CTE).
        if s.startswith("WITH old AS") and "DELETE FROM refresh_tokens" in s:
            old_hash, now, new_hash, new_expires = params
            rec = self.refresh_tokens.get(old_hash)
            if not rec:
                return []
            expires_at = rec["expires_at"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                return []
            user_id = rec["user_id"]
            del self.refresh_tokens[old_hash]
            self.refresh_tokens[new_hash] = {
                "user_id": user_id,
                "expires_at": new_expires,
            }
            return [{"user_id": user_id}]

        if s.startswith("SELECT username FROM users WHERE id"):
            (uid,) = params
            u = self.users.get(uid)
            return [{"username": u["username"]}] if u else []

        if s.startswith("SELECT id FROM password_entries WHERE id"):
            entry_id, user_id = params
            e = self.entries.get(entry_id)
            if e and e["user_id"] == user_id:
                return [{"id": entry_id}]
            return []

        if "FROM password_entries" in s and "WHERE user_id" in s and "ORDER BY" in s:
            (user_id,) = params
            rows = [
                self._entry_row(e)
                for e in self.entries.values()
                if e["user_id"] == user_id
            ]
            return rows

        if "FROM password_entries" in s and "WHERE id" in s and "AND user_id" in s:
            entry_id, user_id = params
            e = self.entries.get(entry_id)
            if e and e["user_id"] == user_id:
                return [self._entry_row(e)]
            return []

        return []

    def _entry_row(self, e):
        import base64

        return {
            "id": e["id"],
            "name": e["name"],
            "ciphertext": base64.b64encode(e["ciphertext"]).decode(),
            "iv": base64.b64encode(e["iv"]).decode(),
            "tag": base64.b64encode(e["tag"]).decode(),
            "meta": e.get("meta"),
            "created_at": e["created_at"].isoformat(),
            "updated_at": e.get("updated_at"),
        }

    def execute(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())

        if s.startswith("INSERT INTO refresh_tokens"):
            user_id, token_hash, expires_at = params
            self.refresh_tokens[token_hash] = {
                "user_id": user_id,
                "expires_at": expires_at,
            }
            return 1

        if s.startswith("DELETE FROM refresh_tokens"):
            (token_hash,) = params
            return 1 if self.refresh_tokens.pop(token_hash, None) else 0

        if (
            s.startswith("UPDATE users")
            and "failed_login_attempts = failed_login_attempts + 1" in s
        ):
            max_failed, lock_until, user_id = params
            u = self.users[user_id]
            u["failed_login_attempts"] += 1
            if u["failed_login_attempts"] >= max_failed:
                u["locked_until"] = lock_until
            return 1

        if s.startswith("UPDATE users SET failed_login_attempts = 0"):
            (user_id,) = params
            u = self.users[user_id]
            u["failed_login_attempts"] = 0
            u["locked_until"] = None
            return 1

        if s.startswith("UPDATE users SET password_hash"):
            password_hash, user_id = params
            self.users[user_id]["password_hash"] = password_hash
            return 1

        if s.startswith("INSERT INTO password_entries"):
            user_id, name, ciphertext, iv, tag, meta = params
            eid = str(uuid.uuid4())
            self.entries[eid] = {
                "id": eid,
                "user_id": user_id,
                "name": name,
                "ciphertext": ciphertext,
                "iv": iv,
                "tag": tag,
                "meta": meta,
                "created_at": self._now(),
                "updated_at": None,
            }
            return 1

        if s.startswith("UPDATE password_entries"):
            name, ciphertext, iv, tag, meta, entry_id, user_id = params
            e = self.entries.get(entry_id)
            if e and e["user_id"] == user_id:
                e.update(
                    name=name,
                    ciphertext=ciphertext,
                    iv=iv,
                    tag=tag,
                    meta=meta,
                    updated_at=self._now(),
                )
                return 1
            return 0

        if s.startswith("DELETE FROM password_entries"):
            entry_id, user_id = params
            e = self.entries.get(entry_id)
            if e and e["user_id"] == user_id:
                del self.entries[entry_id]
                return 1
            return 0

        if s.startswith("INSERT INTO audit_logs"):
            self.audit.append(params)
            return 1

        return 0
