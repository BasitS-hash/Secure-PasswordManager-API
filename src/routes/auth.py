"""
Authentication routes for register, login, token refresh, and logout.
"""

import os
import hashlib
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
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
async def register():
    """Register a new user."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    ip = request.remote_addr
    
    if not username or not password:
        await audit_log(action='register', ip=ip, success=False, message='missing credentials')
        return jsonify({'error': 'username and password required'}), 400
    
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
            await audit_log(user_id=user['id'], action='register', ip=ip, success=True)
            return jsonify({
                'id': user['id'],
                'username': user['username']
            }), 201
        else:
            raise Exception('Failed to create user')
            
    except Exception as err:
        logger.error(f'Registration error: {err}')
        await audit_log(action='register', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
async def login():
    """Authenticate user and return access and refresh tokens."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    ip = request.remote_addr
    
    if not username or not password:
        await audit_log(action='login', ip=ip, success=False, message='missing credentials')
        return jsonify({'error': 'username and password required'}), 400
    
    try:
        # Find user
        result = db.query(
            'SELECT id, password_hash, encryption_salt FROM users WHERE username=%s',
            (username,)
        )
        
        if not result:
            await audit_log(action='login', ip=ip, success=False, message='user not found')
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user = result[0]
        
        # Verify password
        try:
            ph.verify(user['password_hash'], password)
        except VerifyMismatchError:
            await audit_log(user_id=user['id'], action='login', ip=ip, success=False, message='invalid password')
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Create access token
        access_token_expires = parse_expiry(os.getenv('ACCESS_TOKEN_EXPIRES_IN', '15m'))
        access_token = jwt.encode(
            {
                'sub': user['id'],
                'username': username,
                'exp': datetime.utcnow() + access_token_expires
            },
            JWT_SECRET,
            algorithm='HS256'
        )
        
        # Create refresh token
        refresh_token = str(uuid.uuid4())
        token_hash = hash_token(refresh_token)
        
        refresh_token_expires = parse_expiry(os.getenv('REFRESH_TOKEN_EXPIRES_IN', '7d'))
        expires_at = datetime.utcnow() + refresh_token_expires
        
        db.execute(
            '''INSERT INTO refresh_tokens(user_id, token_hash, expires_at)
               VALUES(%s, %s, %s)''',
            (user['id'], token_hash, expires_at)
        )
        
        await audit_log(user_id=user['id'], action='login', ip=ip, success=True)
        
        return jsonify({
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'encryption_salt': user['encryption_salt']
        }), 200
        
    except Exception as err:
        logger.error(f'Login error: {err}')
        await audit_log(action='login', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/token', methods=['POST'])
async def refresh_token():
    """Exchange a refresh token for a new access token."""
    data = request.get_json() or {}
    refresh_token = data.get('refreshToken')
    ip = request.remote_addr
    
    if not refresh_token:
        await audit_log(action='refresh_token', ip=ip, success=False, message='missing refresh token')
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
        if datetime.fromisoformat(record['expires_at'].isoformat()) < datetime.utcnow():
            return jsonify({'error': 'Refresh token expired'}), 403
        
        # Get user info
        user_result = db.query(
            'SELECT username FROM users WHERE id=%s',
            (record['user_id'],)
        )
        
        if not user_result:
            return jsonify({'error': 'User not found'}), 404
        
        username = user_result[0]['username']
        
        # Create new access token
        access_token_expires = parse_expiry(os.getenv('ACCESS_TOKEN_EXPIRES_IN', '15m'))
        access_token = jwt.encode(
            {
                'sub': record['user_id'],
                'username': username,
                'exp': datetime.utcnow() + access_token_expires
            },
            JWT_SECRET,
            algorithm='HS256'
        )
        
        await audit_log(user_id=record['user_id'], action='refresh_token', ip=ip, success=True)
        
        return jsonify({'accessToken': access_token}), 200
        
    except Exception as err:
        logger.error(f'Token refresh error: {err}')
        await audit_log(action='refresh_token', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Token exchange failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
async def logout():
    """Invalidate a refresh token."""
    data = request.get_json() or {}
    refresh_token = data.get('refreshToken')
    ip = request.remote_addr
    
    if not refresh_token:
        await audit_log(action='logout', ip=ip, success=False, message='missing refresh token')
        return jsonify({'error': 'refreshToken required'}), 400
    
    try:
        token_hash = hash_token(refresh_token)
        db.execute(
            'DELETE FROM refresh_tokens WHERE token_hash=%s',
            (token_hash,)
        )
        
        await audit_log(action='logout', ip=ip, success=True)
        return jsonify({'ok': True}), 200
        
    except Exception as err:
        logger.error(f'Logout error: {err}')
        await audit_log(action='logout', ip=ip, success=False, message=str(err))
        return jsonify({'error': 'Logout failed'}), 500
