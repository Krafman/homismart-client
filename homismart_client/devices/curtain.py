"""
homismart_client/devices/curtain.py

Defines the CurtainDevice class, representing devices like curtains and shutters
that can be opened, closed, stopped, or set to a specific level.
"""
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Import the base device class.
# In a package structure, this would simply be:
# from .base_device import HomismartDevice
from .base_device import HomismartDevice

if TYPE_CHECKING:
    from ..session import HomismartSession
    # from ..enums import RequestPrefix # Will be used by the session

logger = logging.getLogger(__name__)

# Constants for curtain states based on observed JS behavior (TableModel.curtainStateFix, SocketFunctions)
# The API seems to use 'curtainState' in the "0006" command.
# A value of '99' was often used for stop or a default/unknown state before setting a new level.
# Levels 0-100 for position.
CURTAIN_STATE_STOP = 99  # Stop signal; sent as a number like every curtainState
CURTAIN_STATE_OPEN_PERCENT = 0 # Typically, 0% means fully open for many systems
CURTAIN_STATE_CLOSED_PERCENT = 100 # Typically, 100% means fully closed

class CurtainDevice(HomismartDevice):
    """
    Represents a curtain or shutter device.
    Inherits directly from :class:`HomismartDevice`.
    Curtain devices are not treated as switchable devices; their
    main control property is ``curtainState`` rather than ``power``.
    """

    def __init__(self, session: 'HomismartSession', initial_data: Dict[str, Any]):
        """
        Initializes a CurtainDevice.

        Args:
            session: The HomismartSession instance managing this device.
            initial_data: The initial dictionary of data for this device.
        """
        super().__init__(session, initial_data)
        logger.debug(f"CurtainDevice initialized: ID='{self.id}', Name='{self.name}'")

    @property
    def current_level(self) -> Optional[int]:
        """
        Returns the current curtain level (position) as a percentage (0-100).
        0 means fully open, 100 fully closed.

        Normalization follows the vendor's TableModel.curtainStateFix logic:
        - Values >= 200 encode a "stopped at" position (e.g. 250 = stopped at 50%).
        - 99 is a special "stop" / unknown state.
        - Values outside 0-100 after normalization are treated as unknown.
        """
        raw_state = self._raw_data.get("curtainState")
        if raw_state is None:
            return None

        try:
            level = int(raw_state)
        except ValueError:
            logger.warning(f"Device {self.id}: Could not parse curtainState '{raw_state}' as integer.")
            return None

        # Vendor encodes "stopped at X%" as 200 + X.
        if level >= 200:
            level = level - 200

        # 99 = stop signal, -1 = unknown, >100 = invalid after normalization.
        if level > 100 or level == 99 or level < 0:
            return None

        return level

    @property
    def open_percentage(self) -> Optional[int]:
        """
        Returns how far the curtain is open, 0 (closed) to 100 (fully open).

        This is the inverse of :attr:`current_level`, which uses the vendor's
        convention (0 = open, 100 = closed). Use this for platforms such as
        Home Assistant, where 0 means closed. The vendor convention was
        confirmed on real shutters: one reporting 80 was physically closed.
        """
        level = self.current_level
        return None if level is None else 100 - level

    async def set_open_percentage(self, open_percentage: int) -> None:
        """
        Moves the curtain so it is *open_percentage* open (0 = closed, 100 = open).
        The inverse convention of :meth:`set_level`.
        """
        if not (0 <= open_percentage <= 100):
            raise ValueError("Open percentage must be between 0 and 100.")
        await self.set_level(100 - open_percentage)

    @property
    def closed_position_calibration(self) -> Optional[int]:
        """
        Returns the calibrated 'closed position' for the curtain, if available.
        This is a value from 1-10 (or 0-10) used by the UI for display logic.
        """
        return cast(Optional[int], self._raw_data.get("closedPosition"))

    async def set_level(self, level_percentage: int) -> None:
        """
        Sets the curtain to a specific level (percentage).
        0 is typically fully open, 100 is fully closed.

        Args:
            level_percentage: The desired level (0-100).
        """
        if not (0 <= level_percentage <= 100):
            logger.error(f"Device {self.id}: Invalid curtain level '{level_percentage}'. Must be 0-100.")
            raise ValueError("Curtain level must be between 0 and 100.")

        logger.info(f"Device {self.id} ('{self.name}'): Attempting to set level to {level_percentage}%.")
        # "0006" with curtainState as a number: some devices ignore it as text.
        await self._execute_control_command({"curtainState": level_percentage})

    async def open_fully(self) -> None:
        """Fully opens the curtain (sets level to 0%)."""
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to fully open.")
        await self.set_level(CURTAIN_STATE_OPEN_PERCENT)

    async def close_fully(self) -> None:
        """Fully closes the curtain (sets level to 100%)."""
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to fully close.")
        await self.set_level(CURTAIN_STATE_CLOSED_PERCENT)

    async def stop(self) -> None:
        """
        Stops the curtain's movement.
        This sends a specific 'curtainState' value, observed as '99' in JS.
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to stop movement.")
        await self._execute_control_command({"curtainState": CURTAIN_STATE_STOP})

    async def set_closed_position_calibration(self, position: int) -> None:
        """
        Sets the calibrated 'closed position' for the curtain.
        This value (typically 1-10) is used by the Homismart system/UI.
        This uses the "0144" SET_CURTAIN_CLOSED_POS command.

        Args:
            position: The calibrated closed position value (e.g., 1-10).
        """
        # The JS `SocketFunctions.setCurtainClosed(thisDevice.id, value)`
        # used `deviceSN` for device ID and `closedPosition` for the value.
        # Assuming position is an int (e.g. 1-10)
        if not (isinstance(position, int) and 0 <= position <= 10): # Or 1-10 if API is strict
             logger.error(f"Device {self.id}: Invalid closed position calibration value '{position}'. Expected 0-10.")
             raise ValueError("Closed position calibration value must be an integer between 0 and 10.")

        logger.info(f"Device {self.id} ('{self.name}'): Attempting to set closed position calibration to {position}.")
        
        payload = {
            "deviceSN": self.id, # SocketFunctions.js used deviceSN
            "closedPosition": position
        }
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="set_curtain_closed_pos", # Session will map to RequestPrefix.SET_CURTAIN_CLOSED_POS
            command_payload=payload
        )

    def __repr__(self) -> str:
        return (f"<CurtainDevice(id='{self.id}', name='{self.name}', "
                f"type_code='{self.device_type_code}', current_level='{self.current_level}')>")
