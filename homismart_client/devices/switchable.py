"""
homismart_client/devices/switchable.py

Defines the SwitchableDevice class, representing devices that can be
turned on or off (e.g., sockets, simple switches).
"""
import logging
import time # For lastOn timestamp
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Import the base device.
# In a package structure, this would be: from .base_device import HomismartDevice
from .base_device import HomismartDevice

if TYPE_CHECKING:
    from ..session import HomismartSession
    # from ..enums import RequestPrefix # Will be used by the session

logger = logging.getLogger(__name__)

class SwitchableDevice(HomismartDevice):
    """
    Represents a device that can be switched on or off, and may have an LED.
    Inherits from HomismartDevice.
    """

    def __init__(self, session: 'HomismartSession', initial_data: Dict[str, Any]):
        """
        Initializes a SwitchableDevice.

        Args:
            session: The HomismartSession instance managing this device.
            initial_data: The initial dictionary of data for this device.
        """
        super().__init__(session, initial_data)
        logger.debug(f"SwitchableDevice initialized: ID='{self.id}', Name='{self.name}'")


    async def turn_on(self) -> None:
        """
        Turns the device ON.
        This uses the "0006" TOGGLE_PROPERTY command.

        The command is always sent, even if the cached state already says ON:
        the cache can be stale (e.g. after a dropped connection), and the
        server's push update is the source of truth.
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to turn ON.")
        # 'lastOn' should be updated when turning on, format from prototype: "YYYY-MM-DD HH:MM:SS"
        current_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        await self._execute_control_command({"power": True, "lastOn": current_time_str})

    async def turn_off(self) -> None:
        """
        Turns the device OFF.
        This uses the "0006" TOGGLE_PROPERTY command.
        Always sent, even if the cached state already says OFF (see turn_on).
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to turn OFF.")
        # 'lastOn' is typically not updated when turning off, but the 'power' field is.
        await self._execute_control_command({"power": False})

    async def toggle(self) -> None:
        """
        Toggles the power state of the device.
        """
        if self.is_on:
            await self.turn_off()
        else:
            await self.turn_on()


    def __repr__(self) -> str:
        return (f"<SwitchableDevice(id='{self.id}', name='{self.name}', "
                f"type_code='{self.device_type_code}', is_on='{self.is_on}')>")
