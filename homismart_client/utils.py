"""
homismart_client/utils.py

Contains miscellaneous utility functions for the Homismart client.
"""
import hashlib
import json

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


# Fields that must never reach a log: credentials and personal details. The
# login request carries the password's MD5 hash, which the server accepts in
# place of the password, so it is as sensitive as the password itself.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "newpassword",
        "oldpassword",
        "username",
        "email",
        "realname",
        "name",  # device, hub and room names are often people's names
        "macaddr",
        "mac",
        "sharedby",
        "token",
        "accesstoken",
        "refreshtoken",
        "devicetoken",
    }
)
REDACTED = "**REDACTED**"


def redact(value):
    """Return a copy of *value* with sensitive fields replaced, for logging.

    Works on nested dicts and lists; key matching ignores case.
    """
    if isinstance(value, dict):
        return {
            key: REDACTED if isinstance(key, str) and key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def redact_message(raw: str) -> str:
    """Return a raw protocol message (4-char prefix + JSON) safe for logging."""
    prefix, body = raw[:4], raw[4:]
    if not body:
        return raw
    try:
        return prefix + json.dumps(redact(json.loads(body)))
    except (ValueError, RecursionError):
        return f"{prefix}<{len(body)} characters, not JSON>"
