"""
homismart_client/devices/lock.py

Defines the LockDevice class, representing smart door locks.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

# Import the base device.
# In a package structure, this would be: from .base_device import HomismartDevice
try:
    from .base_device import HomismartDevice
except ImportError:
    # Fallback for scenarios where the relative import might not work immediately
    from base_device import HomismartDevice # Assumes base_device.py is in the same path

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
        """
        current_lock_state = self.is_locked
        if current_lock_state is True:
            logger.info(f"Device {self.id} ('{self.name}') is already locked.")
            return
        
        logger.info(f"Device {self.id} ('{self.name}'): Attempting to lock.")
        # The _execute_modify_command in HomismartDevice constructs the payload
        # with current name and iconId if not provided.
        await self._execute_modify_command(lock_status=LOCK_STATE_LOCKED)

    async def unlock_device(self) -> None:
        """
        Unlocks the device.
        This uses the "0016" MODIFY_DEVICE command, setting 'lock' to "1".
        """
        current_lock_state = self.is_locked
        if current_lock_state is False:
            logger.info(f"Device {self.id} ('{self.name}') is already unlocked.")
            return
        if current_lock_state is None and self._raw_data.get("lock"):
             logger.warning(f"Device {self.id} ('{self.name}'): Attempting to unlock, but current lock state is ambiguous ('{self._raw_data.get('lock')}'). Proceeding.")
        elif current_lock_state is None:
             logger.warning(f"Device {self.id} ('{self.name}'): Attempting to unlock, but current lock state is unknown. Proceeding.")


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

if __name__ == '__main__':
    # This example is conceptual as it requires a mock session, client, and event loop.
    import asyncio
    import time

    class MockHomismartSession: # Copied for standalone testing
        def _get_device_type_enum_from_code(self, code): return code
        def _notify_device_update(self, device): pass
        async def _send_command_for_device(self, device_id, command_type, command_payload):
            print(f"MockSession: Sending command for {device_id}: {command_type} with {command_payload}")
            # Simulate a state change for the device if it's a known command
            if command_type == "modify_device" and "lock" in command_payload:
                print(f"MockSession: Device {device_id} lock state would be updated to {command_payload.get('lock')}")
            return {"result": True}

    print("Demonstrating LockDevice:")

    mock_session_instance = MockHomismartSession()

    lock_data_locked = {
        "id": "09DOORLOCK001", "name": "Front Door", "type": 9, # DOOR_LOCK type
        "onLine": True, "lock": LOCK_STATE_LOCKED, "iconId": "1",
        "updateTime": int(time.time() * 1000)
        # ... other relevant fields
    }
    lock_data_unlocked = {
        "id": "09DOORLOCK002", "name": "Back Door", "type": 9,
        "onLine": True, "lock": LOCK_STATE_UNLOCKED, "iconId": "1",
        "updateTime": int(time.time() * 1000)
    }

    front_door = LockDevice(session=mock_session_instance, initial_data=lock_data_locked)
    back_door = LockDevice(session=mock_session_instance, initial_data=lock_data_unlocked)

    print(front_door)
    print(f"  Front Door is Locked: {front_door.is_locked}")

    print(back_door)
    print(f"  Back Door is Locked: {back_door.is_locked}")

    async def main_test_lock():
        print("\n--- Testing Front Door (currently Locked) ---")
        await front_door.unlock_device() # Expected: sends lock: "1" via "0016"
        # In a real scenario, front_door.is_locked would update after server confirmation ("0009")
        # front_door.update_state({"id": front_door.id, "lock": LOCK_STATE_UNLOCKED}) # Simulate update
        # print(f"  Front Door is now Locked: {front_door.is_locked}")

        print("\n--- Testing Back Door (currently Unlocked) ---")
        await back_door.lock_device()  # Expected: sends lock: "2" via "0016"
        
        # Example of trying to lock an already locked door (should log and return)
        # front_door.update_state({"id": front_door.id, "lock": LOCK_STATE_LOCKED}) # Simulate it's locked again
        # await front_door.lock_device()


    if hasattr(asyncio, 'run'):
        asyncio.run(main_test_lock())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_test_lock())

    print("\nSimulating server update for front door:")
    lock_update_from_server = {"id": front_door.id, "lock": LOCK_STATE_UNLOCKED}
    front_door.update_state(lock_update_from_server)
    print(front_door)
    print(f"  Front Door is Locked after update: {front_door.is_locked}")
