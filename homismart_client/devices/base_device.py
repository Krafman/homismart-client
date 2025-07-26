"""
homismart_client/devices/base_device.py

Defines the HomismartDevice base class, representing a generic device
in the Homismart ecosystem.
"""
import time
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Enums will be imported by the session/client and resolved there,
# or passed as arguments if needed to avoid circular dependencies at this stage.
# from ..enums import DeviceType, RequestPrefix # For final package structure

if TYPE_CHECKING:
    # This import is only for type hinting and avoids circular dependencies
    # during the initial build-out of the library.
    from ..session import HomismartSession

logger = logging.getLogger(__name__)

class HomismartDevice:
    """
    Base class representing a Homismart device.
    Holds the device's state and provides methods to interact with it.
    """

    def __init__(self, session: 'HomismartSession', initial_data: Dict[str, Any]):
        """
        Initializes a HomismartDevice.

        Args:
            session: The HomismartSession instance managing this device.
            initial_data: The initial dictionary of data for this device
                          as received from the server.
        """
        self._session: 'HomismartSession' = session
        
        if 'id' not in initial_data:
            # Log a warning or raise error if essential data is missing
            logger.error("Device initialized with missing 'id' in initial_data: %s", initial_data)
            raise ValueError("Initial device data must contain an 'id'.")
        
        self.id: str = initial_data['id']
        self._raw_data: Dict[str, Any] = initial_data # Store all initial data

    @property
    def raw(self) -> Dict[str, Any]:
        """
        Returns a copy of the raw dictionary data for the device.
        This allows access to all properties received from the server.
        """
        return self._raw_data.copy()

    @property
    def name(self) -> Optional[str]:
        """Returns the name of the device."""
        return cast(Optional[str], self._raw_data.get("name"))

    @property
    def device_type_code(self) -> Optional[int]:
        """Returns the raw integer device type code (e.g., 1 for SOCKET, 4 for SHUTTER)."""
        return cast(Optional[int], self._raw_data.get("type"))

    @property
    def device_type_enum(self) -> Optional[Any]: # Optional[DeviceType]
        """
        Returns the DeviceType enum member for this device, if resolvable.
        Actual DeviceType enum import will be handled by higher-level modules.
        """
        type_code = self.device_type_code
        if type_code is not None:
            # The session or a utility function can provide the mapping
            # from type_code to the DeviceType enum member.
            # For now, this property indicates the intent.
            # Example: return self._session.get_device_type_enum_for_code(type_code)
            return self._session._get_device_type_enum_from_code(type_code) # Placeholder for session method
        return None

    @property
    def is_online(self) -> bool:
        """Returns True if the device is reported as online, False otherwise."""
        return bool(self._raw_data.get("onLine", False))

    @property
    def is_on(self) -> bool:
        """Returns True if the device is powered on, False otherwise."""
        return bool(self._raw_data.get("power", False))

    @property
    def led_state(self) -> Optional[int]:
        """Returns the LED state/percentage for the device if available."""
        return cast(Optional[int], self._raw_data.get("led"))

    @property
    def shared(self) -> bool:
        """Returns True if the device is a shared device."""
        return bool(self._raw_data.get("shared", False))

    @property
    def permission(self) -> Optional[Any]:
        """
        Returns the permission data for a shared device.
        The exact structure of this data is not fully defined yet.
        """
        return self._raw_data.get("permission")

    @property
    def allowed_time(self) -> Optional[Any]:
        """
        Returns the allowed time data for a shared device.
        The exact structure of this data is not fully defined yet.
        """
        return self._raw_data.get("allowedTime")

    @property
    def has_timers(self) -> bool:
        """
        Returns True if the device has timers configured.
        This flag is typically set by the client based on timer lists.
        """
        return bool(self._raw_data.get("timers", False))
        
    @property
    def pid(self) -> Optional[str]:
        """Returns the PID (Product ID or Parent ID) of the device, if available."""
        return cast(Optional[str], self._raw_data.get("pid"))

    @property
    def version(self) -> Optional[Any]: # Can be int or str
        """Returns the firmware or hardware version of the device, if available."""
        return self._raw_data.get("version")

    @property
    def icon_id(self) -> Optional[str]:
        """Returns the icon ID string of the device, if available."""
        return cast(Optional[str], self._raw_data.get("iconId"))

    def update_state(self, new_data: Dict[str, Any]) -> None:
        """
        Updates the device's state with new data from the server.
        Implements special logic for shared devices to preserve sharing state
        if not explicitly provided in new_data, as observed in MainDeviceModel.js.

        Args:
            new_data: A dictionary containing the new state information.
        """
        logger.debug(f"Device {self.id}: Updating state. Current raw: {self._raw_data}, New data: {new_data}")
        
        # Preserve sharing-related fields if the device was already marked as shared
        # and the new data doesn't explicitly unshare it or provide new sharing info.
        if self._raw_data.get('shared') is True:
            if new_data.get('shared') is None and 'shared' not in new_data: # If new_data doesn't mention 'shared'
                new_data['shared'] = True # Maintain shared status
            
            if new_data.get('shared') is True: # If it's still shared or newly confirmed as shared
                if 'permission' not in new_data and 'permission' in self._raw_data:
                    new_data['permission'] = self._raw_data['permission']
                if 'allowedTime' not in new_data and 'allowedTime' in self._raw_data:
                    new_data['allowedTime'] = self._raw_data['allowedTime']
        
        self._raw_data.update(new_data)
        
        # If 'id' could change (highly unlikely for updates, but good to be aware)
        if 'id' in new_data and self.id != new_data['id']:
            logger.warning(f"Device {self.id}: ID changed to {new_data['id']} during update. This is highly unusual.")
            self.id = new_data['id'] # Update the primary ID attribute
        
        logger.info(f"Device {self.id} ('{self.name}'): State updated.")
        # The session might emit a "device_updated" event here
        self._session._notify_device_update(self)


    async def _execute_control_command(self, updated_properties: Dict[str, Any]) -> None:
        """
        Prepares and requests execution of a "0006" (TOGGLE_PROPERTY) command via the session.
        This command requires sending the full device state dictionary with the
        desired properties updated and 'updateTime' refreshed.

        Args:
            updated_properties: A dictionary of properties to update in the device's state.
                                Example: {"power": True, "lastOn": "timestamp_str"}
        """
        payload = self._raw_data.copy()
        payload.update(updated_properties)
        payload["updateTime"] = int(time.time() * 1000)
        
        logger.debug(f"Device {self.id}: Preparing '0006' (TOGGLE_PROPERTY) command with payload: {payload}")
        # The session will use HomismartCommandBuilder.build_toggle_property_message(payload)
        # and then send it using the client.
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="toggle_property", # Session can map this to RequestPrefix.TOGGLE_PROPERTY
            command_payload=payload
        )

    async def _execute_modify_command(
        self,
        name: Optional[str] = None,
        lock_status: Optional[str] = None,
        icon_id: Optional[str] = None
    ) -> None:
        """
        Prepares and requests execution of a "0016" (MODIFY_DEVICE) command via the session.
        This command uses a specific, smaller payload containing devid, name, lock, and iconId.

        Args:
            name: The new name for the device. If None, current name is used.
            lock_status: The new lock status ("1" or "2"). If None, current lock status is used.
            icon_id: The new icon ID. If None, current icon ID is used.
        """
        # Construct payload always sending current values if new ones are not provided,
        # as "0016" expects devid, name, lock, iconId.
        payload: Dict[str, Any] = {"devid": self.id}
        payload["name"] = name if name is not None else self.name if self.name is not None else ""
        payload["lock"] = lock_status if lock_status is not None else self._raw_data.get("lock", "1")
        payload["iconId"] = icon_id if icon_id is not None else self.icon_id if self.icon_id is not None else "0"

        logger.debug(f"Device {self.id}: Preparing '0016' (MODIFY_DEVICE) command with payload: {payload}")
        # The session will use HomismartCommandBuilder.build_modify_device_message(...)
        # and then send it using the client.
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="modify_device", # Session can map this to RequestPrefix.MODIFY_DEVICE
            command_payload=payload # This payload is specific to "0016"
        )

    async def set_name(self, name: str) -> None:
        """Sets a new name for the device. This uses the "0016" MODIFY_DEVICE command."""
        if not name or not isinstance(name, str):
            logger.error(f"Device {self.id}: Invalid name provided for set_name: '{name}'")
            raise ValueError("Device name must be a non-empty string.")
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to set name to '{name}'.")
        await self._execute_modify_command(name=name)

    async def set_icon(self, icon_id: str) -> None:
        """Sets a new icon ID for the device. This uses the "0016" MODIFY_DEVICE command."""
        # Assuming icon_id is always a string based on JS observations.
        if not isinstance(icon_id, str):
            logger.error(f"Device {self.id}: Invalid icon_id provided for set_icon: '{icon_id}'")
            raise ValueError("Icon ID must be a string.")
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to set icon ID to '{icon_id}'.")
        await self._execute_modify_command(icon_id=icon_id)

    async def set_led_state(self, led_percentage: int) -> None:
        """Sets the LED indicator percentage for the device via the "0030" command."""
        if not (0 <= led_percentage <= 100):
            logger.error(
                f"Device {self.id}: Invalid LED percentage '{led_percentage}'. Must be 0-100."
            )
            raise ValueError("LED percentage must be between 0 and 100.")

        logger.info(
            f"Device {self.id} ('{self.name}'): Attempting to set LED state to {led_percentage}%."
        )

        led_payload = {"devid": self.id, "ledDevice": led_percentage}
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="modify_led",
            command_payload=led_payload,
        )

    async def delete(self) -> None:
        """
        Deletes the device from the account. This uses the "0014" DELETE_DEVICE command.
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to delete.")
        # Payload for "0014" is {"devid": self.id}
        delete_payload = {"devid": self.id}
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="delete_device", # Session can map this to RequestPrefix.DELETE_DEVICE
            command_payload=delete_payload
        )

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__}(id='{self.id}', "
                f"name='{self.name}', type_code='{self.device_type_code}')>")

    def __str__(self) -> str:
        return (f"{self.name or 'Unnamed Device'} (ID: {self.id}, "
                f"Type: {self.device_type_code or 'N/A'}, Online: {self.is_online})")

