"""
Homismart Client Library
~~~~~~~~~~~~~~~~~~~~~~~~

An unofficial asyncio client for Homismart devices, using the same WebSocket
API as the official apps.

Usage::

    import asyncio
    from homismart_client import HomismartClient, AuthenticationError

    async def main():
        try:
            async with HomismartClient("you@example.com", "password") as client:
                await asyncio.sleep(3)  # let the device list arrive
                for device in client.session.get_all_devices():
                    print(device)
        except AuthenticationError:
            print("Wrong username or password.")

    asyncio.run(main())

See README.md for events, device control and reconnection behaviour.
"""

import logging

from .client import HomismartClient
from .devices import (
    CurtainDevice,
    HomismartDevice,
    HomismartHub,
    LockDevice,
    SwitchableDevice,
)
from .enums import DeviceType, ErrorCode, ReceivePrefix, RequestPrefix
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    DeviceNotFoundError,
    HomismartError,
    ParameterError,
)

# Read by setup.py; the release workflow overwrites it with the release tag.
__version__ = "0.3.0"

# Libraries should not configure logging; the application decides.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "HomismartClient",
    # Devices
    "HomismartDevice",
    "HomismartHub",
    "SwitchableDevice",
    "CurtainDevice",
    "LockDevice",
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
]
