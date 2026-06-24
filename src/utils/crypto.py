"""
Cryptographic utilities for AES-256-GCM encryption.
These are provided for testing and client demos.
For zero-knowledge, perform encryption/decryption client-side using derived key.
"""

import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# AES-256 requires a 32-byte (256-bit) key and we use a 96-bit GCM nonce
# (the recommended size for AES-GCM).
AES_256_KEY_BYTES = 32
GCM_NONCE_BYTES = 12


def random_bytes(size=16):
    """Generate cryptographically secure random bytes of the given size."""
    return secrets.token_bytes(size)


def _require_256_bit_key(key: bytes) -> None:
    if len(key) != AES_256_KEY_BYTES:
        raise ValueError(
            f"AES-256 requires a {AES_256_KEY_BYTES}-byte key; got {len(key)} bytes"
        )


def encrypt_aes_gcm(plaintext, key):
    """
    Encrypt plaintext using AES-256-GCM.

    Args:
        plaintext: bytes or string to encrypt
        key: 32-byte (256-bit) encryption key

    Returns:
        dict with 'ciphertext', 'iv', and 'tag' as hex strings
    """
    _require_256_bit_key(key)

    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    iv = secrets.token_bytes(GCM_NONCE_BYTES)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(iv, plaintext, None)

    # AESGCM.encrypt returns ciphertext + tag, we need to split them
    tag = ciphertext[-16:]
    actual_ciphertext = ciphertext[:-16]

    return {"ciphertext": actual_ciphertext.hex(), "iv": iv.hex(), "tag": tag.hex()}


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
    _require_256_bit_key(key)

    ciphertext = bytes.fromhex(ciphertext_hex)
    iv = bytes.fromhex(iv_hex)
    tag = bytes.fromhex(tag_hex)

    cipher = AESGCM(key)
    plaintext = cipher.decrypt(iv, ciphertext + tag, None)

    return plaintext
