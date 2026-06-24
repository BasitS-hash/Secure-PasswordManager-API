"""Negative / adversarial tests for the AES-256-GCM crypto layer.

These prove the authenticated-encryption guarantees: any tampering with the
ciphertext, IV, or tag, or use of the wrong key, is rejected rather than
silently returning corrupted plaintext.
"""

import os

import pytest
from cryptography.exceptions import InvalidTag

from src.utils.crypto import decrypt_aes_gcm, encrypt_aes_gcm, random_bytes


def _flip_first_hex_nibble(hex_str: str) -> str:
    """Return the hex string with its first nibble altered (guaranteed change)."""
    first = "0" if hex_str[0] != "0" else "1"
    return first + hex_str[1:]


class TestAesGcmAuthentication:
    def test_uses_256_bit_key(self):
        """A 256-bit key is required; AES-256 is in use, not AES-128."""
        key = os.urandom(16)  # 128-bit key
        with pytest.raises(ValueError):
            encrypt_aes_gcm(b"data", key)

    def test_nonce_is_unique_per_encryption(self):
        """Each encryption must use a fresh random 96-bit nonce."""
        key = os.urandom(32)
        a = encrypt_aes_gcm(b"same plaintext", key)
        b = encrypt_aes_gcm(b"same plaintext", key)
        assert a["iv"] != b["iv"]
        # Reusing a nonce in GCM is catastrophic; distinct IVs also yield
        # distinct ciphertexts for identical plaintext.
        assert a["ciphertext"] != b["ciphertext"]
        assert len(bytes.fromhex(a["iv"])) == 12

    def test_tampered_ciphertext_is_rejected(self):
        key = os.urandom(32)
        enc = encrypt_aes_gcm(b"top secret value", key)
        tampered = _flip_first_hex_nibble(enc["ciphertext"])
        with pytest.raises(InvalidTag):
            decrypt_aes_gcm(tampered, key, enc["iv"], enc["tag"])

    def test_tampered_tag_is_rejected(self):
        key = os.urandom(32)
        enc = encrypt_aes_gcm(b"top secret value", key)
        tampered_tag = _flip_first_hex_nibble(enc["tag"])
        with pytest.raises(InvalidTag):
            decrypt_aes_gcm(enc["ciphertext"], key, enc["iv"], tampered_tag)

    def test_tampered_iv_is_rejected(self):
        key = os.urandom(32)
        enc = encrypt_aes_gcm(b"top secret value", key)
        tampered_iv = _flip_first_hex_nibble(enc["iv"])
        with pytest.raises(InvalidTag):
            decrypt_aes_gcm(enc["ciphertext"], key, tampered_iv, enc["tag"])

    def test_wrong_key_is_rejected(self):
        enc = encrypt_aes_gcm(b"top secret value", os.urandom(32))
        with pytest.raises(InvalidTag):
            decrypt_aes_gcm(enc["ciphertext"], os.urandom(32), enc["iv"], enc["tag"])

    def test_roundtrip_with_string_input(self):
        key = os.urandom(32)
        enc = encrypt_aes_gcm("unicode secret: ☂ é", key)
        out = decrypt_aes_gcm(enc["ciphertext"], key, enc["iv"], enc["tag"])
        assert out.decode("utf-8") == "unicode secret: ☂ é"

    def test_random_bytes_are_unpredictable(self):
        samples = {random_bytes(16) for _ in range(50)}
        assert len(samples) == 50  # no collisions
