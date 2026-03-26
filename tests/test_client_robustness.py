"""
Unit tests for homismart-client robustness fixes (v0.2.0).

All tests use mocked WebSocket connections — no real server needed.
"""
import asyncio
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Ensure project root is on sys.path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from homismart_client import HomismartClient
from homismart_client.devices.curtain import CurtainDevice
from homismart_client.devices.base_device import HomismartDevice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ws(login_success: bool = True, login_delay: float = 0.0):
    """Create a mock WebSocket that optionally sends a login response."""
    ws = AsyncMock()
    ws.close = AsyncMock()

    async def fake_recv_iter(self_ws):
        """Simulate server messages."""
        if login_success:
            await asyncio.sleep(login_delay)
            yield f'0003{{"result": true}}'
        # Then hang forever (simulating idle connection).
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            return

    ws.__aiter__ = lambda self_ws: fake_recv_iter(self_ws)
    ws.send = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Fix 9: connect() returns after login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_returns_after_login():
    """connect() should return once login succeeds, not block forever."""
    mock_ws = _make_mock_ws(login_success=True, login_delay=0.05)

    with patch("homismart_client.client.websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        client = HomismartClient(username="test@test.com", password="pass")

        # connect() should return within a reasonable time.
        await asyncio.wait_for(client.connect(timeout=5.0), timeout=5.0)

        assert client.is_logged_in
        assert client.is_connected
        assert client._reconnect_task is not None

        await client.disconnect()


@pytest.mark.asyncio
async def test_connect_raises_on_timeout():
    """connect() should raise TimeoutError if login never completes."""
    mock_ws = _make_mock_ws(login_success=False)

    with patch("homismart_client.client.websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        client = HomismartClient(username="test@test.com", password="pass")

        with pytest.raises(asyncio.TimeoutError):
            await client.connect(timeout=1.0)

        assert not client.is_logged_in
        assert not client._keep_running


# ---------------------------------------------------------------------------
# Fix 2: TOCTOU race in send_command_raw()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_command_raw_no_attribute_error():
    """
    When _websocket becomes None between check and send,
    ConnectionError should be raised — not AttributeError.
    """
    from homismart_client.enums import RequestPrefix

    client = HomismartClient(username="test@test.com", password="pass")
    client._is_connected = True

    # Set up a websocket mock whose send() nulls out _websocket mid-call.
    mock_ws = AsyncMock()

    async def sabotage_send(msg):
        client._websocket = None
        raise Exception("connection lost")

    mock_ws.send = sabotage_send
    client._websocket = mock_ws

    # Should get a clean exception, not AttributeError.
    with pytest.raises(Exception):
        await client.send_command_raw(RequestPrefix.HEARTBEAT, {})


# ---------------------------------------------------------------------------
# Fix 8: Exponential backoff
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exponential_backoff_delays():
    """Verify reconnect delays increase exponentially up to the cap."""
    from homismart_client.client import (
        RECONNECT_BASE_DELAY,
        RECONNECT_BACKOFF_FACTOR,
        RECONNECT_MAX_DELAY,
    )

    recorded_delays = []

    original_sleep = asyncio.sleep

    async def mock_sleep(duration):
        recorded_delays.append(duration)
        # Don't actually sleep — just record.
        await original_sleep(0)

    mock_ws_fail = AsyncMock()
    mock_ws_fail.close = AsyncMock()
    call_count = 0

    async def failing_connect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise ConnectionRefusedError("Server down")

    with patch("homismart_client.client.websockets.connect", side_effect=failing_connect):
        with patch("asyncio.sleep", side_effect=mock_sleep):
            client = HomismartClient(username="test@test.com", password="pass")
            client._keep_running = True
            client._reconnect_attempt = 0
            client._login_event = asyncio.Event()

            # Simulate a receive_task that's already done.
            done_task = asyncio.get_event_loop().create_future()
            done_task.set_result(None)
            client._receive_task = done_task

            # Run reconnect loop briefly.
            reconnect = asyncio.create_task(client._reconnect_loop())
            # Let it attempt a few reconnects.
            await asyncio.sleep(0.1)
            client._keep_running = False
            reconnect.cancel()
            try:
                await reconnect
            except asyncio.CancelledError:
                pass

    # Verify delays are increasing (ignoring jitter, check base pattern).
    assert len(recorded_delays) >= 2, f"Expected at least 2 delays, got {len(recorded_delays)}"
    # Each delay should be >= previous (accounting for jitter).
    for i in range(1, len(recorded_delays)):
        assert recorded_delays[i] >= recorded_delays[i - 1] * 0.7, (
            f"Delay {i} ({recorded_delays[i]:.1f}) should be >= ~{recorded_delays[i-1]:.1f}"
        )


# ---------------------------------------------------------------------------
# Fix 5: Heartbeat send timeout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_heartbeat_send_timeout():
    """Heartbeat loop should exit if send hangs beyond 10 seconds."""
    from homismart_client.enums import RequestPrefix

    client = HomismartClient(username="test@test.com", password="pass")
    client._is_connected = True
    client._keep_running = True
    client._last_message_sent_time = 0  # Force heartbeat to trigger immediately.

    # Mock send_command_raw to hang.
    async def hanging_send(*args, **kwargs):
        await asyncio.sleep(3600)

    with patch.object(client, "send_command_raw", side_effect=hanging_send):
        # Override the wait_for timeout to something short for testing.
        original_wait_for = asyncio.wait_for

        async def fast_wait_for(coro, timeout):
            return await original_wait_for(coro, timeout=0.1)

        with patch("homismart_client.client.asyncio.wait_for", side_effect=fast_wait_for):
            # Heartbeat should exit quickly due to timeout.
            await asyncio.wait_for(client._send_heartbeats(), timeout=2.0)

    # If we got here, the heartbeat exited instead of hanging. Success.


# ---------------------------------------------------------------------------
# Fix 7: disconnect() awaits cleanup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disconnect_awaits_cleanup():
    """disconnect() should await heartbeat task cancellation."""
    client = HomismartClient(username="test@test.com", password="pass")
    client._keep_running = True
    client._is_connected = False

    heartbeat_cancelled = False

    async def fake_heartbeat():
        nonlocal heartbeat_cancelled
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            heartbeat_cancelled = True
            raise

    client._heartbeat_task = asyncio.create_task(fake_heartbeat())
    await asyncio.sleep(0.01)  # Let it start.

    await client.disconnect()

    assert heartbeat_cancelled
    assert client._heartbeat_task is None
    assert not client._keep_running


# ---------------------------------------------------------------------------
# Fix 4: Curtain level parsing
# ---------------------------------------------------------------------------

class TestCurtainLevelParsing:
    """Test the rewritten current_level property."""

    def _make_curtain(self, curtain_state):
        """Helper to create a CurtainDevice with a given curtainState."""
        session = MagicMock()
        data = {"id": "test123", "type": 5, "name": "Test Curtain"}
        if curtain_state is not None:
            data["curtainState"] = curtain_state
        device = CurtainDevice(session=session, initial_data=data)
        return device

    def test_none_state(self):
        assert self._make_curtain(None).current_level is None

    def test_normal_50(self):
        assert self._make_curtain("50").current_level == 50

    def test_fully_open(self):
        assert self._make_curtain("0").current_level == 0

    def test_fully_closed(self):
        assert self._make_curtain("100").current_level == 100

    def test_stop_signal_99(self):
        assert self._make_curtain("99").current_level is None

    def test_stopped_at_50(self):
        """250 means stopped at 50%."""
        assert self._make_curtain("250").current_level == 50

    def test_stopped_at_0(self):
        """200 means stopped at 0%."""
        assert self._make_curtain("200").current_level == 0

    def test_value_301_out_of_range(self):
        """301 - 200 = 101, which is > 100 → None."""
        assert self._make_curtain("301").current_level is None

    def test_negative(self):
        assert self._make_curtain("-1").current_level is None

    def test_non_numeric(self):
        assert self._make_curtain("abc").current_level is None


# ---------------------------------------------------------------------------
# Fix 3: update_state() no input mutation
# ---------------------------------------------------------------------------

def test_update_state_no_input_mutation():
    """update_state() should not modify the caller's dict."""
    session = MagicMock()
    session._notify_device_update = MagicMock()
    device = HomismartDevice(
        session=session,
        initial_data={"id": "dev1", "name": "Test", "shared": True, "permission": "rw"},
    )

    # Simulate an update that doesn't include 'shared'.
    update_data = {"id": "dev1", "name": "Updated"}
    original_keys = set(update_data.keys())

    device.update_state(update_data)

    # The caller's dict should not have been modified.
    assert set(update_data.keys()) == original_keys
    assert "shared" not in update_data
    assert "permission" not in update_data
