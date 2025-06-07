# examples/basic_usage.py
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv()
# --- Start of sys.path modification ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"INFO: Added '{project_root}' to sys.path for importing 'homismart_client'")
except Exception as e:
    print(f"ERROR: Could not modify sys.path. Ensure script structure is correct: {e}")
# --- End of sys.path modification ---

try:
    from homismart_client import (
        HomismartClient,
        AuthenticationError,
        ConnectionError,
        DeviceType,
        HomismartError
    )
    from homismart_client.devices import SwitchableDevice, HomismartDevice # CurtainDevice, LockDevice if needed
except ImportError as e_import:
    print(f"Failed to import from homismart_client: {e_import}")
    print("Ensure the 'homismart_client' package is in the parent directory of 'examples',")
    print("or that the package is installed (e.g., 'pip install .')")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("websockets").setLevel(logging.WARNING)
logger = logging.getLogger("basic_usage_example")

async def list_all_devices(client: HomismartClient):
    """Lists all connected devices and their statuses."""
    logger.info("\n--- Listing All Connected Devices ---")
    devices = client.session.get_all_devices()
    hubs = client.session.get_all_hubs()

    if not devices and not hubs:
        logger.info("No devices or hubs found.")
        return

    if hubs:
        logger.info(f"Hubs ({len(hubs)}):")
        for hub in hubs:
            logger.info(
                f"  - ID: {hub.id}, Name: '{hub.name}', Type: {hub.device_type_code}, "
                f"Online: {hub.is_online}"
            )
    if devices:
        logger.info(f"Devices ({len(devices)}):")
        for device in devices:
            status_details = f"Online: {device.is_online}"
            if isinstance(device, SwitchableDevice):
                status_details += f", Power: {'ON' if device.is_on else 'OFF'}"
            # Add more specific status details for other device types if needed
            logger.info(
                f"  - ID: {device.id}, Name: '{device.name}', Type: {device.device_type_enum} ({device.device_type_code}), "
                f"{status_details}"
            )
    logger.info("--- End of Device List ---\n")

async def turn_off_office_light(client: HomismartClient, light_name: str = "office light"):
    """Finds and attempts to turn off a device by its name."""
    logger.info(f"\n--- Attempting to turn OFF '{light_name}' ---")
    office_light_device = None
    all_potential_devices = client.session.get_all_devices() + client.session.get_all_hubs()

    for device in all_potential_devices:
        if device.name and device.name.lower() == light_name.lower():
            office_light_device = device
            break

    if not office_light_device:
        logger.warning(f"Device named '{light_name}' not found.")
        return

    if not isinstance(office_light_device, SwitchableDevice):
        logger.warning(
            f"Device '{office_light_device.name}' (ID: {office_light_device.id}) "
            f"is not a SwitchableDevice (Type: {office_light_device.device_type_code}). Cannot turn off."
        )
        return

    if not office_light_device.is_online:
        logger.warning(
            f"Device '{office_light_device.name}' (ID: {office_light_device.id}) is offline. Cannot turn off."
        )
        return

    if not office_light_device.is_on:
        logger.info(
            f"Device '{office_light_device.name}' (ID: {office_light_device.id}) is already OFF... turning ON"
        )
        await office_light_device.turn_on()
        return

    try:
        logger.info(
            f"Turning OFF device: '{office_light_device.name}' (ID: {office_light_device.id})"
        )
        await office_light_device.turn_off()
        logger.info(
            f"Turn OFF command sent to '{office_light_device.name}'. "
            "Monitor 'device_updated' events for confirmation."
        )
    except HomismartError as e:
        logger.error(
            f"Error turning off device '{office_light_device.name}': {e}"
        )
    logger.info(f"--- Finished attempt to turn OFF '{light_name}' ---\n")


async def main_example():
    username = os.environ.get("HOMISMART_USERNAME") 
    password = os.environ.get("HOMISMART_PASSWORD")

    if not username or not password:
        logger.error(
            "HOMISMART_USERNAME and HOMISMART_PASSWORD environment variables are not set. "
            "Please set them to your Homismart credentials."
        )
        logger.info("Example (Linux/macOS): export HOMISMART_USERNAME=\"your_email@example.com\"")
        logger.info("Example (Linux/macOS): export HOMISMART_PASSWORD=\"your_actual_password\"")
        logger.info("Example (Windows CMD): set HOMISMART_USERNAME=\"your_email@example.com\"")
        logger.info("Example (Windows CMD): set HOMISMART_PASSWORD=\"your_actual_password\"")
        logger.info("Example (Windows PowerShell): $env:HOMISMART_USERNAME=\"your_email@example.com\"")
        logger.info("Example (Windows PowerShell): $env:HOMISMART_PASSWORD=\"your_actual_password\"")
        return

    client = HomismartClient(username=username, password=password)

    def on_new_device(device_obj: HomismartDevice):
        logger.info(
            f"EVENT [New Device]: ID={device_obj.id}, Name='{device_obj.name}', "
            f"Type Code={device_obj.device_type_code}, Online={device_obj.is_online}"
        )

    def on_device_updated(device_obj: HomismartDevice):
        logger.info(
            f"EVENT [Device Update]: ID={device_obj.id}, Name='{device_obj.name}', "
            f"RawData='{device_obj.raw}'"
        )
        if isinstance(device_obj, SwitchableDevice):
            logger.info(f"  Switchable device '{device_obj.name}' power state: {'ON' if device_obj.is_on else 'OFF'}")

    def on_session_authenticated(auth_username: str):
        logger.info(f"EVENT [Session Authenticated]: Successfully logged in as {auth_username}.")

    def on_session_error(error_details: dict):
        logger.error(
            f"EVENT [Session Error]: Type='{error_details.get('type')}', "
            f"Class='{error_details.get('exception_class')}', "
            f"Message='{error_details.get('message')}'"
        )

    client.session.register_event_listener("new_device_added", on_new_device)
    client.session.register_event_listener("device_updated", on_device_updated)
    client.session.register_event_listener("session_authenticated", on_session_authenticated)
    client.session.register_event_listener("session_error", on_session_error)

    connect_task = None
    try:
        logger.info(f"Attempting to connect client for user: {username}...")
        connect_task = asyncio.create_task(client.connect())

        logger.info("Waiting for authentication...")
        auth_timeout = 30.0
        try:
            await asyncio.wait_for(
                _wait_for_login(client),
                timeout=auth_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Authentication timed out after {auth_timeout} seconds.")
            if connect_task and not connect_task.done():
                connect_task.cancel()
            return

        logger.info("Authentication successful. Waiting for device list to populate (5 seconds)...")
        await asyncio.sleep(5)

        await list_all_devices(client)
        await turn_off_office_light(client, "Office Light") # Adjust name if needed

        logger.info("Main tasks complete. Monitoring for 10 more seconds for any final events...")
        await asyncio.sleep(10)

    except AuthenticationError:
        logger.error("Authentication failed. Please check your credentials in environment variables.")
    except ConnectionError as e_conn:
        logger.error(f"Connection attempt failed: {e_conn}")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down client...")
    except Exception as e_main:
        logger.error(f"An unexpected error occurred in main_example: {e_main}", exc_info=True)
    finally:
        logger.info("Example finished or interrupted. Disconnecting client...")
        if client:
            await client.disconnect()
        if connect_task and not connect_task.done():
            logger.info("Cancelling main client connect task...")
            connect_task.cancel()
            try:
                await connect_task
            except asyncio.CancelledError:
                logger.info("Client connect task successfully cancelled.")
        logger.info("Client shutdown process complete.")

async def _wait_for_login(client: HomismartClient, poll_interval: float = 0.5):
    """Helper coroutine to wait until the client is logged in."""
    # Yield control once to allow client.connect() to start and set _keep_running
    await asyncio.sleep(0) 
    
    while not client.is_logged_in:
        # If _keep_running becomes false, it means disconnect() was called or connect() loop truly exited
        if not client._keep_running: # client._keep_running is an internal attribute, access if necessary
            logger.warning("Client is no longer trying to run/connect. Aborting wait for login.")
            raise ConnectionError("Client stopped attempting to connect while waiting for login.")
        
        if not client.is_connected:
            logger.debug("_wait_for_login: Client not connected yet, but still trying. Waiting...")

        await asyncio.sleep(poll_interval)
    logger.debug("Client is logged in (from _wait_for_login perspective).")

if __name__ == "__main__":
    asyncio.run(main_example())
