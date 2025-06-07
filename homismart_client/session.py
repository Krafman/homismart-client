"""
homismart_client/session.py

Defines the HomismartSession class, which manages the active, authenticated
session, holds device states, and dispatches incoming server messages.
"""
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

# Attempt to import dependent modules.
try:
    from .commands import HomismartCommandBuilder
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
        DeviceNotFoundError,
        HomismartError,
        ParameterError,
    )
except ImportError:
    # Fallbacks for standalone development/testing.
    from commands import HomismartCommandBuilder  # type: ignore
    from devices import (  # type: ignore
        CurtainDevice,
        HomismartDevice,
        HomismartHub,
        LockDevice,
        SwitchableDevice,
    )
    from enums import DeviceType, ErrorCode, ReceivePrefix, RequestPrefix  # type: ignore
    from exceptions import (  # type: ignore
        AuthenticationError,
        CommandError,
        DeviceNotFoundError,
        HomismartError,
        ParameterError,
    )


if TYPE_CHECKING:
    # This import is only for type hinting and avoids circular dependencies
    from .client import HomismartClient

logger = logging.getLogger(__name__)

# Type alias for event listener callbacks
EventListener = Callable[[Any], None]  # Argument could be device object, error data, etc.


class HomismartSession:
    """
    Manages the active, authenticated session with the Homismart server.
    It holds device states, processes incoming messages, and provides an
    interface for device interactions.
    """

    def __init__(self, client: "HomismartClient"):
        """
        Initializes the HomismartSession.

        Args:
            client: The HomismartClient instance that owns this session.
        """
        self._client: "HomismartClient" = client
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
            "session_error": [],  # For "9999" errors or other session-level issues
        }
        self._message_handlers: Dict[
            str, Callable[[Dict[str, Any]], None]
        ] = self._initialize_message_handlers()

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
        }

    def register_event_listener(self, event_name: str, callback: EventListener) -> None:
        """Registers a callback for a specific event."""
        # *** DEFINITIVE FIX: Add a guard clause to prevent non-callable listeners from being added. ***
        if not callable(callback):
            logger.error(
                "Attempted to register a non-callable listener for event '%s': %s",
                event_name,
                callback
            )
            return

        if event_name in self._event_listeners:
            self._event_listeners[event_name].append(callback)
            logger.debug(
                "Registered listener for event '%s': %s", event_name, callback
            )
        else:
            logger.warning("Attempted to register listener for unknown event: '%s'", event_name)

    def unregister_event_listener(
        self, event_name: str, callback: EventListener
    ) -> None:
        """Unregisters a specific callback for an event."""
        if (
            event_name in self._event_listeners
            and callback in self._event_listeners[event_name]
        ):
            self._event_listeners[event_name].remove(callback)
            logger.debug(
                "Unregistered listener for event '%s': %s", event_name, callback
            )
        else:
            logger.warning(
                "Attempted to unregister non-existent listener for event '%s': %s",
                event_name,
                callback,
            )

    def _emit_event(self, event_name: str, *args: Any) -> None:
        """Emits an event, calling all registered listeners."""
        if event_name in self._event_listeners:
            logger.debug("Emitting event '%s' with args: %s", event_name, args)
            for callback in list(self._event_listeners[event_name]):
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(
                        "Error in event listener for '%s' (%s): %s",
                        event_name,
                        callback,
                        e,
                        exc_info=True,
                    )

    def dispatch_message(self, prefix_str: str, data: Dict[str, Any]) -> None:
        """
        Dispatches incoming messages from the client to appropriate handlers
        based on the message prefix.
        """
        logger.debug("Dispatching message: Prefix='%s', Data='%s'", prefix_str, data)
        handler = self._message_handlers.get(prefix_str)
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error(
                    "Error processing message (Prefix: %s, Data: %s): %s",
                    prefix_str,
                    data,
                    e,
                    exc_info=True,
                )
                self._emit_event(
                    "session_error",
                    {"type": "message_handling_error", "prefix": prefix_str, "exception": e},
                )
        else:
            logger.warning("No handler found for message prefix: '%s'. Data: %s", prefix_str, data)

    def _handle_login_response(self, data: Dict[str, Any]) -> None:
        """Handles the "0003" login response."""
        logger.info("Handling login response: %s", data)
        if data.get("result") is True:
            self._client._is_logged_in = True
            username = self._client._username
            logger.info("Login successful for user: %s", username)
            self._emit_event("session_authenticated", username)
            self._client._schedule_task(self._client._request_device_list())
            if data.get("shouldConfirmTerms") == 1 and hasattr(
                self._client, "_accept_terms_and_conditions"
            ):
                logger.info("Terms and conditions need to be accepted.")
                self._client._schedule_task(self._client._accept_terms_and_conditions())
        else:
            self._client._is_logged_in = False
            error_msg = f"Authentication failed. Server response: {data}"
            logger.error(error_msg)
            auth_exception = AuthenticationError(error_msg)
            self._emit_event(
                "session_error",
                {"type": "authentication_failed", "data": data, "exception": auth_exception},
            )

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
            return HomismartDevice

        try:
            dt_enum = DeviceType(type_code)
            if dt_enum in [DeviceType.CURTAIN, DeviceType.SHUTTER]:
                return CurtainDevice
            elif dt_enum == DeviceType.DOOR_LOCK:
                return LockDevice
            elif dt_enum in [
                DeviceType.SOCKET,
                DeviceType.SWITCH,
                DeviceType.SWITCH_MULTI_GANG_A,
                DeviceType.DOUBLE_SWITCH_OR_SOCKET,
                DeviceType.SOCKET_ALT,
            ]:
                return SwitchableDevice
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
            if not isinstance(device, DeviceClass):
                logger.warning(f"Device {device_id} type changed. Recreating with new class {DeviceClass.__name__}.")
                device = DeviceClass(session=self, initial_data=device_data)
                self._devices[device_id] = device
                is_new = True
            else:
                device.update_state(device_data)
        else:
            device = DeviceClass(session=self, initial_data=device_data)
            self._devices[device_id] = device
            is_new = True
        
        if is_new:
            logger.info(f"New device added/re-instantiated: {device}")
            self._emit_event("new_device_added", device)

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

    def _handle_delete_device_response(self, data: Dict[str, Any]) -> None:
        """Handles "0015" Delete Device response."""
        logger.info(f"Delete device response: {data}")
        if data.get("result") is True and "status" in data and isinstance(data["status"], dict):
            device_id_data = data["status"]
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
        
        exception_to_raise: HomismartError
        if error_code_enum in [ErrorCode.PARAMETER_ERROR]:
            exception_to_raise = ParameterError(
                message=f"Server parameter error: {error_info}",
                error_code=error_code_val,
                server_info=error_info,
            )
        else:
            exception_to_raise = CommandError(
                message=f"Server command error: {error_info}",
                error_code=error_code_val,
                server_info=error_info,
            )
        
        self._emit_event(
            "session_error",
            {"type": "server_command_error", "data": error_data, "exception": exception_to_raise},
        )

    def _handle_redirect_info(self, redirect_data: Dict[str, Any]) -> None:
        """Handles "0039" server redirect instruction."""
        new_ip = redirect_data.get("ip")
        new_port_str = redirect_data.get("port")
        logger.info(f"Server redirection requested: IP='{new_ip}', Port='{new_port_str}'")

        if new_ip and new_port_str:
            try:
                new_port = int(new_port_str)
                self._client._schedule_task(self._client._handle_redirect(new_ip, new_port))
            except ValueError:
                logger.error(f"Invalid port in redirect data: {new_port_str}")
        else:
            logger.error(f"Incomplete redirect data received: {redirect_data}")

    async def _send_command_for_device(
        self,
        device_id: str,
        command_type: str,
        command_payload: Dict[str, Any],
    ) -> None:
        """Generic method for device objects to request sending a command."""
        logger.debug(
            f"Session: Received request to send command '{command_type}' for device '{device_id}' with payload: {command_payload}"
        )
        
        try:
            # Dynamically get the prefix from the enum based on the command_type string.
            prefix = RequestPrefix[command_type.upper()]
            await self._client.send_command_raw(prefix, command_payload)
        except KeyError:
            logger.error(f"Session: Unknown command_type '{command_type}' requested for device '{device_id}'.")
            raise ValueError(f"Unknown command_type: {command_type}")

    def _get_device_type_enum_from_code(
        self, type_code: Optional[int]
    ) -> Optional[DeviceType]:
        """Converts a numeric device type code to a DeviceType enum member."""
        if type_code is None:
            return None
        try:
            return DeviceType(type_code)
        except ValueError:
            logger.warning(f"Unknown device type code encountered: {type_code}")
            return None

    def _notify_device_update(self, device: HomismartDevice) -> None:
        """Called by device objects when their state is updated."""
        if isinstance(device, HomismartHub):
            self._emit_event("hub_updated", device)
        else:
            self._emit_event("device_updated", device)

    def get_device_by_id(self, device_id: str) -> Optional[HomismartDevice]:
        """Retrieves a device (non-hub) by its ID."""
        return self._devices.get(device_id)

    def get_hub_by_id(self, hub_id: str) -> Optional[HomismartHub]:
        """Retrieves a hub by its ID."""
        return self._hubs.get(hub_id)

    def get_all_devices(self) -> List[HomismartDevice]:
        """Returns a list of all managed non-hub devices."""
        return list(self._devices.values())

    def get_all_hubs(self) -> List[HomismartHub]:
        """Returns a list of all managed hubs."""
        return list(self._hubs.values())
