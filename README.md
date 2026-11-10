# Homismart Client (Unofficial Python Library)

![PyPI - Version](https://img.shields.io/pypi/v/homismart-client)
![Python Versions](https://img.shields.io/pypi/pyversions/homismart-client)
![License](https://img.shields.io/pypi/l/homismart-client)
![Tests](https://github.com/krafman/homismart-client/actions/workflows/tests.yml/badge.svg)

> ⚠️ **Disclaimer**: This is an unofficial, community-driven library. It is not affiliated with, authorized, or endorsed by Homismart or its parent company. Use at your own risk — changes to Homismart's API may break functionality without notice.

An asyncio Python client for Homismart smart home devices. It talks to the same cloud WebSocket API as the official app, which was reverse-engineered from the vendor's web client. It powers the [Home Assistant integration](https://github.com/Krafman/ha-homismart).

## Features

- Log in with your Homismart account and receive live (push) device updates.
- Control switches, sockets, lights and curtains/shutters; read hubs and locks.
- Automatic reconnection with exponential backoff, heartbeats and server redirects.
- Events for device changes, connection loss and recovery, and errors.

## Installation

```bash
pip install homismart-client
```

Requires Python 3.10 or newer.

## Quick start

```python
import asyncio
import os

from homismart_client import AuthenticationError, HomismartClient, SwitchableDevice


async def main():
    try:
        async with HomismartClient(
            os.environ["HOMISMART_USERNAME"], os.environ["HOMISMART_PASSWORD"]
        ) as client:
            await asyncio.sleep(3)  # the device list arrives just after login

            for device in client.session.get_all_devices():
                print(device)  # name, ID, type code, online state

            lamp = next(
                d for d in client.session.get_all_devices()
                if isinstance(d, SwitchableDevice)
            )
            await lamp.turn_on()
    except AuthenticationError:
        print("Wrong username or password.")


asyncio.run(main())
```

`connect()` (or entering `async with`) returns as soon as login succeeds. A wrong
username or password raises `AuthenticationError` immediately; a server that
doesn't answer raises `asyncio.TimeoutError` after `timeout` seconds (default 30).

`examples/` has two runnable scripts that read credentials from a `.env` file
(`pip install python-dotenv` first; `.env` files are git-ignored).

## Devices

| Class | Type codes | Main members |
|---|---|---|
| `SwitchableDevice` | 1, 2, 6, 7, 8 | `is_on`, `turn_on()`, `turn_off()`, `toggle()` |
| `CurtainDevice` | 4 (shutter), 5 (curtain) | `current_level`, `open_percentage`, `set_level()`, `set_open_percentage()`, `open_fully()`, `close_fully()`, `stop()` |
| `LockDevice` | 9 | `is_locked`, `lock_device()`, `unlock_device()` |
| `HomismartHub` | IDs starting with `00` | `is_online` |

Every device also has `id`, `name`, `is_online`, `device_type_code`, `pid`
(parent hub ID) and `raw` (the full server payload).

**Two-gang switches** (type 7) appear as one device per gang, with IDs like
`07000000000002-1` and `07000000000002-2`. `relay_number` tells you the gang and
`unit_id` gives the physical switch they share (`07000000000002`).

**Curtain positions.** Homismart counts the other way from most platforms:
`current_level` 0 means fully open and 100 means fully closed. If you want 0 to mean
closed (as Home Assistant does), use `open_percentage` and `set_open_percentage()`.

**Commands are always sent.** `turn_on()` sends the command even if the cached
state already says on, because the cache can be stale after a dropped connection.
The device object updates when the server pushes the new state.

## Events

Register a callback on the session. Callbacks are called synchronously on the
event loop, so keep them short.

```python
client.session.register_event_listener("device_updated", lambda d: print(d))
```

| Event | Argument | When |
|---|---|---|
| `new_device_added` | device | A device is first seen (including the initial device list). |
| `device_updated` | device | A device's state changed. |
| `device_deleted` | device | A device was removed, or its type changed (it is then re-added). |
| `new_hub_added`, `hub_updated`, `hub_deleted` | hub | Same, for hubs. |
| `session_authenticated` | username | Login succeeded (also after each reconnect). |
| `connection_lost` | — | An established connection dropped; reconnecting has started. |
| `connection_restored` | — | Reconnected and logged in again. |
| `session_error` | dict with `type` | Server or connection errors. `type == "authentication_failed"` means the credentials were rejected; the client then stops reconnecting. |

## Reconnection

After a successful `connect()`, the client keeps the connection alive by itself:

- A heartbeat is sent every 30 seconds of silence. If it gets stuck, the connection is dropped and rebuilt.
- After a drop, it reconnects with exponential backoff (5 s doubling up to 5 min, with jitter) until `disconnect()` is called.
- If the server rejects the stored credentials on reconnect (for example after a password change), it stops and emits `session_error` with type `authentication_failed`.

## Development

```bash
pip install -e . pytest pytest-asyncio
pytest
```

Tests use a mocked WebSocket and need no account. See `ARCHITECTURE.md` for
how the pieces fit and `CHANGELOG.md` for release history.

## License

MIT © Adir Krafman
