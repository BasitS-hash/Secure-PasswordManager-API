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
        """Test that registration requires username and password."""
        response = client.post('/auth/register', json={})
        
        assert response.status_code == 400
        assert 'error' in response.json
        assert 'username and password required' in response.json['error']
    
    def test_login_requires_username_and_password(self, client):
        """Test that login requires username and password."""
        response = client.post('/auth/login', json={})
        
        assert response.status_code == 400
        assert 'error' in response.json
        assert 'username and password required' in response.json['error']


class TestEntriesEndpoints:
    """Test password entry endpoints."""
    
    def test_get_entries_without_auth_returns_401(self, client):
        """Test that accessing entries without token returns 401."""
        response = client.get('/entries/')
        
        assert response.status_code == 401
        assert 'error' in response.json
    
    def test_create_entry_without_auth_returns_401(self, client):
        """Test that creating entry without token returns 401."""
        response = client.post(
            '/entries/',
            json={
                'name': 'test',
                'ciphertext': 'xyz',
                'iv': 'abc',
                'tag': 'def'
            }
        )
        
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
