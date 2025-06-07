# Homismart Client

This repository contains an unofficial Python library for controlling Homismart smart home devices via their WebSocket API. It provides asynchronous helpers to log in with your Homismart account, discover devices and send commands such as turning switches on or off.

## Installation

1. Clone this repository.
2. (Optional) create and activate a virtual environment.
3. Install the package from the project root:

```bash
pip install .
```

Dependencies listed in `requirements.txt` will be installed automatically.

## How to Run

Set your Homismart credentials in environment variables:

```bash
export HOMISMART_USERNAME="your_email@example.com"
export HOMISMART_PASSWORD="your_password"
```

You can then run the example script included in the project:

```bash
python homismart_client/examples/basic_usage.py
```

The example connects to the Homismart service, lists devices and performs a simple action. Use `HomismartClient` in your own scripts to build custom automations.

## License

This project is licensed under the MIT License.
