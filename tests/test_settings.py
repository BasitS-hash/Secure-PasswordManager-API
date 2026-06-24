"""Tests for fail-fast JWT secret validation in src.settings."""

import importlib

import pytest


def _reload_settings(monkeypatch, secret):
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)
    import src.settings as settings

    return importlib.reload(settings)


class TestJwtSecretValidation:
    def test_missing_secret_raises(self, monkeypatch):
        with pytest.raises(RuntimeError):
            _reload_settings(monkeypatch, None)

    @pytest.mark.parametrize(
        "weak",
        ["your-secret-key-change-me", "change-me-in-production", "secret", "changeme"],
    )
    def test_known_placeholder_raises(self, monkeypatch, weak):
        with pytest.raises(RuntimeError):
            _reload_settings(monkeypatch, weak)

    def test_too_short_secret_raises(self, monkeypatch):
        with pytest.raises(RuntimeError):
            _reload_settings(monkeypatch, "x" * 16)

    def test_strong_secret_loads(self, monkeypatch):
        strong = "a" * 64
        settings = _reload_settings(monkeypatch, strong)
        assert settings.JWT_SECRET == strong

    def teardown_method(self):
        # Restore a valid secret so later modules importing settings still work.
        import os

        os.environ["JWT_SECRET"] = "test-" + "x" * 40
        import src.settings

        importlib.reload(src.settings)
