"""
Authentication routes for register, login, token refresh, and logout.
"""

import os
import re
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
from dotenv import load_dotenv

from src import db
from src.logger import logger
from src.middleware.audit import audit_log

load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
ph = PasswordHasher()
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-me')


def hash_token(token):
    """Hash a refresh token using SHA256."""
    return hashlib.sha256(token.encode()).hexdigest()


def validate_username(username):
    """3–30 chars, letters/digits/underscore only."""
    if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
        return False, 'Username must be 3–30 characters (letters, digits, underscore only)'
    return True, ''


def validate_password(password):
    """Min 20 chars with uppercase, lowercase, digit, and special character (@, $, etc.)."""
    if len(password) < 20:
        return False, 'Password must be at least 20 characters long'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one digit (e.g. 1, 3, 5)'
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]', password):
        return False, 'Password must contain at least one special character (e.g. @, $)'
    return True, ''


def parse_expiry(expiry_str):
    """
    Parse expiry string like '7d', '15m', etc. and return timedelta.

    Args:
        expiry_str: String like '7d', '15m', '1h'

    Returns:
        timedelta object
    """
    if not expiry_str:
        return timedelta(hours=1)

    import re
    match = re.match(r'^(\d+)([smhd])$', expiry_str)
    if not match:
        return timedelta(hours=1)

    value, unit = int(match.group(1)), match.group(2)

    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    else:
        return timedelta(hours=1)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    ip = request.remote_addr

    if not username or not password:
        audit_log(action='register', ip=ip, success=False, message='missing credentials')
        return jsonify({'error': 'username and password required'}), 400

    valid, msg = validate_username(username)
    if not valid:
        return jsonify({'error': msg}), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'error': msg}), 400

    try:
        # Hash password with Argon2
        password_hash = ph.hash(password)

        # Generate encryption salt for client-side key derivation
        encryption_salt = os.urandom(16).hex()

        # Insert user into database
        result = db.query(
            '''INSERT INTO users(username, password_hash, encryption_salt)
               VALUES(%s, %s, %s)
               RETURNING id, username, encryption_salt''',
            (username, password_hash, encryption_salt)
        )

        if result:
            user = result[0]
            audit_log(user_id=user['id'], action='register', ip=ip, success=True)
            return jsonify({
                'id': user['id'],
                'username': user['username']
            }), 201
        else:
            raise Exception('Failed to create user')

    except Exception as err:
        logger.error(f'Registration error: {err}')
        audit_log(action='register', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return access and refresh tokens."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    ip = request.remote_addr

    if not username or not password:
        audit_log(action='login', ip=ip, success=False, message='missing credentials')
        return jsonify({'error': 'username and password required'}), 400

    try:
        # Find user
        result = db.query(
            'SELECT id, password_hash, encryption_salt FROM users WHERE username=%s',
            (username,)
        )

        if not result:
            audit_log(action='login', ip=ip, success=False, message='user not found')
            return jsonify({'error': 'Invalid credentials'}), 401

        user = result[0]

        # Verify password
        try:
            ph.verify(user['password_hash'], password)
        except VerifyMismatchError:
            audit_log(user_id=user['id'], action='login', ip=ip, success=False, message='invalid password')
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create access token
        now = datetime.now(timezone.utc)
        access_token_expires = parse_expiry(os.getenv('ACCESS_TOKEN_EXPIRES_IN', '15m'))
        access_token = jwt.encode(
            {
                'sub': user['id'],
                'username': username,
                'exp': now + access_token_expires
            },
            JWT_SECRET,
            algorithm='HS256'
        )

        # Create refresh token
        refresh_token = str(uuid.uuid4())
        token_hash = hash_token(refresh_token)

        refresh_token_expires = parse_expiry(os.getenv('REFRESH_TOKEN_EXPIRES_IN', '7d'))
        expires_at = now + refresh_token_expires

        db.execute(
            '''INSERT INTO refresh_tokens(user_id, token_hash, expires_at)
               VALUES(%s, %s, %s)''',
            (user['id'], token_hash, expires_at)
        )

        audit_log(user_id=user['id'], action='login', ip=ip, success=True)

        return jsonify({
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'encryption_salt': user['encryption_salt']
        }), 200

    except Exception as err:
        logger.error(f'Login error: {err}')
        audit_log(action='login', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/token', methods=['POST'])
def refresh_token():
    """Exchange a refresh token for a new access token."""
    data = request.get_json() or {}
    refresh_token = data.get('refreshToken')
    ip = request.remote_addr

    if not refresh_token:
        audit_log(action='refresh_token', ip=ip, success=False, message='missing refresh token')
        return jsonify({'error': 'refreshToken required'}), 400

    try:
        token_hash = hash_token(refresh_token)

        # Look up refresh token
        result = db.query(
            'SELECT user_id, expires_at FROM refresh_tokens WHERE token_hash=%s',
            (token_hash,)
        )

        if not result:
            return jsonify({'error': 'Invalid refresh token'}), 403

        record = result[0]

        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = record['expires_at']
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            return jsonify({'error': 'Refresh token expired'}), 403

        # Get user info
        user_result = db.query(
            'SELECT username FROM users WHERE id=%s',
            (record['user_id'],)
        )

        if not user_result:
            return jsonify({'error': 'User not found'}), 404

        username = user_result[0]['username']

        # Rotate: delete old token, issue new one
        db.execute('DELETE FROM refresh_tokens WHERE token_hash=%s', (token_hash,))

        new_refresh_token = str(uuid.uuid4())
        new_token_hash = hash_token(new_refresh_token)
        new_expires_at = now + parse_expiry(os.getenv('REFRESH_TOKEN_EXPIRES_IN', '7d'))
        db.execute(
            'INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES(%s, %s, %s)',
            (record['user_id'], new_token_hash, new_expires_at)
        )

        # Issue new access token
        access_token_expires = parse_expiry(os.getenv('ACCESS_TOKEN_EXPIRES_IN', '15m'))
        access_token = jwt.encode(
            {
                'sub': record['user_id'],
                'username': username,
                'exp': now + access_token_expires
            },
            JWT_SECRET,
            algorithm='HS256'
        )

        audit_log(user_id=record['user_id'], action='refresh_token', ip=ip, success=True)

        return jsonify({'accessToken': access_token, 'refreshToken': new_refresh_token}), 200

    except Exception as err:
        logger.error(f'Token refresh error: {err}')
        audit_log(action='refresh_token', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Token exchange failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Invalidate a refresh token."""
    data = request.get_json() or {}
    refresh_token = data.get('refreshToken')
    ip = request.remote_addr

    if not refresh_token:
        audit_log(action='logout', ip=ip, success=False, message='missing refresh token')
        return jsonify({'error': 'refreshToken required'}), 400

    try:
        token_hash = hash_token(refresh_token)
        db.execute(
            'DELETE FROM refresh_tokens WHERE token_hash=%s',
            (token_hash,)
        )

        audit_log(action='logout', ip=ip, success=True)
        return jsonify({'ok': True}), 200

    except Exception as err:
        logger.error(f'Logout error: {err}')
        audit_log(action='logout', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Logout failed'}), 500
