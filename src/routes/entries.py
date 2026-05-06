"""
Password entry routes for storing and retrieving encrypted passwords.
"""

import os
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import base64

from src import db
from src.logger import logger
from src.middleware.auth import authenticate_token
from src.middleware.audit import audit_log

load_dotenv()

entries_bp = Blueprint('entries', __name__, url_prefix='/entries')


@entries_bp.route('/', methods=['POST'])
@authenticate_token
def create_entry():
    """
    Create a password entry (expects ciphertext, iv, tag from client-side encryption).
    """
    data = request.get_json() or {}
    name = data.get('name')
    ciphertext = data.get('ciphertext')
    iv = data.get('iv')
    tag = data.get('tag')
    meta = data.get('meta')

    user_id = request.user.get('sub') if request.user else None
    ip = request.remote_addr

    if not all([name, ciphertext, iv, tag]):
        audit_log(user_id=user_id, action='create_entry', ip=ip, success=False,
                  message='missing required fields')
        return jsonify({'error': 'name, ciphertext, iv and tag are required'}), 400

    try:
        # Convert base64 strings to bytes
        ciphertext_bytes = base64.b64decode(ciphertext)
        iv_bytes = base64.b64decode(iv)
        tag_bytes = base64.b64decode(tag)

        db.execute(
            '''INSERT INTO password_entries(user_id, name, ciphertext, iv, tag, meta)
               VALUES(%s, %s, %s, %s, %s, %s)''',
            (user_id, name, ciphertext_bytes, iv_bytes, tag_bytes, meta or None)
        )

        audit_log(user_id=user_id, action='create_entry', ip=ip, success=True)
        return jsonify({'ok': True}), 201

    except Exception as err:
        logger.error(f'Create entry error: {err}')
        audit_log(user_id=user_id, action='create_entry', ip=ip, success=False,
                  message=str(err))
        return jsonify({'error': 'Failed to create entry'}), 500


@entries_bp.route('/', methods=['GET'])
@authenticate_token
def list_entries():
    """
    List all password entries for the authenticated user.
    Returns ciphertext blobs only (encrypted on client-side).
    """
    user_id = request.user.get('sub') if request.user else None
    ip = request.remote_addr

    try:
        result = db.query(
            '''SELECT id, name, encode(ciphertext, 'base64') AS ciphertext,
                      encode(iv, 'base64') AS iv, encode(tag, 'base64') AS tag,
                      meta, created_at, updated_at
               FROM password_entries
               WHERE user_id=%s
               ORDER BY created_at DESC''',
            (user_id,)
        )

        audit_log(user_id=user_id, action='list_entries', ip=ip, success=True)

        return jsonify({'entries': result or []}), 200

    except Exception as err:
        logger.error(f'List entries error: {err}')
        audit_log(user_id=user_id, action='list_entries', ip=ip, success=False,
                  message=str(err))
        return jsonify({'error': 'Failed to list entries'}), 500


@entries_bp.route('/<string:entry_id>', methods=['GET'])
@authenticate_token
def get_entry(entry_id):
    """Fetch a single password entry by ID."""
    user_id = request.user.get('sub') if request.user else None
    ip = request.remote_addr

    try:
        result = db.query(
            '''SELECT id, name, encode(ciphertext, 'base64') AS ciphertext,
                      encode(iv, 'base64') AS iv, encode(tag, 'base64') AS tag,
                      meta, created_at, updated_at
               FROM password_entries
               WHERE id=%s AND user_id=%s''',
            (entry_id, user_id)
        )

        if not result:
            audit_log(user_id=user_id, action='get_entry', ip=ip, success=False,
                      message='not found')
            return jsonify({'error': 'Entry not found'}), 404

        audit_log(user_id=user_id, action='get_entry', ip=ip, success=True)
        return jsonify(result[0]), 200

    except Exception as err:
        logger.error(f'Get entry error: {err}')
        audit_log(user_id=user_id, action='get_entry', ip=ip, success=False,
                  message=str(err))
        return jsonify({'error': 'Failed to get entry'}), 500


@entries_bp.route('/<string:entry_id>', methods=['PUT'])
@authenticate_token
def update_entry(entry_id):
    """Update a password entry (re-encrypt and replace ciphertext)."""
    data = request.get_json() or {}
    name = data.get('name')
    ciphertext = data.get('ciphertext')
    iv = data.get('iv')
    tag = data.get('tag')
    meta = data.get('meta')

    user_id = request.user.get('sub') if request.user else None
    ip = request.remote_addr

    if not all([name, ciphertext, iv, tag]):
        audit_log(user_id=user_id, action='update_entry', ip=ip, success=False,
                  message='missing required fields')
        return jsonify({'error': 'name, ciphertext, iv and tag are required'}), 400

    try:
        ciphertext_bytes = base64.b64decode(ciphertext)
        iv_bytes = base64.b64decode(iv)
        tag_bytes = base64.b64decode(tag)

        existing = db.query(
            'SELECT id FROM password_entries WHERE id=%s AND user_id=%s',
            (entry_id, user_id)
        )
        if not existing:
            audit_log(user_id=user_id, action='update_entry', ip=ip, success=False,
                      message='not found')
            return jsonify({'error': 'Entry not found'}), 404

        db.execute(
            '''UPDATE password_entries
               SET name=%s, ciphertext=%s, iv=%s, tag=%s, meta=%s, updated_at=now()
               WHERE id=%s AND user_id=%s''',
            (name, ciphertext_bytes, iv_bytes, tag_bytes, meta or None, entry_id, user_id)
        )

        audit_log(user_id=user_id, action='update_entry', ip=ip, success=True)
        return jsonify({'ok': True}), 200

    except Exception as err:
        logger.error(f'Update entry error: {err}')
        audit_log(user_id=user_id, action='update_entry', ip=ip, success=False,
                  message=str(err))
        return jsonify({'error': 'Failed to update entry'}), 500


@entries_bp.route('/<string:entry_id>', methods=['DELETE'])
@authenticate_token
def delete_entry(entry_id):
    """Delete a password entry."""
    user_id = request.user.get('sub') if request.user else None
    ip = request.remote_addr

    try:
        existing = db.query(
            'SELECT id FROM password_entries WHERE id=%s AND user_id=%s',
            (entry_id, user_id)
        )
        if not existing:
            audit_log(user_id=user_id, action='delete_entry', ip=ip, success=False,
                      message='not found')
            return jsonify({'error': 'Entry not found'}), 404

        db.execute(
            'DELETE FROM password_entries WHERE id=%s AND user_id=%s',
            (entry_id, user_id)
        )

        audit_log(user_id=user_id, action='delete_entry', ip=ip, success=True)
        return jsonify({'ok': True}), 200

    except Exception as err:
        logger.error(f'Delete entry error: {err}')
        audit_log(user_id=user_id, action='delete_entry', ip=ip, success=False,
                  message=str(err))
        return jsonify({'error': 'Failed to delete entry'}), 500
