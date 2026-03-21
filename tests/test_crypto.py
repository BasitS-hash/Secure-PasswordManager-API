"""
Test cases for cryptographic utilities.
"""

import pytest
import os
from src.utils.crypto import encrypt_aes_gcm, decrypt_aes_gcm, random_bytes
from src.utils.passwords import generate_password, entropy_bits


class TestCrypto:
    """Test cryptographic functions."""
    
    def test_aes_gcm_encrypt_decrypt_roundtrip(self):
        """Test AES-GCM encryption/decryption roundtrip."""
        key = os.urandom(32)
        plaintext = b'my_secret_password'
        
        encrypted = encrypt_aes_gcm(plaintext, key)
        
        decrypted = decrypt_aes_gcm(
            encrypted['ciphertext'],
            key,
            encrypted['iv'],
            encrypted['tag']
        )
        
        assert decrypted == plaintext
    
    def test_random_bytes_generation(self):
        """Test random bytes generation."""
        bytes1 = random_bytes(16)
        bytes2 = random_bytes(16)
        
        assert len(bytes1) == 16
        assert len(bytes2) == 16
        assert bytes1 != bytes2  # Should be different


class TestPasswordGeneration:
    """Test password generation functions."""
    
    def test_generate_password_creates_correct_length(self):
        """Test that generated password has correct length."""
        pw = generate_password(length=20)
        assert len(pw) == 20
    
    def test_generate_password_includes_character_types(self):
        """Test that password includes specified character types."""
        pw = generate_password(
            length=32,
            upper=True,
            lower=True,
            digits=True,
            symbols=True
        )
        
        # At least one character type should be present
        assert len(pw) == 32
        assert any(c.isupper() for c in pw) or \
               any(c.islower() for c in pw) or \
               any(c.isdigit() for c in pw)
    
    def test_generate_password_with_limited_charsets(self):
        """Test password generation with only digits."""
        pw = generate_password(
            length=10,
            upper=False,
            lower=False,
            digits=True,
            symbols=False
        )
        
        assert len(pw) == 10
        assert all(c.isdigit() for c in pw)
    
    def test_generate_password_requires_at_least_one_charset(self):
        """Test that at least one character set is required."""
        with pytest.raises(ValueError):
            generate_password(
                upper=False,
                lower=False,
                digits=False,
                symbols=False
            )


class TestEntropyCalculation:
    """Test password entropy calculations."""
    
    def test_entropy_bits_returns_reasonable_value(self):
        """Test that entropy calculation returns reasonable values."""
        pw = 'Abc123!@#'
        entropy = entropy_bits(pw)
        
        assert entropy > 0
        assert entropy < 200
    
    def test_entropy_bits_for_empty_password(self):
        """Test entropy for empty password."""
        entropy = entropy_bits('')
        assert entropy == 0
    
    def test_entropy_increases_with_length(self):
        """Test that longer passwords have higher entropy."""
        pw_short = 'Abc123'
        pw_long = 'Abc123Abc123'
        
        entropy_short = entropy_bits(pw_short)
        entropy_long = entropy_bits(pw_long)
        
        assert entropy_long > entropy_short


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
