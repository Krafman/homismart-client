"""
homismart_client/commands.py

Defines the HomismartCommandBuilder class, responsible for constructing
the correctly formatted message strings (prefix + JSON payload) for all
outgoing commands to the Homismart server.
"""
import json
from typing import Optional, Dict, Any, List

# Attempt to import RequestPrefix. If this script is run directly,
# this might fail, so we handle it for potential direct testing,
# but in package use, it should be available.
try:
    from .enums import RequestPrefix
except ImportError:
    # This is to allow the file to be run standalone for simple tests,
    # assuming enums.py is in the same directory or Python path.
    # In a real package structure, the relative import above should work.
    from enums import RequestPrefix

class HomismartCommandBuilder:
    """
    Constructs command strings for the Homismart WebSocket API.
    Each method returns a string ready to be sent over the WebSocket,
    consisting of a 4-digit prefix followed by a JSON string payload.
    """

    @staticmethod
    def _build_message(prefix: RequestPrefix, payload: Optional[Dict[str, Any]] = None) -> str:
        """
        Helper to construct the final message string.

        Args:
            prefix: The RequestPrefix enum member for the command.
            payload: An optional dictionary to be JSON stringified.
                     If None, an empty JSON object "{}" might be implied by some commands,
                     or no payload part if the command truly expects none (handled by specific methods).

        Returns:
            The fully formatted command string.
        """
        if payload is None:
            # Some commands expect an empty JSON object "{}"
            # Others might expect no JSON part at all.
            # For now, if payload is None, we assume it means no JSON string part,
            # unless a specific builder method adds "{}".
            # Based on SocketFunctions.js, cs.send(prefix, payload_obj)
            # implies if payload_obj is undefined/null, only prefix is sent.
            # If payload_obj is {}, then prefix + "{}" is sent.
            return prefix.value
        return prefix.value + json.dumps(payload)

    @staticmethod
    def build_login_message(username: str, password_hash: str) -> str:
        """
        Builds the login command ("0002").
        Password should already be MD5 hashed.
        """
        payload = {
            "username": username,
            "password": password_hash
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.LOGIN, payload)

    @staticmethod
    def build_list_devices_message() -> str:
        """
        Builds the command to request the list of all devices ("0004").
        Payload is an empty JSON object.
        """
        return HomismartCommandBuilder._build_message(RequestPrefix.LIST_DEVICES, {})

    @staticmethod
    def build_toggle_property_message(device_dict: Dict[str, Any]) -> str:
        """
        Builds the command to toggle a device's power or update its properties ("0006").
        The `device_dict` should be the full device object with the desired
        property (e.g., 'power', 'curtainState') updated, and 'updateTime' refreshed.
        """
        # Ensure 'updateTime' is present and current if this command implies an update.
        # This responsibility might also lie with the caller preparing device_dict.
        return HomismartCommandBuilder._build_message(RequestPrefix.TOGGLE_PROPERTY, device_dict)

    @staticmethod
    def build_modify_device_message(device_id: str, name: str, lock_status: str, icon_id: str) -> str:
        """
        Builds the command to modify device details like name, lock status, or icon ("0016").
        """
        payload = {
            "devid": device_id,
            "name": name,
            "lock": lock_status, # "1" for unlocked, "2" for locked
            "iconId": icon_id
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.MODIFY_DEVICE, payload)

    @staticmethod
    def build_delete_device_message(device_id: str) -> str:
        """
        Builds the command to delete a device ("0014").
        """
        payload = {
            "devid": device_id
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.DELETE_DEVICE, payload)

    @staticmethod
    def build_set_curtain_closed_pos_message(device_id_or_sn: str, position: int) -> str:
        """
        Builds the command to set a curtain's closed position ("0144").
        Note: SocketFunctions.js used "deviceSN" for this payload key.
        """
        payload = {
            "deviceSN": device_id_or_sn,
            "closedPosition": position
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.SET_CURTAIN_CLOSED_POS, payload)

    @staticmethod
    def build_modify_led_message(device_id: str, led_state_percentage: int) -> str:
        """
        Builds the command to modify a device's LED state ("0030").
        SocketFunctions.js used "ledDevice" for the state.
        """
        payload = {
            "devid": device_id,
            "ledDevice": led_state_percentage
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.MODIFY_LED, payload)

    @staticmethod
    def build_control_all_devices_message(action: str, device_type_code: int) -> str:
        """
        Builds the command to control all devices of a certain type ("0138").
        Args:
            action: "1" for ON, "0" for OFF (based on TableModel.onlineAction).
            device_type_code: Integer code for the device type category
                              (e.g., 10 for all, 1 for sockets, 45 for curtain group).
        """
        payload = {
            "action": action,
            "type": device_type_code
        }
        return HomismartCommandBuilder._build_message(RequestPrefix.CONTROL_ALL_DEVICES_BY_TYPE, payload)

    @staticmethod
    def build_heartbeat_message() -> str:
        """
        Builds the heartbeat/keep-alive message ("0072").
        Payload is an empty JSON object.
        """
        return HomismartCommandBuilder._build_message(RequestPrefix.HEARTBEAT, {})

    @staticmethod
    def build_accept_terms_message() -> str:
        """
        Builds the message to accept terms and conditions ("0222").
        Payload is an empty JSON object.
        """
        return HomismartCommandBuilder._build_message(RequestPrefix.ACCEPT_TERMS_CONDITIONS, {})

    # --- Timer Related Commands ---
    @staticmethod
    def build_get_all_timers_message() -> str:
        """Builds command to get all timers for the account ("0044"). Payload: {}"""
        return HomismartCommandBuilder._build_message(RequestPrefix.GET_ALL_TIMERS, {})

    @staticmethod
    def build_query_timers_for_device_message(device_id: str) -> str:
        """Builds command to query timers for a specific device ("0028")."""
        payload = {"devid": device_id}
        return HomismartCommandBuilder._build_message(RequestPrefix.QUERY_TIMERS, payload)

    @staticmethod
    def build_add_new_timer_message(timer_data: Dict[str, Any]) -> str:
        """Builds command to add a new timer ("0018"). timer_data is the full timer object."""
        return HomismartCommandBuilder._build_message(RequestPrefix.ADD_NEW_TIMER, timer_data)

    @staticmethod
    def build_edit_timer_message(timer_data: Dict[str, Any]) -> str:
        """Builds command to edit an existing timer ("0020"). timer_data is the full timer object."""
        return HomismartCommandBuilder._build_message(RequestPrefix.EDIT_TIMER, timer_data)

    @staticmethod
    def build_delete_timer_message(timer_id: str) -> str: # Assuming timer ID is a string
        """Builds command to delete a specific timer ("0022")."""
        payload = {"id": timer_id}
        return HomismartCommandBuilder._build_message(RequestPrefix.DELETE_TIMER, payload)

    @staticmethod
    def build_delete_all_timers_for_device_message(device_sn: str) -> str:
        """Builds command to delete all timers for a device ("0024")."""
        payload = {"deviceSN": device_sn}
        return HomismartCommandBuilder._build_message(RequestPrefix.DELETE_ALL_TIMERS, payload)

    # Add more builder methods here for other RequestPrefixes as needed,
    # following the patterns observed in SocketFunctions.js for their payloads.
    # Examples:
    # - add_device ("0012")
    # - change_password ("0040")
    # - scenario commands ("0112" - "0142")
    # - etc.

if __name__ == '__main__':
    # Example usage (can be removed or kept for simple testing)
    print("Demonstrating HomismartCommandBuilder:")

    login_cmd = HomismartCommandBuilder.build_login_message("user@example.com", "hashed_password_here")
    print(f"Login Command: {login_cmd}")

    list_devices_cmd = HomismartCommandBuilder.build_list_devices_message()
    print(f"List Devices Command: {list_devices_cmd}")

    # Example device dict for toggle property
    # In a real scenario, this would come from a HomismartDevice object's state
    sample_device_state = {
        "id": "02518744000162", "name": "Office Light", "power": False,
        "type": 2, "pid": "some_pid", "consumption": 0, "deviceId": "same_as_id",
        "version": 1, "onLine": True, "updateTime": 1678886400000, "lock": "1",
        "lastOn": "", "led": 0, "iconId": "0", "shared": False, "timers": False
        # Ensure all fields expected by the "0006" command are present
    }
    # Simulate toggling power ON
    toggled_device_state = sample_device_state.copy()
    toggled_device_state["power"] = True
    toggled_device_state["updateTime"] = 1678886500000 # New timestamp
    toggled_device_state["lastOn"] = "2023-03-15 12:01:40" # Example

    toggle_cmd = HomismartCommandBuilder.build_toggle_property_message(toggled_device_state)
    print(f"Toggle Property Command (0006): {toggle_cmd}")

    modify_cmd = HomismartCommandBuilder.build_modify_device_message(
        device_id="02518744000162",
        name="New Office Light Name",
        lock_status="1",
        icon_id="5"
    )
    print(f"Modify Device Command (0016): {modify_cmd}")

    delete_cmd = HomismartCommandBuilder.build_delete_device_message("02518744000162")
    print(f"Delete Device Command (0014): {delete_cmd}")

    heartbeat_cmd = HomismartCommandBuilder.build_heartbeat_message()
    print(f"Heartbeat Command (0072): {heartbeat_cmd}")
