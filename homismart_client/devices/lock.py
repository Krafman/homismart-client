"""
homismart_client/devices/lock.py

Defines the LockDevice class, representing smart door locks.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Import the base device.
# In a package structure, this would be: from .base_device import HomismartDevice
from .base_device import HomismartDevice

if TYPE_CHECKING:
    from ..session import HomismartSession
    # from ..enums import RequestPrefix # Will be used by the session

logger = logging.getLogger(__name__)

LOCK_STATE_UNLOCKED = "1"
LOCK_STATE_LOCKED = "2"

class LockDevice(HomismartDevice):
    """
    Represents a smart door lock device.
    Inherits from HomismartDevice.
    Locking/unlocking is typically done via the "0016" (MODIFY_DEVICE) command,
    by updating the 'lock' property.
    """

    def __init__(self, session: 'HomismartSession', initial_data: Dict[str, Any]):
        """
        Initializes a LockDevice.

        Args:
            session: The HomismartSession instance managing this device.
            initial_data: The initial dictionary of data for this device.
        """
        super().__init__(session, initial_data)
        logger.debug(f"LockDevice initialized: ID='{self.id}', Name='{self.name}'")

    @property
    def is_locked(self) -> Optional[bool]:
        """
        Returns True if the lock is currently locked, False if unlocked.
        Returns None if the lock state is unknown or not applicable.
        Based on the 'lock' field in raw_data ("2" for locked, "1" for unlocked).
        """
        lock_status = self._raw_data.get("lock")
        if lock_status == LOCK_STATE_LOCKED:
            return True
        if lock_status == LOCK_STATE_UNLOCKED:
            return False
        logger.warning(f"Device {self.id}: Unknown lock status '{lock_status}'.")
        return None # Or raise an error if status is unexpected

    async def lock_device(self) -> None:
        """
        Locks the device.
        This uses the "0016" MODIFY_DEVICE command, setting 'lock' to "2".
        Always sent, even if the cached state already says locked.
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to lock.")
        # The _execute_modify_command in HomismartDevice constructs the payload
        # with current name and iconId if not provided.
        await self._execute_modify_command(lock_status=LOCK_STATE_LOCKED)

    async def unlock_device(self) -> None:
        """
        Unlocks the device.
        This uses the "0016" MODIFY_DEVICE command, setting 'lock' to "1".
        Always sent, even if the cached state already says unlocked.
        """
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to unlock.")
        await self._execute_modify_command(lock_status=LOCK_STATE_UNLOCKED)

    # Door locks might have an 'operationTime' property, as seen in TableModel.js
    # This was related to `saveDoorDuration` and used `powerDevice` which sent a "0006" command.
    # If setting duration is a separate "0006" command, a method could be added here.
    # However, `SocketFunctions.maxWorkTime` used "0156" (dto) for this.

    # async def set_operation_time(self, duration_seconds: int) -> None:
    #     """
    #     Sets the operation time (e.g., auto-lock duration) for the door lock.
    #     This likely uses the "0156" (SET_DEVICE_OPERATION_TIME) command.
    #
    #     Args:
    #         duration_seconds: The desired operation time in seconds.
    #     """
    #     logger.info(f"Device {self.id} ('{self.name}'): Attempting to set operation time to {duration_seconds}s.")
    #     # The exact payload structure for "0156" needs to be confirmed from SocketFunctions.maxWorkTime(e)
    #     # Assuming 'e' is a dict like {"id": self.id, "operationTime": duration_seconds}
    #     payload = {
    #         "id": self.id, # Or "devid" or "deviceSN" - needs confirmation
    #         "operationTime": duration_seconds
    #     }
    #     await self._session._send_command_for_device(
    #         device_id=self.id,
    #         command_type="set_device_operation_time", # Session maps to RequestPrefix.SET_DEVICE_OPERATION_TIME
    #         command_payload=payload
    #     )

    def __repr__(self) -> str:
        locked_status_str = "Unknown"
        if self.is_locked is True:
            locked_status_str = "Locked"
        elif self.is_locked is False:
            locked_status_str = "Unlocked"
            
        return (f"<LockDevice(id='{self.id}', name='{self.name}', "
                f"type_code='{self.device_type_code}', status='{locked_status_str}')>")
