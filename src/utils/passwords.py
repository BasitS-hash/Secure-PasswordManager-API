"""
Password generation and entropy calculation utilities.
"""

import secrets
import re
import math


def generate_password(length=16, upper=True, lower=True, digits=True, symbols=True):
    """
    Generate a random password with specified character sets.

    Args:
        length: password length (default 16)
        upper: include uppercase letters
        lower: include lowercase letters
        digits: include digits
        symbols: include symbols

    Returns:
        Generated password string
    """
    sets = []
    if upper:
        sets.append('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    if lower:
        sets.append('abcdefghijklmnopqrstuvwxyz')
    if digits:
        sets.append('0123456789')
    if symbols:
        sets.append('!@#$%^&*()-_=+[]{}|;:,.<>?')

    if not sets:
        raise ValueError('At least one character set required')

    if length < len(sets):
        raise ValueError(f'Length must be at least {len(sets)} to satisfy all character requirements')

    all_chars = ''.join(sets)

    # Guarantee one character from each required set, then fill the rest randomly
    guaranteed = [secrets.choice(s) for s in sets]
    filler = [secrets.choice(all_chars) for _ in range(length - len(guaranteed))]

    password_chars = guaranteed + filler
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)


def entropy_bits(password):
    """
    Estimate entropy of password by calculating log2(possibleSymbols^length).

    Args:
        password: password string to analyze

    Returns:
        Estimated entropy in bits
    """
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digits = bool(re.search(r'[0-9]', password))
    has_symbols = bool(re.search(r'[^A-Za-z0-9]', password))

    pool = 0
    if has_upper:
        pool += 26
    if has_lower:
        pool += 26
    if has_digits:
        pool += 10
    if has_symbols:
        pool += 32  # approximate symbol count

    if pool == 0:
        return 0

    return math.log2(pow(pool, len(password)))
