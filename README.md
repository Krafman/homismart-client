# Homismart Client (Unofficial Python Library)

![PyPI - Version](https://img.shields.io/pypi/v/homismart-client)
![Python Versions](https://img.shields.io/pypi/pyversions/homismart-client)
![License](https://img.shields.io/pypi/l/homismart-client)
![GitHub stars](https://img.shields.io/github/stars/krafman/homismart-client?style=social)
![GitHub last commit](https://img.shields.io/github/last-commit/krafman/homismart-client)

> ⚠️ **Disclaimer**: This is an unofficial, community-driven library. It is not affiliated with, authorized, or endorsed by Homismart or its parent company. Use at your own risk — changes to Homismart's API may break functionality without notice.

A Python library for interacting with Homismart smart home devices via their WebSocket API. This client was developed by reverse-engineering the protocol used by the official Homismart web application.

## Features

- Asynchronous API using `asyncio` and `websockets`.
- Login and session handling for Homismart accounts.
- Real-time device updates via WebSocket.
- Object-oriented interface for:
  - Switchable devices (sockets, lights)
  - Curtain/shutter controls
  - Door locks
  - Hubs
- Custom event system for reacting to device changes, session status, or errors.
- Built-in reconnection and redirection handling.

## Installation

```bash
pip install homismart-client
```

Or from source:

```bash
git clone https://github.com/krafman/homismart-client.git
cd homismart-client
pip install .
```

> ✅ All dependencies (e.g. `websockets`, `python-dotenv`) will be installed automatically.

## Quick Start

### 1. Set your credentials

You can use environment variables or a `.env` file:

```bash
export HOMISMART_USERNAME="your_email@example.com"
export HOMISMART_PASSWORD="your_password"
```

Or create a `.env` file:

```env
HOMISMART_USERNAME="your_email@example.com"
HOMISMART_PASSWORD="your_password"
```

And in your Python script:

```python
from dotenv import load_dotenv
load_dotenv()
```

### 2. Connect and control devices

```python
import asyncio
from homismart_client import HomismartClient

async def main():
    async with HomismartClient() as client:
        await client.login()
        devices = client.session.get_all_devices()
        for device in devices:
            print(f"{device.name} ({device.device_type}): {device.online}")
            if device.supports_on_off:
                await device.turn_on()

asyncio.run(main())
```

## Event Handling Example

You can register callbacks to respond to device changes:

```python
def on_update(device):
    print(f"{device.name} updated: {device}")

client.session.register_event_listener("device_updated", on_update)
```

## Project Status

This project is currently in **Alpha**. The protocol is still being reverse-engineered and APIs may change between versions.

## Requirements

- Python 3.8+
- `websockets>=10.0,<13.0`
- `python-dotenv>=1.0.0`

## License
[![forthebadge](https://forthebadge.com/images/badges/license-mit.svg)](https://forthebadge.com)

MIT © Adir Krafman
