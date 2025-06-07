# Homismart Client Python Library

**Version: 0.1.0** (Update as versions change)

A Python library for interacting with Homismart smart home devices via their WebSocket API. This client is based on reverse-engineering the communication protocol of the official Homismart web application.

**Disclaimer:** This is an unofficial, community-driven library and is not affiliated with, authorized, or endorsed by Homismart or its parent company. Use it at your own risk. API changes by Homismart could break this library without notice.

## Table of Contents

1.  [Features](#features)
2.  [Project Status](#project-status)
3.  [Requirements](#requirements)
4.  [Installation](#installation)
5.  [Configuration](#configuration)
    * [Credentials](#credentials)
6.  [Core Concepts](#core-concepts)
    * [Asynchronous Nature](#asynchronous-nature)
    * [The `HomismartClient`](#the-homismartclient)
    * [The `HomismartSession`](#the-homismartsession)
    * [Device Objects](#device-objects)
    * [Event System](#event-system)
7.  [Basic Usage Example](#basic-usage-example)
8.  [API Documentation](#api-documentation)
    * [`HomismartClient`](#apihomismartclient)
    * [`HomismartSession`](#apihomismartsession)
    * [`HomismartDevice` (Base Class)](#apihomismartdevice-base-class)
    * [`SwitchableDevice`](#apiswitchabledevice)
    * [`CurtainDevice`](#apicurtaindevice)
    * [`LockDevice`](#apilockdevice)
    * [`HomismartHub`](#apihomismarthub)
    * [Enums (`DeviceType`, `ErrorCode`, etc.)](#apienums)
9.  [Error Handling](#error-handling)
10. [Logging](#logging)
11. [Development & Contributing](#development--contributing)
12. [License](#license)

## Features

* Connects to the Homismart WebSocket server.
* Handles authentication (login) using username and password.
* Manages device states and updates them in real-time based on server messages.
* Provides an object-oriented interface for interacting with various device types:
    * **Switches and Sockets:** Turn on/off, toggle power, control LED indicators.
    * **Curtains and Shutters:** Open, close, set to a specific level, stop, and set calibrated closed position.
    * **Door Locks:** Lock and unlock.
    * **Hubs/Main Units:** Basic information and renaming.
* Automatically handles server-initiated reconnections and IP/port redirections.
* Asynchronous design using Python's `asyncio` and the `websockets` library.
* Customizable event system to react to:
    * New devices being added.
    * Existing device states being updated.
    * Successful session authentication.
    * Session-level errors and server errors.

## Project Status

Currently in **Alpha**. The core functionality for device discovery and control of common device types (switches, curtains, locks) is implemented. More advanced features, support for a wider range of device types (e.g., timers, scenarios, cameras), and more comprehensive error handling are planned for future development.

**The API is subject to change in future versions as the library evolves and more is understood about the Homismart protocol.**

## Requirements

* Python 3.8 or higher (due to `asyncio` features and type hinting).
* `websockets` library (version 10.0 or higher is recommended).

## Installation

1.  **Clone the repository (if you have access to it, or download the source):**
    ```bash
    # If hosted on GitHub, for example:
    # git clone [https://github.com/your_username/homismart-client.git](https://github.com/your_username/homismart-client.git)
    # cd homismart-client
    ```

2.  **Create and activate a Python virtual environment (highly recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install the package and its dependencies:**
    Navigate to the root directory of the project (where `setup.py` is located) and run:
    ```bash
    pip install .
    ```
    This command will install the `homismart_client` package and any dependencies listed in `setup.py` (like the `websockets` library).

    For development purposes, you can install the package in editable mode. This allows you to make changes to the library code and have them immediately reflected without needing to reinstall:
    ```bash
    pip install -e .
    ```

## Configuration

### Credentials

To interact with your Homismart devices, the client needs your Homismart account username (typically your email address) and password.

It is **strongly recommended** to provide these credentials using environment variables for security, rather than hardcoding them into your scripts. The library will look for:

* `HOMISMART_USERNAME`
* `HOMISMART_PASSWORD`

**Setting Environment Variables:**

* **On macOS/Linux (in your terminal session):**
    ```bash
    export HOMISMART_USERNAME="your_email@example.com"
    export HOMISMART_PASSWORD="your_actual_password"
    ```

* **On Windows (Command Prompt, for the current session):**
    ```cmd
    set HOMISMART_USERNAME="your_email@example.com"
    set HOMISMART_PASSWORD="your_actual_password"
    ```

* **On Windows (PowerShell, for the current session):**
    ```powershell
    $env:HOMISMART_USERNAME = "your_email@example.com"
    $env:HOMISMART_PASSWORD = "your_actual_password"
    ```

For a more permanent solution, especially during development, consider using a `.env` file with the `python-dotenv` library.
1.  Install `python-dotenv`: `pip install python-dotenv`
2.  Create a `.env` file in your project's root directory:
    ```env
    HOMISMART_USERNAME="your_email@example.com"
    HOMISMART_PASSWORD="your_actual_password"
    ```
3.  **Important:** Add `.env` to your `.gitignore` file to prevent committing credentials.
4.  Load it at the beginning of your script:
    ```python
    from dotenv import load_dotenv
    load_dotenv()
    # Now os.environ.get() will find these variables.
    ```

## Core Concepts

### Asynchronous Nature

The `homismart-client` library is built using `asyncio`, making it suitable for non-blocking I/O operations, which is essential for handling real-time WebSocket communication. Most methods that involve network communication (connecting, sending commands, etc.) are `async` coroutines and must be `await`ed.

### The `HomismartClient`

The `HomismartClient` class (from `homismart_client.client`) is the main entry point for using the library. It is responsible for:

* Managing the WebSocket connection to the Homismart server.
* Handling the authentication process.
* Sending commands and receiving messages.
* Coordinating with the `HomismartSession` for message processing and device state management.
* Managing server-initiated redirections.
* Handling automatic reconnections.

### The `HomismartSession`

Accessible via `client.session`, the `HomismartSession` class (from `homismart_client.session`) manages the active, authenticated session. Its key responsibilities include:

* Storing and managing all known device objects (`HomismartDevice` and its subclasses).
* Processing incoming messages from the server (dispatched by `HomismartClient`).
* Updating device states based on server messages.
* Instantiating the correct device type objects (e.g., `SwitchableDevice`, `CurtainDevice`).
* Providing an event system for applications to subscribe to changes.
* Offering methods to retrieve device objects (e.g., `get_device_by_id`, `get_all_devices`).

### Device Objects

Individual Homismart devices are represented by instances of `HomismartDevice` (from `homismart_client.devices.base_device`) or one of its specific subclasses (e.g., `SwitchableDevice`, `CurtainDevice`, `LockDevice`, `HomismartHub`) found in the `homismart_client.devices` package.

These objects hold the current state of the device (e.g., name, ID, power status, online status, specific attributes like curtain level) and provide `async` methods to interact with the device (e.g., `turn_on()`, `set_level()`).

Device states are automatically updated by the `HomismartSession` when new messages arrive from the server.

### Event System

The `HomismartSession` provides a simple event system allowing your application to react to various occurrences. You can register and unregister callback functions for events like:

* `new_device_added`: Fired when a new device is discovered (receives the device object).
* `device_updated`: Fired when an existing device's state is updated (receives the device object).
* `new_hub_added`: Fired for new hub devices.
* `hub_updated`: Fired for hub device updates.
* `device_deleted` / `hub_deleted`: Fired if a device/hub is removed from the list provided by the server.
* `session_authenticated`: Fired after successful login (receives the username).
* `session_error`: Fired for various errors, including server-reported command errors ("9999" messages) or connection issues (receives a dictionary with error details).

See the `HomismartSession` API documentation below for how to use `register_event_listener`.

## Basic Usage Example

This example demonstrates connecting to the Homismart service, listing devices, and performing a simple action. Ensure you have set your credentials as environment variables.

```python
import asyncio
import logging
import os

# Make sure the library is installed or sys.path is configured
from homismart_client import (
    HomismartClient,
    AuthenticationError,
    ConnectionError,
    HomismartError
)
from homismart_client.devices import SwitchableDevice, HomismartDevice

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"