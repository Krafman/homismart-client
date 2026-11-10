# Changelog

## 0.3.0 — unreleased

### Changed (behaviour)
- **A wrong password fails immediately.** `connect()` now raises `AuthenticationError`
  as soon as the server rejects the login. The server signals this with error code 2
  (`USERNAME_PASSWORD_ERROR`), not with a failed login response; codes 3 and 11 are
  treated the same way. Before, the client waited for the full timeout and raised
  `asyncio.TimeoutError`.
- **Reconnecting stops on rejected credentials** (for example after a password change)
  instead of retrying forever. A `session_error` event of type `authentication_failed`
  is emitted.
- **On/off and lock commands are always sent**, even if the cached state already
  matches. Before, a stale cache could silently swallow a command.
- **A device whose type changes** is now announced as `device_deleted` (old object)
  followed by `new_device_added` (new object), instead of a second `new_device_added`
  for the same ID.
- The `loop` argument of `HomismartClient` is deprecated and ignored; the running
  event loop is used. Constructing a client outside a running loop no longer touches
  `asyncio.get_event_loop()`.
- Python 3.10 or newer is required.
- `python-dotenv` is no longer installed as a dependency; only the examples use it.

### Added
- `connection_lost` and `connection_restored` events.
- `CurtainDevice.open_percentage` and `set_open_percentage()`: positions where
  0 = closed and 100 = open, the inverse of the vendor's `current_level`.
- `async with HomismartClient(...)` support.
- `relay_number` and `unit_id` on every device, so the two gangs of a two-gang
  switch can be grouped under their physical unit.
- `DeviceType.TWO_GANG_SWITCH` (7) and `DeviceType.WATER_HEATER_SWITCH` (6), named
  from real hardware. The old names `DOUBLE_SWITCH_OR_SOCKET` and
  `SWITCH_MULTI_GANG_A` still work as aliases.
- Python 3.14 is tested and supported.
- Device classes are exported from the top-level package.
- Server errors without a message are logged with the error code's name.
- Tests for login failure, connection events, redirects, device lists and commands,
  and a GitHub Actions workflow that runs them on every push and pull request.
- The PyPI release workflow now runs the tests, refuses to publish if the release
  tag doesn't match `__version__`, and checks the built package before uploading.

### Fixed
- A heartbeat that gets stuck now forces a reconnect instead of leaving a dead
  connection open.

### Removed
- Leftover demo code (`if __name__ == "__main__"` blocks) and fallback imports from
  the library modules. `tests/test_enumerate_devices.py` (a live script, not a test)
  moved to `examples/enumerate_devices.py`.

## 0.2.1 — 2026-05-24
- Default server changed from `prom.homismart.com` to `prod.homismart.com`.
  `prom` was a typo in the original code that worked for a while; by November 2026
  the `prom` hostname no longer resolved, so **0.2.0 and earlier cannot connect**
  with default settings.

## 0.2.0 — 2026-03-27
- Connection robustness overhaul: `connect()` returns after login, exponential
  backoff with jitter, heartbeat timeouts, redirect handling, and the first unit tests.

## 0.1.x — 2025-06 to 2025-07
- Initial releases: login, device list, push updates, switches, curtains, locks, hubs.
