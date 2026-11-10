"""
homismart_client/utils.py

Contains miscellaneous utility functions for the Homismart client.
"""
import hashlib

def md5_hash(text: str) -> str:
    """
    Computes the MD5 hash of the input string.

    The Homismart API requires the password to be MD5 hashed before sending
    it in the login request.

    Args:
        text: The string to hash.

    Returns:
        The hexadecimal MD5 hash string.
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()
