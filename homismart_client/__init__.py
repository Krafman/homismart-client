# homismart_client/homismart_client/__init__.py
"""
Homismart Client Library
~~~~~~~~~~~~~~~~~~~~~~

A Python library to interact with Homismart devices via their WebSocket API.

This __init__.py file makes the core components of the library, such as the
HomismartClient, custom exceptions, and key enumerations, available directly
when the 'homismart_client' package is imported.

Usage:
    >>> import asyncio
    >>> from homismart_client import HomismartClient, AuthenticationError
    >>>
    >>> async def main():
    ...     client = HomismartClient(username="your_email", password="your_password")
    ...     try:
    ...         await client.connect()
    ...         # Wait for devices to be populated or for specific events
    ...         await asyncio.sleep(10) # Example: allow time for connection and device discovery
    ...         if client.session:
    ...             print(f"Connected! Found {len(client.session.get_all_devices())} devices.")
    ...             for device_id, device in client.session.get_all_devices().items():
    ...                 print(f"  - {device}")
    ...     except AuthenticationError:
    ...         print("Authentication failed. Please check your credentials.")
    ...     except Exception as e:
    ...         print(f"An error occurred: {e}")
    ...     finally:
    ...         if client.is_connected: # Check if client has is_connected attribute
    ...             await client.disconnect()
    >>>
    >>> # To run the example (ensure HOMISMART_USERNAME and HOMISMART_PASSWORD env vars are set):
    >>> # if __name__ == "__main__":
    >>> # asyncio.run(main())

For more detailed information, please refer to the documentation (README.md).
"""

import logging

# Core client class, making it available as: from homismart_client import HomismartClient
from .client import HomismartClient

# Key exceptions, available as: from homismart_client import AuthenticationError, etc.
from .exceptions import (
    HomismartError,
    AuthenticationError,
    ConnectionError,
    CommandError,
    ParameterError,
    DeviceNotFoundError
)

# Core enums (optional, but can be convenient for users to have at the top level)
# Available as: from homismart_client import RequestPrefix, etc.
from .enums import (
    RequestPrefix,
    ReceivePrefix,
    DeviceType,
    ErrorCode
)

# Device classes:
# You can choose to expose these directly from `homismart_client` or require users
# to import them from `homismart_client.devices`.
# If you want them directly available (e.g., `from homismart_client import SwitchableDevice`),
# uncomment the following and ensure homismart_client/devices/__init__.py correctly exports them.
#
# from .devices import (
# HomismartDevice,
# HomismartHub,
# SwitchableDevice,
# CurtainDevice,
# LockDevice
# )

# Version of the homismart_client package.
# This is often read by setup.py.
__version__ = "0.1.1" # Initialize with your starting version

# Configure a NullHandler for the library's root logger.
# This is crucial for libraries to prevent "No handler found" warnings
# if the consuming application has not configured logging. Application developers
# can then set up their own logging handlers as needed.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Define __all__ to specify what `from homismart_client import *` imports.
# While explicit imports are generally preferred by users, defining __all__ is good practice.
__all__ = [
    # Client
    "HomismartClient",

    # Exceptions
    "HomismartError",
    "AuthenticationError",
    "ConnectionError",
    "CommandError",
    "ParameterError",
    "DeviceNotFoundError",

    # Enums
    "RequestPrefix",
    "ReceivePrefix",
    "DeviceType",
    "ErrorCode",

    # If you uncommented the device class imports above, add their names here too:
    # "HomismartDevice",
    # "HomismartHub",
    # "SwitchableDevice",
    # "CurtainDevice",
    # "LockDevice",
]

# Optional: A simple log message to indicate the library's top-level __init__ has run.
# This is usually not done in library __init__.py files unless for specific debugging.
# logger = logging.getLogger(__name__)
# logger.debug(f"Homismart Client Library top-level __init__ executed, version {__version__}")