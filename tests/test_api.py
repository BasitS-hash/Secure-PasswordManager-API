"""
API integration tests for the Secure Password Manager.
"""

import os
import base64
import pytest
from fastapi.testclient import TestClient
from app import app

# A valid password that passes all validation rules
VALID_PASSWORD = 'TestPass1@3$5678XX90'
VALID_USERNAME = 'testuser_ci'

# Fake encrypted entry data (base64-encoded bytes, like a real client would send)
FAKE_CIPHERTEXT = base64.b64encode(b'x' * 32).decode()
FAKE_IV = base64.b64encode(b'y' * 12).decode()
FAKE_TAG = base64.b64encode(b'z' * 16).decode()

# Skip any test that needs a real database when DATABASE_URL is not set
requires_db = pytest.mark.skipif(
    not os.getenv('DATABASE_URL'),
    reason='DATABASE_URL not set — skipping DB tests'
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def logged_in(client):
    """
    Register and log in a test user.
    Returns (client, access_token, refresh_token) so tests can make
    authenticated requests.
    """
    client.post('/auth/register', json={
        'username': VALID_USERNAME,
        'password': VALID_PASSWORD
    })

    response = client.post('/auth/login', json={
        'username': VALID_USERNAME,
        'password': VALID_PASSWORD
    })

    data = response.json()
    return client, data['accessToken'], data['refreshToken']


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_register_requires_username_and_password(self, client):
        response = client.post('/auth/register', json={})
        assert response.status_code == 400
        assert 'username and password required' in response.json()['error']

    def test_login_requires_username_and_password(self, client):
        response = client.post('/auth/login', json={})
        assert response.status_code == 400
        assert 'username and password required' in response.json()['error']

    def test_register_rejects_short_password(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'Short1@'
        })
        assert response.status_code == 400
        assert 'at least 20 characters' in response.json()['error']

    def test_register_rejects_password_without_uppercase(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'alllowercase1@3$567890'
        })
        assert response.status_code == 400
        assert 'uppercase' in response.json()['error']

    def test_register_rejects_password_without_special_char(self, client):
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'password': 'NoSpecialChar12345678'
        })
        assert response.status_code == 400
        assert 'special character' in response.json()['error']

    def test_register_rejects_invalid_username(self, client):
        response = client.post('/auth/register', json={
            'username': 'ab',
            'password': VALID_PASSWORD
        })
        assert response.status_code == 400
        assert 'Username' in response.json()['error']

    @requires_db
    def test_register_success(self, client):
        response = client.post('/auth/register', json={
            'username': 'newuser_reg',
            'password': VALID_PASSWORD
        })
        assert response.status_code == 201
        assert 'id' in response.json()
        assert response.json()['username'] == 'newuser_reg'

    @requires_db
    def test_login_success(self, client):
        client.post('/auth/register', json={
            'username': 'newuser_login',
            'password': VALID_PASSWORD
        })
        response = client.post('/auth/login', json={
            'username': 'newuser_login',
            'password': VALID_PASSWORD
        })
        assert response.status_code == 200
        assert 'accessToken' in response.json()
        assert 'refreshToken' in response.json()
        assert 'encryption_salt' in response.json()

    @requires_db
    def test_login_wrong_password(self, client):
        client.post('/auth/register', json={
            'username': 'newuser_wrong',
            'password': VALID_PASSWORD
        })
        response = client.post('/auth/login', json={
            'username': 'newuser_wrong',
            'password': 'WrongPass1@3$567890XX'
        })
        assert response.status_code == 401

    @requires_db
    def test_token_refresh(self, logged_in):
        client, _, refresh_token = logged_in
        response = client.post('/auth/token', json={'refreshToken': refresh_token})
        assert response.status_code == 200
        assert 'accessToken' in response.json()
        assert 'refreshToken' in response.json()

    @requires_db
    def test_logout(self, logged_in):
        client, _, refresh_token = logged_in
        response = client.post('/auth/logout', json={'refreshToken': refresh_token})
        assert response.status_code == 200
        assert response.json()['ok'] is True

    @requires_db
    def test_used_refresh_token_is_invalid_after_rotation(self, logged_in):
        client, _, refresh_token = logged_in
        client.post('/auth/token', json={'refreshToken': refresh_token})
        response = client.post('/auth/token', json={'refreshToken': refresh_token})
        assert response.status_code == 403


class TestEntriesEndpoints:
    """Test password entry endpoints."""

    def test_get_entries_without_auth_returns_401(self, client):
        response = client.get('/entries/')
        assert response.status_code == 401

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

    @requires_db
    def test_create_entry(self, logged_in):
        client, token, _ = logged_in
        headers = {'Authorization': f'Bearer {token}'}
        response = client.post('/entries/', headers=headers, json={
            'name': 'GitHub',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        assert response.status_code == 201
        assert response.json()['ok'] is True
        assert 'id' in response.json()

    @requires_db
    def test_list_entries(self, logged_in):
        client, token, _ = logged_in
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/entries/', headers=headers, json={
            'name': 'GitHub',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        response = client.get('/entries/', headers=headers)
        assert response.status_code == 200
        assert len(response.json()['entries']) >= 1

    @requires_db
    def test_get_entry_by_id(self, logged_in):
        client, token, _ = logged_in
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/entries/', headers=headers, json={
            'name': 'GitHub',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        entries = client.get('/entries/', headers=headers).json()['entries']
        entry_id = entries[0]['id']
        response = client.get(f'/entries/{entry_id}', headers=headers)
        assert response.status_code == 200
        assert response.json()['name'] == 'GitHub'

    @requires_db
    def test_update_entry(self, logged_in):
        client, token, _ = logged_in
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/entries/', headers=headers, json={
            'name': 'GitHub',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        entry_id = client.get('/entries/', headers=headers).json()['entries'][0]['id']
        response = client.put(f'/entries/{entry_id}', headers=headers, json={
            'name': 'GitHub Updated',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        assert response.status_code == 200
        assert response.json()['ok'] is True

    @requires_db
    def test_delete_entry(self, logged_in):
        client, token, _ = logged_in
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/entries/', headers=headers, json={
            'name': 'GitHub',
            'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV,
            'tag': FAKE_TAG
        })
        entry_id = client.get('/entries/', headers=headers).json()['entries'][0]['id']
        response = client.delete(f'/entries/{entry_id}', headers=headers)
        assert response.status_code == 200
        assert response.json()['ok'] is True

    @requires_db
    def test_cannot_access_another_users_entry(self, client):
        client.post('/auth/register', json={
            'username': 'user_one_x', 'password': VALID_PASSWORD
        })
        client.post('/auth/register', json={
            'username': 'user_two_x', 'password': VALID_PASSWORD
        })

        token1 = client.post('/auth/login', json={
            'username': 'user_one_x', 'password': VALID_PASSWORD
        }).json()['accessToken']

        client.post('/entries/', headers={'Authorization': f'Bearer {token1}'}, json={
            'name': 'Secret', 'ciphertext': FAKE_CIPHERTEXT,
            'iv': FAKE_IV, 'tag': FAKE_TAG
        })

        entry_id = client.get(
            '/entries/', headers={'Authorization': f'Bearer {token1}'}
        ).json()['entries'][0]['id']

        token2 = client.post('/auth/login', json={
            'username': 'user_two_x', 'password': VALID_PASSWORD
        }).json()['accessToken']

        response = client.get(
            f'/entries/{entry_id}',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert response.status_code == 404


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
        assert 'timestamp' in response.json()


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self, client):
        response = client.get('/nonexistent-api-path')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
