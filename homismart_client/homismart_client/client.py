"""
homismart_client/client.py

Defines the HomismartClient class, the main entry point for interacting
with the Homismart WebSocket API.
"""
import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, cast

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode, WebSocketException

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
RECONNECT_DELAY_SECONDS = 10
HEARTBEAT_INTERVAL_SECONDS = 30 # Send a heartbeat if no other messages are sent

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
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_message_sent_time: float = 0.0

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

    async def connect(self) -> None:
        """
        Establishes a WebSocket connection to the Homismart server and starts listening.
        This method will run indefinitely, attempting to reconnect on disconnections,
        until disconnect() is called.
        """
        if self._keep_running:
            logger.warning("Connect called while already running. Ignoring.")
            return

        self._keep_running = True
        logger.info("Starting Homismart client...")

        while self._keep_running:
            try:
                logger.info(f"Attempting to connect to WebSocket: {self._ws_url}")
                # Set a timeout for the connection attempt
                async with websockets.connect(self._ws_url, open_timeout=10) as ws:
                    self._websocket = ws
                    self._is_connected = True
                    logger.info(f"WebSocket connection established to {self._ws_url}.")
                    
                    # The on_open logic (sending login) is now triggered by the session
                    # after the client signals connection.
                    # We can directly call the login sequence initiator here.
                    await self._on_open() 

                    if self._heartbeat_task is None or self._heartbeat_task.done():
                        self._heartbeat_task = self._loop.create_task(self._send_heartbeats())
                    
                    # Start the message listening loop
                    await self._receive_loop()

            except InvalidStatusCode as e:
                logger.error(f"WebSocket connection failed with status code {e.status_code}. URL: {self._ws_url}")
                self._is_connected = False
                self._websocket = None # Ensure websocket is None if connection failed
                # No automatic retry for HTTP errors like 401/403 during handshake.
                # This might indicate a persistent issue (e.g. wrong URL, server down).
                self._emit_session_error("connection_failed_status", e)
                if not self._keep_running: break # Exit if disconnect was called
                await asyncio.sleep(RECONNECT_DELAY_SECONDS * 2) # Longer delay for status code errors
            except (ConnectionRefusedError, OSError, WebSocketException, asyncio.TimeoutError) as e:
                logger.error(f"WebSocket connection/operational error: {e}. URL: {self._ws_url}", exc_info=False) # exc_info=True for more detail
                self._is_connected = False
                self._websocket = None
                self._emit_session_error("connection_operational_error", e)
            except Exception as e:
                logger.error(f"An unexpected error occurred in the connect loop: {e}", exc_info=True)
                self._is_connected = False
                self._websocket = None
                self._emit_session_error("unexpected_connection_loop_error", e)
            finally:
                self._is_connected = False
                self._is_logged_in = False # Reset login status on disconnect
                if self._websocket:
                    try:
                        await self._websocket.close()
                    except WebSocketException:
                        pass # Already closed or error during close
                self._websocket = None
                logger.info("WebSocket connection closed.")

                if self._keep_running:
                    logger.info(f"Will attempt to reconnect in {RECONNECT_DELAY_SECONDS} seconds...")
                    await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                else:
                    logger.info("Client stopping as per request.")
                    break # Exit the while loop if _keep_running is False
        
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                logger.debug("Heartbeat task cancelled.")
        logger.info("Homismart client stopped.")


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
                    await self.send_command_raw(RequestPrefix.HEARTBEAT, {})
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS / 2) # Check more frequently
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
        if not self._websocket or not self._is_connected:
            msg = "WebSocket is not connected. Cannot send command."
            logger.error(msg)
            raise ConnectionError(msg)

        # Use the instance of HomismartCommandBuilder
        message_str = self._command_builder._build_message(prefix, payload)
        
        try:
            logger.debug(f"SENT CMD: {prefix.name} ({prefix.value}) | Payload: {json.dumps(payload) if payload else '{}'}")
            await self._websocket.send(message_str)
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
        # Port is part of the template, but the JS used cs.port (443) and just updated the IP.
        # The server message for redirect ("0039") was: {"ip":"...", "port":"..."}
        # Let's assume the new_port from server is the one to use for the path,
        # but the actual connection port might still be 443 if it's WSS.
        # The JS was: "wss://" + e.ip + ":" + cs.port + "/homismartmain/websocket"
        # This implies the port in the redirect_data might be for a different purpose or cs.port (443) is always used.
        # Let's assume the redirect_data's port is for the path, and connection port remains 443 for wss.
        # For now, we'll just update the subdomain/IP part of the URL if the port is standard.
        # If the new_port is different from 443, the URL structure might change.
        # The simplest interpretation is that 'new_ip' replaces the subdomain part.
        
        # Let's assume the `new_ip` is the new host/subdomain part.
        # If the server sends a full new hostname in `new_ip`, that's fine.
        # If it only sends an IP, we might need to adjust.
        # The JS `cs.ct("wss://" + e.ip + ":" + cs.port + "/homismartmain/websocket")`
        # suggests `e.ip` is the new host and `cs.port` (443) is still used for the WSS connection.
        # The `port` in the redirect message might be informational or for a different protocol.
        
        self._ws_url = f"wss://{new_ip}:{WEBSOCKET_URL_TEMPLATE.split(':')[2].split('/')[0]}/homismartmain/websocket"
        # This takes the port from the template (443)
        
        logger.info(f"Updated WebSocket URL for redirection: {self._ws_url}")

        if self._websocket and self._is_connected:
            logger.info("Closing current connection to redirect...")
            # Don't set _keep_running to False, as connect() loop will handle reconnect.
            await self._websocket.close(code=1000, reason="Client redirecting") 
            # The connect() loop's finally block will set _is_connected = False
            # and then it will retry connecting to the new _ws_url.
        else:
            # If not connected, the next connection attempt in connect() will use the new URL.
            logger.info("Not currently connected, next connection attempt will use the new URL.")


    async def disconnect(self) -> None:
        """
        Disconnects from the WebSocket server and stops reconnection attempts.
        """
        logger.info("Disconnect requested. Stopping client...")
        self._keep_running = False
        
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        
        if self._websocket and self._is_connected:
            try:
                await self._websocket.close(code=1000, reason="Client initiated disconnect")
            except WebSocketException as e:
                logger.warning(f"Exception during explicit disconnect: {e}")
        
        if self._receive_task and not self._receive_task.done():
            # This task will exit when the websocket closes or _keep_running is false
            logger.debug("Receive task should self-terminate.")

        # Ensure flags are set correctly
        self._is_connected = False
        self._is_logged_in = False
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

