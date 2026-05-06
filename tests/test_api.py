"""
API integration tests for the Secure Password Manager.
"""

import pytest
from flask import Flask
from app import app as flask_app


@pytest.fixture
def client():
    """Create a test client."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_register_requires_username_and_password(self, client):
        response = client.post('/auth/register', json={})
        assert response.status_code == 400
        assert 'username and password required' in response.json['error']

    def test_login_requires_username_and_password(self, client):
        response = client.post('/auth/login', json={})
        assert response.status_code == 400
        assert 'username and password required' in response.json['error']

    def test_register_rejects_short_password(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'Short1@'
        })
        assert response.status_code == 400
        assert 'at least 20 characters' in response.json['error']

    def test_register_rejects_password_without_uppercase(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'alllowercase1@3$567890'
        })
        assert response.status_code == 400
        assert 'uppercase' in response.json['error']

    def test_register_rejects_password_without_special_char(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'NoSpecialChar12345678'
        })
        assert response.status_code == 400
        assert 'special character' in response.json['error']

    def test_register_rejects_invalid_username(self, client):
        response = client.post('/auth/register', json={
            'username': 'ab',
            'password': 'ValidPass1@3$567890XX'
        })
        assert response.status_code == 400
        assert 'Username' in response.json['error']


class TestEntriesEndpoints:
    """Test password entry endpoints."""

    def test_get_entries_without_auth_returns_401(self, client):
        response = client.get('/entries/')
        assert response.status_code == 401
        assert 'error' in response.json

    def test_create_entry_without_auth_returns_401(self, client):
        response = client.post('/entries/', json={
            'name': 'test', 'ciphertext': 'xyz', 'iv': 'abc', 'tag': 'def'
        })
        assert response.status_code == 401

    def test_get_entry_by_id_without_auth_returns_401(self, client):
        response = client.get('/entries/some-uuid')
        assert response.status_code == 401

    def test_update_entry_without_auth_returns_401(self, client):
        response = client.put('/entries/some-uuid', json={
            'name': 'test', 'ciphertext': 'xyz', 'iv': 'abc', 'tag': 'def'
        })
        assert response.status_code == 401

    def test_delete_entry_without_auth_returns_401(self, client):
        response = client.delete('/entries/some-uuid')
        assert response.status_code == 401


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint_returns_ok(self, client):
        """Test that health endpoint returns ok status."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert 'timestamp' in response.json


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_not_found(self, client):
        """Test that 404 returns proper error."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404
        assert 'error' in response.json


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
