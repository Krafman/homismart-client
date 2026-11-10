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
from .base_device import HomismartDevice


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
