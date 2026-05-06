"""
Cryptographic utilities for AES-256-GCM encryption.
These are provided for testing and client demos.
For zero-knowledge, perform encryption/decryption client-side using derived key.
"""

import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def random_bytes(size=16):
    """Generate random bytes of specified size."""
    return secrets.token_bytes(size)


def encrypt_aes_gcm(plaintext, key):
    """
    Encrypt plaintext using AES-256-GCM.

    Args:
        plaintext: bytes or string to encrypt
        key: 32-byte encryption key

    Returns:
        dict with 'ciphertext', 'iv', and 'tag' as hex strings
    """
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')

    iv = secrets.token_bytes(12)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(iv, plaintext, None)

    # AESGCM.encrypt returns ciphertext + tag, we need to split them
    tag = ciphertext[-16:]
    actual_ciphertext = ciphertext[:-16]

    return {
        'ciphertext': actual_ciphertext.hex(),
        'iv': iv.hex(),
        'tag': tag.hex()
    }


def decrypt_aes_gcm(ciphertext_hex, key, iv_hex, tag_hex):
    """
    Decrypt ciphertext using AES-256-GCM.

    Args:
        ciphertext_hex: hex string of ciphertext
        key: 32-byte encryption key
        iv_hex: hex string of IV
        tag_hex: hex string of authentication tag

    Returns:
        decrypted plaintext as bytes
    """
    ciphertext = bytes.fromhex(ciphertext_hex)
    iv = bytes.fromhex(iv_hex)
    tag = bytes.fromhex(tag_hex)

    cipher = AESGCM(key)
    plaintext = cipher.decrypt(iv, ciphertext + tag, None)

    return plaintext
