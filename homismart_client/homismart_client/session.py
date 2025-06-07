"""
homismart_client/session.py

Defines the HomismartSession class, which manages the active, authenticated
session, holds device states, and dispatches incoming server messages.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Callable, cast

# Attempt to import dependent modules.
# These imports will work when the package is installed or structured correctly.
try:
    from .enums import ReceivePrefix, DeviceType, ErrorCode, RequestPrefix
    from .exceptions import (
        AuthenticationError, CommandError, DeviceNotFoundError,
        ParameterError, HomismartError
    )
    from .devices.base_device import HomismartDevice
    from .devices.hub import HomismartHub
    from .devices.switchable import SwitchableDevice
    from .devices.curtain import CurtainDevice
    from .devices.lock import LockDevice
except ImportError:
    # Fallbacks for scenarios where this file might be processed before full package setup
    # or in a different environment. Assumes these files are in the same path or PYTHONPATH.
    from enums import ReceivePrefix, DeviceType, ErrorCode, RequestPrefix # type: ignore
    from exceptions import ( # type: ignore
        AuthenticationError, CommandError, DeviceNotFoundError,
        ParameterError, HomismartError
    )
    from devices.base_device import HomismartDevice # type: ignore
    from devices.hub import HomismartHub # type: ignore
    from devices.switchable import SwitchableDevice # type: ignore
    from devices.curtain import CurtainDevice # type: ignore
    from devices.lock import LockDevice # type: ignore


if TYPE_CHECKING:
    # This import is only for type hinting and avoids circular dependencies
    from .client import HomismartClient

logger = logging.getLogger(__name__)

# Type alias for event listener callbacks
EventListener = Callable[[Any], None] # Argument could be device object, error data, etc.

class HomismartSession:
    """
    Manages the active, authenticated session with the Homismart server.
    It holds device states, processes incoming messages, and provides an
    interface for device interactions.
    """

    def __init__(self, client: 'HomismartClient'):
        """
        Initializes the HomismartSession.

        Args:
            client: The HomismartClient instance that owns this session.
        """
        self._client: 'HomismartClient' = client
        self._devices: Dict[str, HomismartDevice] = {}
        self._hubs: Dict[str, HomismartHub] = {}

        # Basic event listener registry
        self._event_listeners: Dict[str, List[EventListener]] = {
            "device_updated": [],
            "new_device_added": [],
            "device_deleted": [],
            "hub_updated": [],
            "new_hub_added": [],
            "hub_deleted": [],
            "session_authenticated": [],
            "session_error": [], # For "9999" errors or other session-level issues
        }
        self._message_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = self._initialize_message_handlers()


    def _initialize_message_handlers(self) -> Dict[str, Callable[[Dict[str, Any]], None]]:
        """Initializes the mapping from ReceivePrefix values to handler methods."""
        return {
            ReceivePrefix.LOGIN_RESPONSE.value: self._handle_login_response,
            ReceivePrefix.DEVICE_LIST.value: self._handle_device_list,
            ReceivePrefix.DEVICE_UPDATE_PUSH.value: self._handle_device_update_push,
            ReceivePrefix.ADD_DEVICE_RESPONSE.value: self._handle_add_device_response,
            ReceivePrefix.DELETE_DEVICE_RESPONSE.value: self._handle_delete_device_response,
            ReceivePrefix.SERVER_ERROR.value: self._handle_server_error,
            ReceivePrefix.SERVER_REDIRECT.value: self._handle_redirect_info,
            # Add handlers for other ReceivePrefixes as functionality is built out
            # e.g., timer lists, scenario lists, etc.
        }

    def register_event_listener(self, event_name: str, callback: EventListener) -> None:
        """Registers a callback for a specific event."""
        if event_name in self._event_listeners:
            self._event_listeners[event_name].append(callback)
            logger.debug(f"Registered listener for event '{event_name}': {callback}")
        else:
            logger.warning(f"Attempted to register listener for unknown event: '{event_name}'")

    def unregister_event_listener(self, event_name: str, callback: EventListener) -> None:
        """Unregisters a specific callback for an event."""
        if event_name in self._event_listeners and callback in self._event_listeners[event_name]:
            self._event_listeners[event_name].remove(callback)
            logger.debug(f"Unregistered listener for event '{event_name}': {callback}")
        else:
            logger.warning(f"Attempted to unregister non-existent listener for event '{event_name}': {callback}")

    def _emit_event(self, event_name: str, *args: Any) -> None:
        """Emits an event, calling all registered listeners."""
        if event_name in self._event_listeners:
            logger.debug(f"Emitting event '{event_name}' with args: {args}")
            for callback in self._event_listeners[event_name]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Error in event listener for '{event_name}' ({callback}): {e}", exc_info=True)

    def dispatch_message(self, prefix_str: str, data: Dict[str, Any]) -> None:
        """
        Dispatches incoming messages from the client to appropriate handlers
        based on the message prefix.

        Args:
            prefix_str: The 4-digit message prefix string.
            data: The parsed JSON payload as a dictionary.
        """
        logger.debug(f"Dispatching message: Prefix='{prefix_str}', Data='{data}'")
        handler = self._message_handlers.get(prefix_str)
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error processing message (Prefix: {prefix_str}, Data: {data}): {e}", exc_info=True)
                self._emit_event("session_error", {"type": "message_handling_error", "prefix": prefix_str, "exception": e})
        else:
            logger.warning(f"No handler found for message prefix: '{prefix_str}'. Data: {data}")

    def _handle_login_response(self, data: Dict[str, Any]) -> None:
        """Handles the "0003" login response."""
        logger.info(f"Handling login response: {data}")
        if data.get("result") is True:
            self._client._is_logged_in = True # Should be managed by client
            logger.info(f"Login successful for user: {data.get('username', 'N/A')}")
            self._emit_event("session_authenticated", data.get('username'))
            # After successful login, client should request device list
            self._client._schedule_task(self._client._request_device_list())
            # Handle terms and conditions if necessary
            if data.get("shouldConfirmTerms") == 1 and hasattr(self._client, '_accept_terms_and_conditions'):
                 logger.info("Terms and conditions need to be accepted.")
                 self._client._schedule_task(self._client._accept_terms_and_conditions())

        else:
            self._client._is_logged_in = False
            error_msg = f"Authentication failed. Server response: {data}"
            logger.error(error_msg)
            # We don't have a specific server error code here, so create a generic auth error
            auth_exception = AuthenticationError(error_msg)
            self._emit_event("session_error", {"type": "authentication_failed", "data": data, "exception": auth_exception})
            # Optionally, raise AuthenticationError if the client should handle it immediately
            # raise auth_exception

    def _handle_device_list(self, device_list_data: List[Dict[str, Any]]) -> None:
        """Handles the "0005" device list response."""
        if not isinstance(device_list_data, list):
            logger.error(f"Expected a list for device data (0005), got: {type(device_list_data)}")
            return

        logger.info(f"Received device list with {len(device_list_data)} total entries.")
        
        current_device_ids = set(self._devices.keys())
        current_hub_ids = set(self._hubs.keys())
        
        processed_device_ids = set()
        processed_hub_ids = set()

        for device_data in device_list_data:
            if not isinstance(device_data, dict) or "id" not in device_data:
                logger.warning(f"Skipping invalid device data entry: {device_data}")
                continue
            
            device_id = device_data["id"]
            if device_id.startswith("00"): # Hub/MAC device
                self._update_or_create_hub(device_data)
                processed_hub_ids.add(device_id)
            else: # Regular device
                self._update_or_create_device(device_data)
                processed_device_ids.add(device_id)
        
        # Identify and remove devices/hubs no longer in the list (if any)
        # This assumes the "0005" list is authoritative.
        ids_to_remove = current_device_ids - processed_device_ids
        for dev_id in ids_to_remove:
            self._remove_device(dev_id, is_hub=False)
            
        hub_ids_to_remove = current_hub_ids - processed_hub_ids
        for hub_id in hub_ids_to_remove:
            self._remove_device(hub_id, is_hub=True)

        logger.info(f"Device list processing complete. Devices: {len(self._devices)}, Hubs: {len(self._hubs)}")

    def _handle_device_update_push(self, device_data: Dict[str, Any]) -> None:
        """Handles the "0009" individual device update push."""
        if not isinstance(device_data, dict) or "id" not in device_data:
            logger.warning(f"Skipping invalid device push update data: {device_data}")
            return
        
        logger.info(f"Received push update for device ID: {device_data['id']}")
        device_id = device_data["id"]
        if device_id.startswith("00"):
            self._update_or_create_hub(device_data)
        else:
            self._update_or_create_device(device_data)

    def _get_device_class_for_type(self, type_code: Optional[int]) -> type:
        """Determines the appropriate device class based on the type code."""
        if type_code is None:
            return HomismartDevice # Default or unknown

        try:
            dt_enum = DeviceType(type_code) # Convert int to DeviceType enum member
            if dt_enum in [DeviceType.CURTAIN, DeviceType.SHUTTER]:
                return CurtainDevice
            elif dt_enum == DeviceType.DOOR_LOCK:
                return LockDevice
            elif dt_enum in [DeviceType.SOCKET, DeviceType.SWITCH,
                             DeviceType.SWITCH_MULTI_GANG_A,
                             DeviceType.DOUBLE_SWITCH_OR_SOCKET, DeviceType.SOCKET_ALT]:
                return SwitchableDevice
            # Add more specific types if needed
        except ValueError:
            logger.warning(f"Unknown device type code '{type_code}'. Using base device class.")
        
        return HomismartDevice


    def _update_or_create_device(self, device_data: Dict[str, Any]) -> None:
        """Updates an existing device or creates a new one."""
        device_id = device_data["id"]
        device_type_code = cast(Optional[int], device_data.get("type"))
        DeviceClass = self._get_device_class_for_type(device_type_code)
        
        is_new = False
        if device_id in self._devices:
            device = self._devices[device_id]
            # Check if class needs to change (e.g. type reported differently)
            if not isinstance(device, DeviceClass):
                logger.warning(f"Device {device_id} type changed. Recreating with new class {DeviceClass.__name__}.")
                device = DeviceClass(session=self, initial_data=device_data)
                self._devices[device_id] = device
                is_new = True # Treat as new due to class change
            else:
                device.update_state(device_data)
        else:
            device = DeviceClass(session=self, initial_data=device_data)
            self._devices[device_id] = device
            is_new = True
        
        if is_new:
            logger.info(f"New device added/re-instantiated: {device}")
            self._emit_event("new_device_added", device)
        # Note: device.update_state already calls _notify_device_update which emits "device_updated"

    def _update_or_create_hub(self, hub_data: Dict[str, Any]) -> None:
        """Updates an existing hub or creates a new one."""
        hub_id = hub_data["id"]
        is_new = False
        if hub_id in self._hubs:
            hub = self._hubs[hub_id]
            hub.update_state(hub_data)
        else:
            hub = HomismartHub(session=self, initial_data=hub_data)
            self._hubs[hub_id] = hub
            is_new = True
        
        if is_new:
            logger.info(f"New hub added: {hub}")
            self._emit_event("new_hub_added", hub)
        # Note: hub.update_state already calls _notify_device_update which emits "hub_updated"

    def _remove_device(self, device_id: str, is_hub: bool) -> None:
        """Removes a device or hub from internal tracking."""
        if is_hub:
            if device_id in self._hubs:
                hub = self._hubs.pop(device_id)
                logger.info(f"Hub removed: {hub}")
                self._emit_event("hub_deleted", hub)
        else:
            if device_id in self._devices:
                device = self._devices.pop(device_id)
                logger.info(f"Device removed: {device}")
                self._emit_event("device_deleted", device)

    def _handle_add_device_response(self, data: Dict[str, Any]) -> None:
        """Handles "0013" Add Device response."""
        logger.info(f"Add device response: {data}")
        if data.get("result") is True and "status" in data and isinstance(data["status"], dict):
            device_data = data["status"]
            if "id" in device_data:
                if device_data["id"].startswith("00"):
                    self._update_or_create_hub(device_data)
                else:
                    self._update_or_create_device(device_data)
            else:
                logger.warning("Add device response 'status' missing 'id'.")
        else:
            logger.error(f"Failed to add device. Server response: {data}")
            # Potentially emit an error event or raise an exception

    def _handle_delete_device_response(self, data: Dict[str, Any]) -> None:
        """Handles "0015" Delete Device response."""
        logger.info(f"Delete device response: {data}")
        if data.get("result") is True and "status" in data and isinstance(data["status"], dict):
            device_id_data = data["status"] # This usually contains just the ID of the deleted device
            device_id = device_id_data.get("id")
            if device_id:
                if device_id in self._devices:
                    self._remove_device(device_id, is_hub=False)
                elif device_id in self._hubs:
                    self._remove_device(device_id, is_hub=True)
                else:
                    logger.warning(f"Delete response for unknown device ID: {device_id}")
            else:
                logger.warning("Delete device response 'status' missing 'id'.")
        else:
            logger.error(f"Failed to delete device. Server response: {data}")

    def _handle_server_error(self, error_data: Dict[str, Any]) -> None:
        """Handles "9999" server error messages."""
        error_code_val = error_data.get("code")
        error_info = error_data.get("info", "Unknown server error.")
        logger.error(f"Server error received: Code={error_code_val}, Info='{error_info}'")

        error_code_enum = None
        if isinstance(error_code_val, int):
            try:
                error_code_enum = ErrorCode(error_code_val)
            except ValueError:
                logger.warning(f"Unknown server error code: {error_code_val}")
        
        # Determine specific exception type if possible
        if error_code_enum in [ErrorCode.PARAMETER_ERROR]: # Add other parameter error codes if any
            exception_to_raise: HomismartError = ParameterError(
                message=f"Server parameter error: {error_info}",
                error_code=error_code_val,
                server_info=error_info
            )
        else:
            exception_to_raise = CommandError(
                message=f"Server command error: {error_info}",
                error_code=error_code_val,
                server_info=error_info
            )
        
        self._emit_event("session_error", {"type": "server_command_error", "data": error_data, "exception": exception_to_raise})
        # Consider if the client should raise this immediately or if listeners handle it.
        # For now, emitting as an event. The client can decide to re-raise.

    def _handle_redirect_info(self, redirect_data: Dict[str, Any]) -> None:
        """Handles "0039" server redirect instruction."""
        new_ip = redirect_data.get("ip")
        new_port_str = redirect_data.get("port") # Port might be string
        logger.info(f"Server redirection requested: IP='{new_ip}', Port='{new_port_str}'")

        if new_ip and new_port_str:
            try:
                new_port = int(new_port_str)
                self._client._schedule_task(self._client._handle_redirect(new_ip, new_port))
            except ValueError:
                logger.error(f"Invalid port in redirect data: {new_port_str}")
        else:
            logger.error(f"Incomplete redirect data received: {redirect_data}")

    # --- Methods called by Device objects to request actions ---
    async def _send_command_for_device(
        self,
        device_id: str,
        command_type: str, # e.g., "toggle_property", "modify_device", "delete_device"
        command_payload: Dict[str, Any]
    ) -> None:
        """
        Generic method for device objects to request sending a command.
        The session will ask the client to build and send the command.
        """
        logger.debug(f"Session: Received request to send command '{command_type}' for device '{device_id}' with payload: {command_payload}")
        
        # Map command_type string to RequestPrefix enum and call client's send method
        # This requires client to have access to HomismartCommandBuilder
        if command_type == "toggle_property":
            prefix = RequestPrefix.TOGGLE_PROPERTY
            # Payload is already the full device dict for "0006"
            await self._client.send_command_raw(prefix, command_payload)
        elif command_type == "modify_device":
            prefix = RequestPrefix.MODIFY_DEVICE
            # Payload is specific for "0016": {devid, name, lock, iconId}
            # Ensure command_payload matches this structure.
            await self._client.send_command_raw(prefix, command_payload)
        elif command_type == "delete_device":
            prefix = RequestPrefix.DELETE_DEVICE
            # Payload is {"devid": device_id}
            await self._client.send_command_raw(prefix, command_payload)
        elif command_type == "set_curtain_closed_pos":
            prefix = RequestPrefix.SET_CURTAIN_CLOSED_POS
            # Payload is {"deviceSN": device_id, "closedPosition": position}
            await self._client.send_command_raw(prefix, command_payload)
        elif command_type == "modify_led":
            prefix = RequestPrefix.MODIFY_LED
            # Payload is {"devid": device_id, "ledDevice": percentage}
            await self._client.send_command_raw(prefix, command_payload)
        else:
            logger.error(f"Session: Unknown command_type '{command_type}' requested for device '{device_id}'.")
            raise ValueError(f"Unknown command_type: {command_type}")

    # --- Utility methods for device classes or internal use ---
    def _get_device_type_enum_from_code(self, type_code: Optional[int]) -> Optional[DeviceType]:
        """Converts a numeric device type code to a DeviceType enum member."""
        if type_code is None:
            return None
        try:
            return DeviceType(type_code)
        except ValueError:
            logger.warning(f"Unknown device type code encountered: {type_code}")
            return DeviceType.UNKNOWN # Or return None

    def _notify_device_update(self, device: HomismartDevice) -> None:
        """Called by device objects when their state is updated."""
        if isinstance(device, HomismartHub):
            self._emit_event("hub_updated", device)
        else:
            self._emit_event("device_updated", device)
            
    # --- Public API for accessing devices ---
    def get_device_by_id(self, device_id: str) -> Optional[HomismartDevice]:
        """Retrieves a device (non-hub) by its ID."""
        device = self._devices.get(device_id)
        if not device:
            logger.debug(f"Device with ID '{device_id}' not found in managed devices.")
        return device

    def get_hub_by_id(self, hub_id: str) -> Optional[HomismartHub]:
        """Retrieves a hub by its ID."""
        hub = self._hubs.get(hub_id)
        if not hub:
            logger.debug(f"Hub with ID '{hub_id}' not found in managed hubs.")
        return hub

    def get_all_devices(self) -> List[HomismartDevice]:
        """Returns a list of all managed non-hub devices."""
        return list(self._devices.values())

    def get_all_hubs(self) -> List[HomismartHub]:
        """Returns a list of all managed hubs."""
        return list(self._hubs.values())

