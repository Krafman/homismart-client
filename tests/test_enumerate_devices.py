import os
import sys
import asyncio
from typing import List

# Ensure the project root is on sys.path for direct execution
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from homismart_client import HomismartClient, AuthenticationError, ConnectionError


def format_table(rows: List[List[str]], headers: List[str]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt(row: List[str]) -> str:
        return " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))

    sep = "-+-".join("-" * w for w in col_widths)
    lines = [fmt(headers), sep]
    for row in rows:
        lines.append(fmt(row))
    return "\n".join(lines)


async def enumerate_devices() -> None:
    username = os.environ.get("HOMISMART_USERNAME")
    password = os.environ.get("HOMISMART_PASSWORD")

    if not username or not password:
        print("HOMISMART_USERNAME and HOMISMART_PASSWORD environment variables are required")
        return

    client = HomismartClient(username=username, password=password)

    login_event = asyncio.Event()

    def _on_auth(_):
        login_event.set()

    client.session.register_event_listener("session_authenticated", _on_auth)

    connect_task = asyncio.create_task(client.connect())

    try:
        await asyncio.wait_for(login_event.wait(), timeout=30.0)
    except asyncio.TimeoutError:
        print("Authentication timed out")
        await client.disconnect()
        return

    await asyncio.sleep(5)  # allow device list to populate
    devices = client.session.get_all_hubs() + client.session.get_all_devices()
    rows = []
    for dev in devices:
        dtype = getattr(dev, "device_type_code", getattr(dev, "device_type_enum", "?"))
        rows.append([dev.id, dev.name or "", str(dtype), "Yes" if dev.is_online else "No"])

    print(format_table(rows, headers=["ID", "Name", "Type", "Online"]))

    await client.disconnect()
    await connect_task


if __name__ == "__main__":
    asyncio.run(enumerate_devices())
