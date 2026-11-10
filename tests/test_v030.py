"""Tests for the 0.3.0 behaviour changes. No network or account needed."""
import asyncio
import json
import warnings
from typing import List, Optional
from unittest.mock import patch

import pytest

import homismart_client.client as client_mod
from homismart_client import (
    AuthenticationError,
    CurtainDevice,
    HomismartClient,
    HomismartDevice,
    SwitchableDevice,
)

_CLOSE = object()


class FakeWS:
    """Scripted WebSocket: yields queued server messages until closed."""

    def __init__(self, messages: Optional[List[str]] = None, end_after: bool = False):
        self.sent: List[str] = []
        self._queue: asyncio.Queue = asyncio.Queue()
        for m in messages or []:
            self._queue.put_nowait(m)
        if end_after:
            self._queue.put_nowait(_CLOSE)
        self.closed = False

    def push(self, message: str) -> None:
        self._queue.put_nowait(message)

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if not self.closed:
            self.closed = True
            self._queue.put_nowait(_CLOSE)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        item = await self._queue.get()
        if item is _CLOSE:
            raise StopAsyncIteration
        return item


LOGIN_OK = '0003{"result": true}'
WRONG_PASSWORD = '9999{"code": 2}'


def _patch_connect(*sockets: FakeWS):
    """Make websockets.connect return the given sockets in order."""
    it = iter(sockets)

    async def fake_connect(url, open_timeout=None, ssl=None):
        return next(it)

    return patch.object(client_mod.websockets, "connect", side_effect=fake_connect)


async def _wait_for(predicate, timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.01)


# --- Login failures ---------------------------------------------------------

@pytest.mark.asyncio
async def test_wrong_password_raises_authentication_error_fast():
    client = HomismartClient("user@example.com", "bad")
    errors = []
    client.session.register_event_listener("session_error", errors.append)

    with _patch_connect(FakeWS([WRONG_PASSWORD])):
        start = asyncio.get_running_loop().time()
        with pytest.raises(AuthenticationError, match="USERNAME_PASSWORD_ERROR"):
            await client.connect(timeout=10)
        assert asyncio.get_running_loop().time() - start < 1.0

    assert errors and errors[-1]["type"] == "authentication_failed"
    assert not client.is_connected
    await client.disconnect()


@pytest.mark.asyncio
async def test_login_response_false_raises_authentication_error():
    client = HomismartClient("user@example.com", "bad")
    with _patch_connect(FakeWS(['0003{"result": false}'])):
        with pytest.raises(AuthenticationError):
            await client.connect(timeout=10)
    await client.disconnect()


@pytest.mark.asyncio
async def test_non_auth_server_error_after_login_is_only_an_event():
    client = HomismartClient("user@example.com", "pw")
    ws = FakeWS([LOGIN_OK])
    errors = []
    client.session.register_event_listener("session_error", errors.append)
    with _patch_connect(ws):
        await client.connect(timeout=5)
        ws.push('9999{"code": 40}')
        await _wait_for(lambda: errors)
    assert errors[0]["type"] == "server_command_error"
    assert "NO_RESPONSE_FROM_DEVICE" in str(errors[0]["exception"])
    assert client.is_logged_in
    await client.disconnect()


# --- Redirect ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_redirect_before_login_reconnects_to_new_host():
    client = HomismartClient("user@example.com", "pw")
    urls = []
    sockets = iter([FakeWS(['0039{"ip": "10.0.0.5", "port": "8443"}']), FakeWS([LOGIN_OK])])

    async def fake_connect(url, open_timeout=None, ssl=None):
        urls.append(url)
        return next(sockets)

    with patch.object(client_mod.websockets, "connect", side_effect=fake_connect):
        await client.connect(timeout=5)

    assert urls[0].startswith("wss://prod.homismart.com")
    assert urls[1] == "wss://10.0.0.5:443/homismartmain/websocket"
    assert client.is_logged_in
    await client.disconnect()


# --- Reconnect and connection events ----------------------------------------

@pytest.mark.asyncio
async def test_connection_lost_and_restored_events():
    client = HomismartClient("user@example.com", "pw")
    events = []
    client.session.register_event_listener("connection_lost", lambda: events.append("lost"))
    client.session.register_event_listener("connection_restored", lambda: events.append("restored"))

    first = FakeWS([LOGIN_OK])
    second = FakeWS([LOGIN_OK])
    with _patch_connect(first, second), patch.object(client_mod, "RECONNECT_BASE_DELAY", 0):
        await client.connect(timeout=5)
        await first.close()  # server drops the connection
        await _wait_for(lambda: events == ["lost", "restored"])

    assert client.is_connected and client.is_logged_in
    await client.disconnect()


@pytest.mark.asyncio
async def test_reconnect_stops_when_credentials_rejected():
    client = HomismartClient("user@example.com", "pw")
    errors = []
    client.session.register_event_listener("session_error", errors.append)

    first = FakeWS([LOGIN_OK])
    second = FakeWS([WRONG_PASSWORD])
    with _patch_connect(first, second), patch.object(client_mod, "RECONNECT_BASE_DELAY", 0):
        await client.connect(timeout=5)
        reconnect_task = client._reconnect_task
        await first.close()
        await asyncio.wait_for(reconnect_task, timeout=2)

    assert not client._keep_running
    assert any(e["type"] == "authentication_failed" for e in errors)
    await client.disconnect()


@pytest.mark.asyncio
async def test_stuck_heartbeat_ends_receive_loop():
    client = HomismartClient("user@example.com", "pw")

    class StuckCloseWS(FakeWS):
        async def close(self, code=1000, reason=""):
            await asyncio.sleep(3600)  # a dead socket never finishes closing

    ws = StuckCloseWS([LOGIN_OK])
    with _patch_connect(ws):
        await client.connect(timeout=5)
        receive_task = client._receive_task
        async def close_times_out(coro, timeout):
            coro.close()  # never awaited: pretend it hung past the timeout
            raise asyncio.TimeoutError

        with patch.object(client_mod.asyncio, "wait_for", side_effect=close_times_out):
            await client._abort_stale_connection()
        await asyncio.wait({receive_task}, timeout=1)
    assert receive_task.done()
    client._websocket = None  # its close() would hang
    await client.disconnect()


# --- Event loop handling ----------------------------------------------------

def test_construct_outside_event_loop_without_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        HomismartClient("user@example.com", "pw")


def test_loop_argument_is_deprecated():
    with pytest.warns(DeprecationWarning):
        HomismartClient("user@example.com", "pw", loop=object())


# --- Device list handling ---------------------------------------------------

def _device_list(*devices) -> str:
    return "0005" + json.dumps(list(devices))


@pytest.mark.asyncio
async def test_device_list_add_update_remove_and_type_change():
    client = HomismartClient("user@example.com", "pw")
    events = []
    for name in ("new_device_added", "device_deleted", "new_hub_added"):
        client.session.register_event_listener(name, lambda d, n=name: events.append((n, d.id, type(d).__name__)))

    ws = FakeWS([LOGIN_OK])
    with _patch_connect(ws):
        await client.connect(timeout=5)
        ws.push(_device_list(
            {"id": "00AABB", "name": "Hub"},
            {"id": "s1", "type": 1, "power": False},
            {"id": "c1", "type": 4, "curtainState": "0"},
        ))
        await _wait_for(lambda: len(client.session.get_all_devices()) == 2)
        assert isinstance(client.session.get_device_by_id("c1"), CurtainDevice)

        events.clear()
        # s1 disappears, c1 changes from shutter to an unknown type.
        ws.push(_device_list({"id": "00AABB"}, {"id": "c1", "type": 99}))
        await _wait_for(lambda: client.session.get_device_by_id("s1") is None)

    assert ("device_deleted", "c1", "CurtainDevice") in events
    assert ("new_device_added", "c1", "HomismartDevice") in events
    assert ("device_deleted", "s1", "SwitchableDevice") in events
    assert events.index(("device_deleted", "c1", "CurtainDevice")) < events.index(
        ("new_device_added", "c1", "HomismartDevice")
    )
    assert type(client.session.get_device_by_id("c1")) is HomismartDevice
    await client.disconnect()


# --- Commands ---------------------------------------------------------------

def _sent_payloads(ws: FakeWS, prefix: str):
    return [json.loads(m[4:]) for m in ws.sent if m.startswith(prefix)]


@pytest.mark.asyncio
async def test_turn_on_is_sent_even_when_cached_state_is_on():
    client = HomismartClient("user@example.com", "pw")
    ws = FakeWS([LOGIN_OK])
    with _patch_connect(ws):
        await client.connect(timeout=5)
        ws.push(_device_list({"id": "s1", "type": 2, "power": True}))
        await _wait_for(lambda: client.session.get_device_by_id("s1"))
        switch = client.session.get_device_by_id("s1")
        assert isinstance(switch, SwitchableDevice) and switch.is_on

        await switch.turn_on()
        await switch.turn_off()

    payloads = _sent_payloads(ws, "0006")
    assert [p["power"] for p in payloads] == [True, False]
    assert all(p["id"] == "s1" for p in payloads)
    await client.disconnect()


@pytest.mark.asyncio
async def test_curtain_open_percentage_is_inverse_of_level():
    client = HomismartClient("user@example.com", "pw")
    ws = FakeWS([LOGIN_OK])
    with _patch_connect(ws):
        await client.connect(timeout=5)
        ws.push(_device_list({"id": "c1", "type": 4, "curtainState": "80"}))
        await _wait_for(lambda: client.session.get_device_by_id("c1"))
        curtain = client.session.get_device_by_id("c1")

        assert curtain.current_level == 80
        assert curtain.open_percentage == 20

        await curtain.set_open_percentage(100)
        await curtain.set_open_percentage(30)
        with pytest.raises(ValueError):
            await curtain.set_open_percentage(101)

    assert [p["curtainState"] for p in _sent_payloads(ws, "0006")] == ["0", "70"]
    await client.disconnect()


def test_two_gang_switch_gangs_share_a_unit_id():
    from homismart_client import DeviceType

    gang = SwitchableDevice(session=None, initial_data={
        "id": "07518733000047-2", "type": 7, "relayNumber": 2, "deviceId": 12001,
    })
    single = SwitchableDevice(session=None, initial_data={"id": "02518744000032", "type": 2})

    assert gang.relay_number == 2
    assert gang.unit_id == "07518733000047"
    assert single.relay_number is None
    assert single.unit_id == "02518744000032"
    assert DeviceType(7) is DeviceType.TWO_GANG_SWITCH is DeviceType.DOUBLE_SWITCH_OR_SOCKET
    assert DeviceType(6).name == "WATER_HEATER_SWITCH"


def test_open_percentage_none_when_unknown():
    curtain = CurtainDevice(session=None, initial_data={"id": "c1", "curtainState": "99"})
    assert curtain.open_percentage is None


# --- TLS context (0.3.1) ----------------------------------------------------

@pytest.mark.asyncio
async def test_given_ssl_context_is_used():
    import ssl as ssl_mod

    context = ssl_mod.SSLContext(ssl_mod.PROTOCOL_TLS_CLIENT)
    client = HomismartClient("user@example.com", "pw", ssl_context=context)
    seen = []

    async def fake_connect(url, open_timeout=None, ssl=None):
        seen.append(ssl)
        return FakeWS([LOGIN_OK])

    with patch.object(client_mod.websockets, "connect", side_effect=fake_connect):
        await client.connect(timeout=5)
    assert seen == [context]
    await client.disconnect()


@pytest.mark.asyncio
async def test_default_ssl_context_is_built_off_the_event_loop():
    import threading

    threads = []

    def create_default_context():
        threads.append(threading.current_thread())
        return "default-context"

    seen = []

    async def fake_connect(url, open_timeout=None, ssl=None):
        seen.append(ssl)
        return FakeWS([LOGIN_OK])

    with (
        patch.object(client_mod, "_default_ssl_context", None),
        patch.object(client_mod.ssl, "create_default_context", create_default_context),
        patch.object(client_mod.websockets, "connect", side_effect=fake_connect),
    ):
        for _ in range(2):  # built once, then reused
            client = HomismartClient("user@example.com", "pw")
            await client.connect(timeout=5)
            await client.disconnect()

    assert seen == ["default-context", "default-context"]
    assert len(threads) == 1 and threads[0] is not threading.main_thread()
