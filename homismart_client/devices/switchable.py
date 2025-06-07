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
try:
    from .base_device import HomismartDevice
except ImportError:
    from base_device import HomismartDevice # Fallback for standalone/test scenarios

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

    @property
    def is_on(self) -> bool:
        """
        Returns True if the device is currently powered on, False otherwise.
        Based on the 'power' field in raw_data.
        """
        return bool(self._raw_data.get("power", False))

    @property
    def led_state(self) -> Optional[int]:
        """
        Returns the current LED state/percentage of the device, if available.
        Based on the 'led' field in raw_data.
        """
        return cast(Optional[int], self._raw_data.get("led"))

    async def turn_on(self) -> None:
        """
        Turns the device ON.
        This uses the "0006" TOGGLE_PROPERTY command.
        """
        if self.is_on:
            logger.info(f"Device {self.id} ('{self.name}') is already ON.")
            return

        logger.info(f"Device {self.id} ('{self.name}'): Attempting to turn ON.")
        # 'lastOn' should be updated when turning on, format from prototype: "YYYY-MM-DD HH:MM:SS"
        current_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        await self._execute_control_command({"power": True, "lastOn": current_time_str})

    async def turn_off(self) -> None:
        """
        Turns the device OFF.
        This uses the "0006" TOGGLE_PROPERTY command.
        """
        if not self.is_on:
            logger.info(f"Device {self.id} ('{self.name}') is already OFF.")
            return

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

    async def set_led_state(self, led_percentage: int) -> None:
        """
        Sets the LED indicator state/percentage for the device.
        This uses the "0030" MODIFY_LED command.

        Args:
            led_percentage: The desired LED state (e.g., 0-100).
                            The exact meaning (brightness, on/off) might vary.
        """
        if not (0 <= led_percentage <= 100):
            logger.error(f"Device {self.id}: Invalid LED percentage '{led_percentage}'. Must be 0-100.")
            raise ValueError("LED percentage must be between 0 and 100.")

        logger.info(f"Device {self.id} ('{self.name}'): Attempting to set LED state to {led_percentage}%.")
        
        # Payload for "0030" (MODIFY_LED) is {"devid": self.id, "ledDevice": led_percentage}
        # as seen in SocketFunctions.modifyLed
        led_payload = {
            "devid": self.id,
            "ledDevice": led_percentage
        }
        await self._session._send_command_for_device(
            device_id=self.id,
            command_type="modify_led", # Session will map this to RequestPrefix.MODIFY_LED
            command_payload=led_payload
        )

    def __repr__(self) -> str:
        return (f"<SwitchableDevice(id='{self.id}', name='{self.name}', "
                f"type_code='{self.device_type_code}', is_on='{self.is_on}')>")


if __name__ == '__main__':
    # This example is conceptual as it requires a mock session, client, and event loop.
    # It's for demonstrating the class structure.
    import asyncio

    class MockHomismartSession:
        def _get_device_type_enum_from_code(self, code): return code # Simplified
        def _notify_device_update(self, device): pass
        async def _send_command_for_device(self, device_id, command_type, command_payload):
            print(f"MockSession: Sending command for {device_id}: {command_type} with {command_payload}")
            # Simulate a state change for the device if it's a known command
            # In a real scenario, the device's update_state would be called
            # by the session upon receiving a confirmation message (e.g., "0009")
            if command_type == "toggle_property":
                print(f"MockSession: Device {device_id} power state would be updated to {command_payload.get('power')}")
            elif command_type == "modify_led":
                print(f"MockSession: Device {device_id} LED state would be updated to {command_payload.get('ledDevice')}")
            return {"result": True} # Simulate a successful command dispatch

    print("Demonstrating SwitchableDevice:")

    mock_session_instance = MockHomismartSession()

    switch_data_on = {
        "id": "012345SWITCH01", "name": "Living Room Lamp", "type": 1, # SOCKET type
        "onLine": True, "power": True, "led": 100, "updateTime": int(time.time() * 1000)
        # ... other relevant fields from a real device object
    }
    switch_data_off = {
        "id": "012345SWITCH02", "name": "Fan Socket", "type": 1,
        "onLine": True, "power": False, "led": 0, "updateTime": int(time.time() * 1000)
    }

    lamp_switch = SwitchableDevice(session=mock_session_instance, initial_data=switch_data_on)
    fan_socket = SwitchableDevice(session=mock_session_instance, initial_data=switch_data_off)

    print(lamp_switch)
    print(f"  Lamp is ON: {lamp_switch.is_on}")
    print(f"  Lamp LED state: {lamp_switch.led_state}")

    print(fan_socket)
    print(f"  Fan is ON: {fan_socket.is_on}")

    async def main_test():
        print("\n--- Testing Lamp (currently ON) ---")
        await lamp_switch.turn_off() # Expected: sends power: False
        # In a real scenario, lamp_switch.is_on would update after server confirmation ("0009")
        # For this mock, we'd manually call update_state or assume it happened.
        # lamp_switch.update_state({"id": lamp_switch.id, "power": False}) # Simulate update
        # print(f"  Lamp is now ON: {lamp_switch.is_on}")

        await lamp_switch.set_led_state(50)

        print("\n--- Testing Fan (currently OFF) ---")
        await fan_socket.turn_on()  # Expected: sends power: True
        await fan_socket.toggle()   # Expected: sends power: False (since it would be "on" after previous command)

    if hasattr(asyncio, 'run'): # Python 3.7+
        asyncio.run(main_test())
    else: # Older Python versions might need explicit loop management for testing
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_test())

    print("\nSimulating server update for lamp:")
    lamp_update_from_server = {"id": lamp_switch.id, "power": False, "led": 10}
    lamp_switch.update_state(lamp_update_from_server)
    print(lamp_switch)
    print(f"  Lamp is ON after update: {lamp_switch.is_on}")
    print(f"  Lamp LED state after update: {lamp_switch.led_state}")

