"""
homismart_client/devices/hub.py

Defines the HomismartHub class, representing a Homismart main unit or hub.
Hubs are typically devices with IDs starting with "00".
"""
import logging
from typing import TYPE_CHECKING, Any, Dict

# Import the base device.
# In a package structure, this would be: from .base_device import HomismartDevice
# For standalone development or if base_device.py is in PYTHONPATH:
try:
    from .base_device import HomismartDevice
except ImportError:
    # Fallback for scenarios where the relative import might not work immediately
    # (e.g., running this file directly before full package setup)
    from base_device import HomismartDevice


if TYPE_CHECKING:
    from ..session import HomismartSession

logger = logging.getLogger(__name__)

class HomismartHub(HomismartDevice):
    """
    Represents a Homismart main unit or hub.
    These devices typically have an ID starting with "00".
    """

    def __init__(self, session: 'HomismartSession', initial_data: Dict[str, Any]):
        """
        Initializes a HomismartHub.

        Args:
            session: The HomismartSession instance managing this hub.
            initial_data: The initial dictionary of data for this hub
                          as received from the server.
        """
        super().__init__(session, initial_data)
        if not self.id.startswith("00"):
            logger.warning(
                f"HomismartHub initialized with ID '{self.id}' which does not start with '00'. "
                "This might not be a typical hub device."
            )
        logger.debug(f"HomismartHub initialized: ID='{self.id}', Name='{self.name}'")

    # Hub-specific properties or methods can be added here if needed.
    # For example, if hubs have unique attributes not covered by HomismartDevice:
    # @property
    # def mac_address(self) -> Optional[str]:
    #     """Returns the MAC address of the hub, if available in raw_data."""
    #     # This assumes 'macAddr' or similar key might exist in the raw_data for hubs
    #     return self._raw_data.get("macAddr")

    # As observed in MainMacModel.js, hubs can have their names changed using
    # SocketFunctions.modifyDevice, which sends a "0016" command.
    # The set_name method is inherited from HomismartDevice and already handles this.

    # Other hub-specific actions like "reset" or "replace" (frmu, fremu from SocketFunctions)
    # would require new methods here and corresponding command builders if they are
    # to be exposed through the Hub object. For now, we'll keep it simple.

    def __repr__(self) -> str:
        return (f"<HomismartHub(id='{self.id}', "
                f"name='{self.name}', type_code='{self.device_type_code}')>")

if __name__ == '__main__':
    # This example is conceptual as it requires a mock session and client.
    # It's for demonstrating the class structure.
    class MockHomismartSession:
        def _get_device_type_enum_from_code(self, code): return code # Simplified
        def _notify_device_update(self, device): pass
        async def _send_command_for_device(self, device_id, command_type, command_payload):
            print(f"MockSession: Sending command for {device_id}: {command_type} with {command_payload}")
            # Simulate a state change if it's a known command
            if command_type == "modify_device" and "name" in command_payload:
                # In a real scenario, the device's update_state would be called
                # by the session upon receiving a confirmation message (e.g., "0009")
                print(f"MockSession: Device {device_id} name would be updated to {command_payload['name']}")
            return {"result": True} # Simulate a successful command dispatch

    print("Demonstrating HomismartHub:")

    mock_session_instance = MockHomismartSession()

    hub_data_from_server = {
        "id": "00123456789ABC",
        "name": "Main Hub",
        "type": 0, # Hubs might have a generic type or a specific one
        "onLine": True,
        "macAddr": "00:1A:2B:3C:4D:5E", # Example custom property
        "version": "1.2.3"
        # ... other relevant fields
    }

    my_hub = HomismartHub(session=mock_session_instance, initial_data=hub_data_from_server)

    print(my_hub)
    print(f"  Raw data: {my_hub.raw}")
    print(f"  Is online: {my_hub.is_online}")
    # print(f"  MAC Address (custom property example): {my_hub.mac_address}")

    # Example of using an inherited method:
    # asyncio.run(my_hub.set_name("Living Room Hub"))
    # This would call _execute_modify_command -> _session._send_command_for_device
    # For direct testing without asyncio loop:
    # my_hub._execute_modify_command(name="Living Room Hub") # This is not async in the mock

    print("\nSimulating an update from server:")
    hub_update_data = {
        "id": "00123456789ABC", # ID must match
        "name": "Living Room Hub Central",
        "onLine": False,
        "new_hub_prop": "some_value"
    }
    my_hub.update_state(hub_update_data)
    print(my_hub)
    print(f"  Updated raw data: {my_hub.raw}")

