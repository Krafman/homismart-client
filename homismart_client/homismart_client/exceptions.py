"""
homismart_client/exceptions.py

Defines custom exceptions for the Homismart client library.
"""

class HomismartError(Exception):
    """Base class for all Homismart client exceptions."""
    pass

class AuthenticationError(HomismartError):
    """Raised when authentication with the Homismart server fails."""
    pass

class ConnectionError(HomismartError):
    """Raised for issues related to the WebSocket connection."""
    pass

class CommandError(HomismartError):
    """
    Raised when the Homismart server returns an error in response to a command.
    Typically corresponds to a "9999" error message from the server.
    """
    def __init__(self, message: str, error_code: int = None, server_info: str = None):
        """
        Initialize the CommandError.

        Args:
            message: The primary error message.
            error_code: The numerical error code received from the server.
            server_info: The informational string received from the server.
        """
        super().__init__(message)
        self.error_code = error_code
        self.server_info = server_info

    def __str__(self):
        base_str = super().__str__()
        details = []
        if self.error_code is not None:
            details.append(f"Server Code: {self.error_code}")
        if self.server_info:
            details.append(f"Server Info: '{self.server_info}'")
        if details:
            return f"{base_str} ({', '.join(details)})"
        return base_str

class DeviceNotFoundError(HomismartError):
    """Raised when an operation targets a device ID that is not found."""
    pass

class ParameterError(CommandError):
    """
    Raised when a command fails due to a parameter error, as indicated by the server.
    This is a more specific version of CommandError.
    """
    pass

if __name__ == '__main__':
    # Example usage (can be removed or kept for simple testing)
    print("Demonstrating custom exceptions:")

    try:
        raise AuthenticationError("Invalid username or password.")
    except AuthenticationError as e:
        print(f"Caught: {e}")

    try:
        raise ConnectionError("Failed to connect to WebSocket server.")
    except ConnectionError as e:
        print(f"Caught: {e}")

    try:
        raise CommandError("Server reported an issue.", error_code=72, server_info="Permission Denied")
    except CommandError as e:
        print(f"Caught: {e}")
        print(f"  Error Code: {e.error_code}")
        print(f"  Server Info: {e.server_info}")

    try:
        raise ParameterError("Invalid parameter for command.", error_code=17, server_info="Parameter 'foo' is missing")
    except ParameterError as e:
        print(f"Caught: {e}")
        print(f"  Error Code: {e.error_code}")
        print(f"  Server Info: {e.server_info}")
    except CommandError as e: # Should catch ParameterError as well
        print(f"Caught by CommandError: {e}")


    try:
        raise DeviceNotFoundError("Device with ID '12345' not found.")
    except DeviceNotFoundError as e:
        print(f"Caught: {e}")
