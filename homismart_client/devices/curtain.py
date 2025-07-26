"""
homismart_client/devices/curtain.py

Defines the CurtainDevice class, representing devices like curtains and shutters
that can be opened, closed, stopped, or set to a specific level.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Import the base device class.
# In a package structure, this would simply be:
# from .base_device import HomismartDevice
try:
    from .base_device import HomismartDevice
except ImportError:
    # Fallback for scenarios where the relative import might not work immediately
    from base_device import HomismartDevice  # type: ignore

if TYPE_CHECKING:
    from ..session import HomismartSession
    # from ..enums import RequestPrefix # Will be used by the session

logger = logging.getLogger(__name__)

# Constants for curtain states based on observed JS behavior (TableModel.curtainStateFix, SocketFunctions)
# The API seems to use 'curtainState' in the "0006" command.
# A value of '99' was often used for stop or a default/unknown state before setting a new level.
# Levels 0-100 for position.
CURTAIN_STATE_STOP = "99" # Observed in JS as a potential stop command or default
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
        0 might mean fully open, 100 fully closed, depending on device interpretation.
        The raw 'curtainState' from the server might need normalization.
        """
        raw_state = self._raw_data.get("curtainState")
        if raw_state is None:
            return None
        
        try:
            level = int(raw_state)
            # Apply normalization similar to TableModel.curtainStateFix
            if level >= 200: # Stop state might be encoded as 200 + level (e.g. 250 for stop at 50%)
                # For simplicity, if it's a "stop" state, we might not have a definitive current level
                # or it might represent the level at which it stopped.
                # The JS `TableModel.curtainStateFix` had:
                # if (level >= 200) { level = level - 200; }
                # if (level > 100 || level === 99 || level === -1) { level = 100; }
                # if (level === 1) { level = 0; }
                # This normalization seems complex and tied to UI display.
                # For now, let's assume the server sends a reasonably direct level or '99' for stop.
                # If '99' is stop, it's not a percentage level.
                if level == 99: # '99' seems to be a special "stop" or "default" state in JS
                    return None # Or a property like `is_stopped` could be True.
                if level >=200 and level <=300: # e.g. 250 means stopped at 50%
                    return level - 200
            
            if level < 0 or level > 100: # Clamp to 0-100 if it's a direct level
                 # If it's '99' (stop), it's not a percentage.
                if level == 99: return None # Or handle as a specific "stopped" state
                # The JS logic for level > 100 was to set it to 100.
                # For now, we'll return None if it's out of expected direct percentage range.
                # A more robust solution might involve an `is_moving` or `is_stopped` property.
                logger.warning(f"Device {self.id}: Raw curtainState '{raw_state}' is outside 0-100 range and not '99'.")
                return None # Or clamp: max(0, min(100, level)) if that's the API behavior.


            return level
        except ValueError:
            logger.warning(f"Device {self.id}: Could not parse curtainState '{raw_state}' as integer.")
            return None

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
        # The "0006" command uses 'curtainState' with the direct percentage value.
        await self._execute_control_command({"curtainState": str(level_percentage)})

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

if __name__ == '__main__':
    # This example is conceptual as it requires a mock session, client, and event loop.
    import asyncio

    class MockHomismartSession:  # Minimal session stub for the example
        def _get_device_type_enum_from_code(self, code): return code
        def _notify_device_update(self, device): pass
        async def _send_command_for_device(self, device_id, command_type, command_payload):
            print(f"MockSession: Sending command for {device_id}: {command_type} with {command_payload}")
            # Simulate a state change for the device if it's a known command
            if command_type == "toggle_property" and "curtainState" in command_payload:
                print(f"MockSession: Device {device_id} curtain state would be updated to {command_payload.get('curtainState')}")
            elif command_type == "set_curtain_closed_pos":
                 print(f"MockSession: Device {device_id} closed position calibration would be set to {command_payload.get('closedPosition')}")
            return {"result": True}

    print("Demonstrating CurtainDevice:")

    mock_session_instance = MockHomismartSession()

    curtain_data = {
        "id": "05CURTAINDEV01", "name": "Bedroom Curtain", "type": 5, # CURTAIN type
        "onLine": True, "power": True, # Curtains might also have a 'power' field
        "curtainState": "50", # Currently at 50%
        "closedPosition": 8, # Example calibration
        "updateTime": int(time.time() * 1000)
    }

    my_curtain = CurtainDevice(session=mock_session_instance, initial_data=curtain_data)

    print(my_curtain)
    print(f"  Current Level: {my_curtain.current_level}%")
    print(f"  Is Online: {my_curtain.is_online}")
    print(f"  Calibrated Closed Position: {my_curtain.closed_position_calibration}")

    async def main_test_curtain():
        print("\n--- Testing Curtain ---")
        await my_curtain.set_level(75)
        await my_curtain.open_fully()
        await my_curtain.close_fully()
        await my_curtain.stop()
        await my_curtain.set_closed_position_calibration(7)

    if hasattr(asyncio, 'run'):
        asyncio.run(main_test_curtain())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_test_curtain())

    print("\nSimulating server update for curtain:")
    curtain_update_from_server = {"id": my_curtain.id, "curtainState": "20"} # 20%
    my_curtain.update_state(curtain_update_from_server)
    print(my_curtain)
    print(f"  Current Level after update: {my_curtain.current_level}%")

    curtain_update_stopped = {"id": my_curtain.id, "curtainState": "99"} # Stopped
    my_curtain.update_state(curtain_update_stopped)
    print(my_curtain)
    print(f"  Current Level after stop update: {my_curtain.current_level}% (None indicates stopped or non-percentage state)")

