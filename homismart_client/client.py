"""
homismart_client/client.py

Defines the HomismartClient class, the main entry point for interacting
with the Homismart WebSocket API.
"""
import asyncio
import json
import logging
import random
import time
from typing import Optional, Dict, Any, cast

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Attempt to import dependent modules from the package
try:
    from .enums import RequestPrefix, ReceivePrefix
    from .exceptions import (
        AuthenticationError, ConnectionError, HomismartError, CommandError
    )
    from .session import HomismartSession
    from .commands import HomismartCommandBuilder
    from .utils import md5_hash
except ImportError:
    # Fallbacks for standalone development/testing
    from enums import RequestPrefix, ReceivePrefix # type: ignore
    from exceptions import ( # type: ignore
        AuthenticationError, ConnectionError, HomismartError, CommandError
    )
    from session import HomismartSession # type: ignore
    from commands import HomismartCommandBuilder # type: ignore
    from utils import md5_hash # type: ignore


logger = logging.getLogger(__name__)

DEFAULT_SUBDOMAIN = "prom"
WEBSOCKET_URL_TEMPLATE = "wss://{subdomain}.homismart.com:443/homismartmain/websocket"
RECONNECT_BASE_DELAY = 5          # Initial reconnect delay in seconds
RECONNECT_MAX_DELAY = 300         # Maximum reconnect delay (5 minutes)
RECONNECT_BACKOFF_FACTOR = 2.0    # Exponential backoff multiplier
HEARTBEAT_INTERVAL_SECONDS = 30   # Send a heartbeat if no other messages are sent

class HomismartClient:
    """
    The main client for interacting with the Homismart WebSocket API.
    Manages the connection, authentication, and message flow.
    """

    def __init__(
        self,
        username: str,
        password: str,
        subdomain: str = DEFAULT_SUBDOMAIN,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initializes the HomismartClient.

        Args:
            username: The Homismart account username (email).
            password: The Homismart account password (plain text).
            subdomain: The server subdomain (e.g., "prom").
            loop: The asyncio event loop to use. If None, asyncio.get_event_loop() is used.
        """
        self._username: str = username
        self._password_hash: str = md5_hash(password) # Hash password immediately
        self._subdomain: str = subdomain
        self._ws_url: str = WEBSOCKET_URL_TEMPLATE.format(subdomain=self._subdomain)
        
        self._loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._session: HomismartSession = HomismartSession(self) # Client provides itself to session
        self._command_builder: HomismartCommandBuilder = HomismartCommandBuilder()

        self._is_connected: bool = False
        self._is_logged_in: bool = False # This will be set by the session upon successful login
        self._keep_running: bool = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._login_event: asyncio.Event = asyncio.Event()
        self._last_message_sent_time: float = 0.0
        self._reconnect_attempt: int = 0

    @property
    def session(self) -> HomismartSession:
        """Provides access to the HomismartSession instance for device interaction."""
        return self._session

    @property
    def is_connected(self) -> bool:
        """Returns True if the WebSocket is currently connected."""
        return self._is_connected

    @property
    def is_logged_in(self) -> bool:
        """Returns True if the client is authenticated with the server."""
        return self._is_logged_in

    async def connect(self, timeout: float = 30.0) -> None:
        """
        Connects to the Homismart server, authenticates, and returns.

        After successful login the receive loop, heartbeat, and background
        reconnect loop are started as tasks. The caller regains control
        once login succeeds (or *timeout* seconds elapse).

        Args:
            timeout: Maximum seconds to wait for the initial login.

        Raises:
            asyncio.TimeoutError: If login does not complete within *timeout*.
            ConnectionError: If the WebSocket connection cannot be established.
        """
        if self._keep_running:
            logger.warning("Connect called while already running. Ignoring.")
            return

        self._keep_running = True
        self._reconnect_attempt = 0
        self._login_event = asyncio.Event()
        logger.info("Starting Homismart client...")

        try:
            # First connection attempt — with a caller-visible timeout.
            await self._open_and_login(timeout)
        except Exception:
            # If first connection fails, clean up and re-raise so the
            # caller knows immediately.
            self._keep_running = False
            await self._cleanup_connection()
            raise

        # First login succeeded — launch background tasks.
        # _receive_task is already running (started in _open_and_login).
        self._heartbeat_task = self._loop.create_task(self._send_heartbeats())
        self._reconnect_task = self._loop.create_task(self._reconnect_loop())
        logger.info("Homismart client connected and running.")

    async def _open_and_login(self, timeout: float) -> None:
        """Open the WebSocket and wait for a successful login response.

        The server may send a redirect (prefix "0039") before the login
        response.  When that happens the WebSocket is closed and
        ``self._ws_url`` is updated by ``_handle_redirect``.  This method
        detects the redirect and retries on the new URL within the same
        overall *timeout*.
        """
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"Login did not complete within {timeout}s"
                )

            logger.info(f"Attempting to connect to WebSocket: {self._ws_url}")
            self._login_event.clear()
            url_before = self._ws_url

            ws = await asyncio.wait_for(
                websockets.connect(self._ws_url, open_timeout=10),
                timeout=remaining,
            )
            self._websocket = ws
            self._is_connected = True
            logger.info(f"WebSocket connection established to {self._ws_url}.")

            # Start receive loop as a task so it can process the login response.
            self._receive_task = self._loop.create_task(self._receive_loop())

            await self._on_open()

            # Wait for either login success or the receive loop ending (redirect / error).
            login_wait = asyncio.ensure_future(self._login_event.wait())

            done, pending = await asyncio.wait(
                [login_wait, self._receive_task],
                timeout=max(deadline - asyncio.get_event_loop().time(), 1.0),
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel the login_wait if it didn't finish, but never cancel
            # _receive_task here — it must keep running after login.
            if login_wait in pending:
                login_wait.cancel()
                try:
                    await login_wait
                except asyncio.CancelledError:
                    pass

            if self._login_event.is_set():
                # Login succeeded.
                break

            if self._ws_url != url_before:
                # Server sent a redirect — _ws_url was updated, retry.
                logger.info(f"Redirected to {self._ws_url}, reconnecting...")
                await self._cleanup_connection()
                continue

            # Neither login nor redirect — something else went wrong.
            raise asyncio.TimeoutError(
                f"Login did not complete within {timeout}s"
            )

        if not self._is_logged_in:
            raise ConnectionError("Authentication failed")

        self._reconnect_attempt = 0

    async def _reconnect_loop(self) -> None:
        """
        Background task: waits for the receive loop to end, then
        reconnects with exponential backoff until disconnect() is called.
        """
        while self._keep_running:
            # Wait for the current receive loop to finish (connection dropped).
            if self._receive_task and not self._receive_task.done():
                try:
                    await self._receive_task
                except Exception:
                    pass  # Errors are handled inside _receive_loop.

            if not self._keep_running:
                break

            # Connection was lost — clean up and reconnect.
            await self._cleanup_connection()

            delay = min(
                RECONNECT_BASE_DELAY * (RECONNECT_BACKOFF_FACTOR ** self._reconnect_attempt),
                RECONNECT_MAX_DELAY,
            )
            jitter = random.uniform(0, delay * 0.25)
            total_delay = delay + jitter
            logger.info(f"Will attempt to reconnect in {total_delay:.1f}s (attempt {self._reconnect_attempt + 1})...")
            await asyncio.sleep(total_delay)
            self._reconnect_attempt += 1

            if not self._keep_running:
                break

            try:
                await self._open_and_login(timeout=30.0)
                # Restart heartbeat for the new connection.
                # _receive_task is already running (started in _open_and_login).
                self._heartbeat_task = self._loop.create_task(self._send_heartbeats())
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {e}", exc_info=False)
                self._emit_session_error("connection_operational_error", e)
                await self._cleanup_connection()
                # Loop continues — will retry with next backoff delay.

        logger.info("Reconnect loop stopped.")

    async def _cleanup_connection(self) -> None:
        """Cancel heartbeat, close WebSocket, and reset state flags."""
        self._is_connected = False
        self._is_logged_in = False

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._websocket:
            try:
                await self._websocket.close()
            except WebSocketException:
                pass
        self._websocket = None


    async def _on_open(self) -> None:
        """Called when the WebSocket connection is successfully opened."""
        logger.info("WebSocket connection opened. Initiating login sequence.")
        # Reset login status before attempting new login
        self._is_logged_in = False
        await self._login()


    async def _receive_loop(self) -> None:
        """Continuously listens for incoming messages from the WebSocket."""
        if not self._websocket:
            logger.error("Receive loop called without an active WebSocket connection.")
            return

        logger.info("Starting to listen for incoming messages...")
        try:
            async for raw_message in self._websocket:
                if isinstance(raw_message, str):
                    logger.debug(f"RECV RAW: {raw_message}")
                    if len(raw_message) >= 4:
                        prefix_str = raw_message[:4]
                        payload_json_str = raw_message[4:]
                        try:
                            # Handle cases where payload might be empty or not valid JSON
                            # for certain prefixes, though most expect JSON.
                            data: Dict[str, Any] = {}
                            if payload_json_str and payload_json_str != "{}":
                                data = json.loads(payload_json_str)
                            elif payload_json_str == "{}":
                                data = {} # Explicit empty dict for "{}"
                            
                            self._session.dispatch_message(prefix_str, data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON payload: '{payload_json_str}' for prefix '{prefix_str}'")
                            self._emit_session_error("json_decode_error", ValueError(f"Invalid JSON: {payload_json_str}"))
                        except Exception as e:
                            logger.error(f"Error dispatching message (Prefix: {prefix_str}): {e}", exc_info=True)
                            self._emit_session_error("message_dispatch_error", e)
                    else:
                        logger.warning(f"Received message too short to process: '{raw_message}'")
                else:
                    logger.warning(f"Received non-text message (type: {type(raw_message)}): {raw_message}")
        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed by server: Code={e.code}, Reason='{e.reason}'")
            self._emit_session_error("connection_closed_by_server", e)
        except WebSocketException as e:
            logger.error(f"WebSocket exception during receive loop: {e}", exc_info=True)
            self._emit_session_error("websocket_exception_receive_loop", e)
        except Exception as e:
            logger.error(f"Unexpected error in receive loop: {e}", exc_info=True)
            self._emit_session_error("unexpected_receive_loop_error", e)
        finally:
            self._is_connected = False # Ensure status is updated if loop exits
            self._is_logged_in = False


    async def _send_heartbeats(self) -> None:
        """Periodically sends a heartbeat message to keep the connection alive."""
        while self._keep_running and self._is_connected:
            try:
                # Only send heartbeat if no other message was sent recently
                if time.time() - self._last_message_sent_time > HEARTBEAT_INTERVAL_SECONDS:
                    logger.debug("Sending heartbeat...")
                    await asyncio.wait_for(
                        self.send_command_raw(RequestPrefix.HEARTBEAT, {}),
                        timeout=10.0,
                    )
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS / 2) # Check more frequently
            except asyncio.TimeoutError:
                logger.warning("Heartbeat: Send timed out. Connection may be stale. Stopping heartbeats.")
                break
            except ConnectionClosed:
                logger.warning("Heartbeat: Connection closed. Stopping heartbeats.")
                break
            except WebSocketException as e:
                logger.error(f"Heartbeat: WebSocket error: {e}. Stopping heartbeats.")
                break
            except asyncio.CancelledError:
                logger.debug("Heartbeat task cancelled.")
                break
            except Exception as e:
                logger.error(f"Heartbeat: Unexpected error: {e}", exc_info=True)
                # Continue trying unless it's a connection issue
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


    async def send_command_raw(self, prefix: RequestPrefix, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Builds a command using HomismartCommandBuilder and sends it over the WebSocket.
        This is the primary method for sending commands.

        Args:
            prefix: The RequestPrefix enum member for the command.
            payload: An optional dictionary for the JSON payload.

        Raises:
            ConnectionError: If the WebSocket is not connected.
        """
        ws = self._websocket
        if not ws or not self._is_connected:
            msg = "WebSocket is not connected. Cannot send command."
            logger.error(msg)
            raise ConnectionError(msg)

        # Use the instance of HomismartCommandBuilder
        message_str = self._command_builder._build_message(prefix, payload)

        try:
            logger.debug(f"SENT CMD: {prefix.name} ({prefix.value}) | Payload: {json.dumps(payload) if payload else '{}'}")
            await ws.send(message_str)
            self._last_message_sent_time = time.time()
        except WebSocketException as e:
            logger.error(f"Failed to send command {prefix.name}: {e}", exc_info=True)
            # Mark as disconnected to trigger reconnect logic
            self._is_connected = False 
            self._is_logged_in = False
            self._emit_session_error("send_command_error", e)
            raise ConnectionError(f"Failed to send command: {e}") from e


    async def _login(self) -> None:
        """Sends the login command to the server."""
        logger.info(f"Attempting to log in as {self._username}...")
        try:
            # HomismartCommandBuilder is now an instance member
            # No, command builder is a static class, so it's fine.
            # Actually, the plan was to make it an instance. Let's stick to that.
            # The session will call this client's send_command_raw.
            # The client itself will use the builder when sending.
            await self.send_command_raw(
                RequestPrefix.LOGIN,
                {"username": self._username, "password": self._password_hash}
            )
        except ConnectionError:
            logger.error("Login failed: Not connected.")
            # Reconnect logic in connect() will handle this.
        except Exception as e:
            logger.error(f"An unexpected error occurred during login attempt: {e}", exc_info=True)
            self._emit_session_error("login_attempt_error", e)

    async def _request_device_list(self) -> None:
        """Requests the list of all devices from the server."""
        if not self._is_logged_in:
            logger.warning("Cannot request device list: Not logged in.")
            return
        logger.info("Requesting device list from server...")
        try:
            await self.send_command_raw(RequestPrefix.LIST_DEVICES, {})
        except ConnectionError:
            logger.error("Device list request failed: Not connected.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during device list request: {e}", exc_info=True)
            self._emit_session_error("device_list_request_error", e)
            
    async def _accept_terms_and_conditions(self) -> None:
        """Sends the command to accept terms and conditions."""
        if not self._is_logged_in: # Or maybe this can be sent before full login? Check JS flow.
                                   # SocketMsgContainer showed it after lre, before flre (list devices)
            logger.warning("Cannot accept terms: Not logged in (or login not fully processed).")
            # return # Let's assume it can be sent if connection is open
        logger.info("Sending command to accept terms and conditions...")
        try:
            await self.send_command_raw(RequestPrefix.ACCEPT_TERMS_CONDITIONS, {})
        except ConnectionError:
            logger.error("Accept terms command failed: Not connected.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during accept terms command: {e}", exc_info=True)
            self._emit_session_error("accept_terms_error", e)


    async def _handle_redirect(self, new_ip: str, new_port: int) -> None:
        """
        Handles server redirection by updating the WebSocket URL and
        triggering a reconnection (which includes re-login).
        """
        logger.info(f"Handling redirection: New IP='{new_ip}', New Port='{new_port}'.")

        # Vendor JS always uses port 443 for WSS: wss://<ip>:443/homismartmain/websocket
        self._ws_url = f"wss://{new_ip}:443/homismartmain/websocket"
        logger.info(f"Updated WebSocket URL for redirection: {self._ws_url}")

        if self._websocket and self._is_connected:
            logger.info("Closing current connection to redirect...")
            await self._websocket.close(code=1000, reason="Client redirecting")
            # The reconnect loop will detect the closed connection and
            # reconnect using the new URL.
        else:
            logger.info("Not currently connected, next connection attempt will use the new URL.")


    async def disconnect(self) -> None:
        """
        Disconnects from the WebSocket server and stops reconnection attempts.
        """
        logger.info("Disconnect requested. Stopping client...")
        self._keep_running = False

        # Cancel background tasks.
        for task_attr in ("_heartbeat_task", "_receive_task", "_reconnect_task"):
            task = getattr(self, task_attr, None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            setattr(self, task_attr, None)

        if self._websocket:
            try:
                await self._websocket.close(code=1000, reason="Client initiated disconnect")
            except WebSocketException as e:
                logger.warning(f"Exception during explicit disconnect: {e}")

        # Ensure flags are set correctly.
        self._is_connected = False
        self._is_logged_in = False
        self._websocket = None
        logger.info("Client disconnect process complete.")

    def _schedule_task(self, coro) -> asyncio.Task:
        """Helper to schedule a task on the client's event loop."""
        return self._loop.create_task(coro)

    def _emit_session_error(self, error_type: str, exception_obj: Exception) -> None:
        """Emits a session_error event via the session."""
        self._session._emit_event("session_error", {
            "type": error_type,
            "exception_class": exception_obj.__class__.__name__,
            "message": str(exception_obj),
            "exception_object": exception_obj
        })

