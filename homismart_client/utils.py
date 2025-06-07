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

if __name__ == '__main__':
    # Example usage (can be removed or kept for simple testing)
    password_plain = "mysecretpassword"
    password_hashed = md5_hash(password_plain)
    print(f"Plain password: {password_plain}")
    print(f"MD5 Hashed: {password_hashed}")

    # Example hash from observed JavaScript if available (for comparison)
    # If "test" hashes to "098f6bcd4621d373cade4e832627b4f6"
    test_str = "test"
    expected_hash = "098f6bcd4621d373cade4e832627b4f6"
    print(f"Hashing 'test': {md5_hash(test_str)}")
    print(f"Expected for 'test': {expected_hash}")
    assert md5_hash(test_str) == expected_hash