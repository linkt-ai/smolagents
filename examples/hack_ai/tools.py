"""
Secure Tools for Browser Agents
================================
Tools that handle sensitive data securely via environment variables.

This prevents credentials and other secrets from being exposed in LLM prompts,
logs, or agent memory. Secrets are stored as environment variables with the
prefix AGENT_SECRET__ and accessed only when needed.
"""

import os
import signal
from typing import Any

import helium
from smolagents import Tool


class WriteSecretTool(Tool):
    """
    Tool for securely writing credentials to browser input fields.

    Retrieves secrets from environment variables prefixed with AGENT_SECRET__.
    For example, write_secret("GOOGLE_PASSWORD") uses AGENT_SECRET__GOOGLE_PASSWORD.

    This prevents sensitive values from appearing in:
    - LLM prompts
    - Agent memory/logs
    - Screenshots or debugging output

    Usage:
        # Set environment variable first:
        # AGENT_SECRET__GOOGLE_PASSWORD=mySecurePassword123

        # Agent calls:
        write_secret("GOOGLE_PASSWORD")

        # Tool retrieves env var and writes to active input field
    """

    name = "write_secret"
    description = """Writes a secure secret value to the current browser input field.
    The secret is retrieved from environment variables prefixed with AGENT_SECRET__.
    For example, write_secret("GOOGLE_PASSWORD") will use the value from env var AGENT_SECRET__GOOGLE_PASSWORD.
    This prevents sensitive values from being included in prompts or logs.

    IMPORTANT: The secret must be set as an environment variable before calling this tool.
    If the secret is not found, an error will be returned."""

    inputs = {
        "secret_name": {
            "type": "string",
            "description": "Name of the secret to write (e.g., 'GOOGLE_PASSWORD'). The actual value will be loaded from AGENT_SECRET__<secret_name> environment variable.",
        }
    }
    output_type = "string"

    def forward(self, secret_name: str) -> str:
        """
        Retrieve secret from environment and write to browser input field.

        Args:
            secret_name: Name of the secret (without AGENT_SECRET__ prefix)

        Returns:
            Success message or error if secret not found
        """
        env_var_name = f"AGENT_SECRET__{secret_name}"
        secret_value = os.getenv(env_var_name)

        if secret_value is None:
            # Get list of available AGENT_SECRET__ environment variables
            available_secrets = [
                key.replace("AGENT_SECRET__", "") for key in os.environ.keys() if key.startswith("AGENT_SECRET__")
            ]

            error_msg = (
                f"ERROR: Secret '{secret_name}' not found.\n"
                f"Please set environment variable: {env_var_name}\n"
                f"Example: export {env_var_name}='your-secret-value'\n"
                f"Or add to .env file: {env_var_name}=your-secret-value\n"
            )

            if available_secrets:
                error_msg += f"\nAvailable secrets configured:\n"
                for secret in sorted(available_secrets):
                    error_msg += f"  - {secret}\n"
                error_msg += "\nPlease use one of the available secret names above."
            else:
                error_msg += "\nNo AGENT_SECRET__ environment variables are currently set."

            return error_msg

        # Write the secret value using helium
        helium.write(secret_value)

        return f"Successfully wrote secret '{secret_name}' to the input field (value hidden for security)"


class Request2FACodeTool(Tool):
    """
    Human-in-the-loop tool for requesting 2FA codes during authentication.

    This tool pauses the agent execution and prompts the user to enter
    a 2FA code (e.g., from SMS or authenticator app). The tool has a 5-minute
    timeout to allow the user time to retrieve the code.

    This prevents 2FA codes from being hardcoded or passed through environment
    variables, while still allowing automated login flows with human assistance.

    Usage:
        # Agent detects 2FA page and calls:
        code = request_2fa_code()
        # User sees prompt: "2FA Confirmation Code: "
        # User enters code (e.g., "123456")
        # Agent receives code and can continue authentication
    """

    name = "request_2fa_code"
    description = """Requests a 2FA code from the user via human-in-the-loop interaction.

    Use this tool when you encounter 2FA/MFA verification during login flows.
    The tool will pause execution and prompt the user to enter their 2FA code.

    IMPORTANT:
    - This has a 5-minute timeout for user input
    - The user must enter the code when prompted
    - The code is returned as a string for you to use in authentication
    - If the timeout expires, an error will be returned

    Common scenarios:
    - SMS verification codes
    - Authenticator app codes (Google Authenticator, Authy, etc.)
    - Email verification codes
    - Backup codes
    """

    inputs = {}  # No inputs - just prompts the user
    output_type = "string"

    def _timeout_handler(self, signum, frame):
        """Handler for timeout signal."""
        raise TimeoutError("2FA code input timed out after 5 minutes")

    def forward(self) -> str:
        """
        Prompt the user for a 2FA code with a 5-minute timeout.

        Returns:
            The 2FA code entered by the user, or an error message if timeout
        """
        print("\n" + "=" * 80)
        print("🔐 2FA VERIFICATION REQUIRED")
        print("=" * 80)
        print("The agent needs your 2FA code to continue authentication.")
        print("Please check your phone/authenticator app for the code.")
        print("You have 5 minutes to enter the code.")
        print("=" * 80)

        try:
            # Set up timeout (5 minutes = 300 seconds)
            # Note: signal.alarm only works on Unix systems
            if hasattr(signal, "SIGALRM"):
                signal.signal(signal.SIGALRM, self._timeout_handler)
                signal.alarm(300)  # 5 minutes

            # Prompt user for input
            code = input("2FA Confirmation Code: ").strip()

            # Cancel timeout
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)

            if not code:
                return "ERROR: No 2FA code entered. Please try again."

            print(f"✅ Received 2FA code: {code}")
            print("=" * 80)
            print()

            return code

        except TimeoutError as e:
            print("\n❌ ERROR: 2FA code input timed out")
            print("=" * 80)
            return f"ERROR: {str(e)}"
        except Exception as e:
            print(f"\n❌ ERROR: Failed to get 2FA code: {str(e)}")
            print("=" * 80)
            return f"ERROR: Failed to get 2FA code: {str(e)}"


class SaveToCSVTool(Tool):
    """
    Tool for saving structured data to a CSV file.

    Takes a list of dictionaries where each dictionary represents a row,
    and writes them to a CSV file with automatic header generation.

    Examples:
        ```python
        >>> from csv_tool import SaveToCSVTool
        >>> csv_tool = SaveToCSVTool()
        >>> data = [
        ...     {"name": "John Doe", "luma_url": "https://lu.ma/user/john", "linkedin_url": "https://linkedin.com/in/johndoe"},
        ...     {"name": "Jane Smith", "luma_url": "https://lu.ma/user/jane", "linkedin_url": "https://linkedin.com/in/janesmith"}
        ... ]
        >>> result = csv_tool(data=data, filename="attendees.csv")
        >>> print(result)
        ✅ Successfully saved 2 rows to: /path/to/attendees.csv
        ```
    """

    name = "save_to_csv"
    description = (
        "Saves structured data to a CSV file. Takes a list of dictionaries and writes to CSV with headers. "
        "Each dictionary represents a row, with dictionary keys becoming column headers. "
        "Perfect for saving lists of people with names, URLs, and other structured information."
    )
    inputs = {
        "data": {
            "type": "any",
            "description": (
                "List of dictionaries to save as CSV. Each dict is a row, keys are column names. "
                "Example: [{'name': 'John', 'luma_url': 'https://lu.ma/user/john', 'linkedin_url': 'https://linkedin.com/in/john'}]"
            ),
        },
        "filename": {
            "type": "string",
            "description": "CSV filename to create (e.g., 'hackai-atendees.csv'). Can include relative or absolute path.",
        },
    }
    output_type = "string"

    def forward(self, data: Any, filename: str) -> str:
        """
        Save structured data to CSV file.

        Args:
            data: List of dictionaries where each dict is a row
            filename: Path to CSV file to create

        Returns:
            Success message with absolute file path

        Raises:
            TypeError: If data is not a list of dictionaries
            ValueError: If data is empty or invalid
            IOError: If file cannot be written
        """
        import csv
        from pathlib import Path

        # Validate data type
        if not isinstance(data, list):
            raise TypeError(f"Data must be a list of dictionaries, got {type(data).__name__}")

        if len(data) == 0:
            raise ValueError("Cannot save empty data to CSV. Provide at least one row.")

        if not all(isinstance(row, dict) for row in data):
            raise TypeError("All items in data must be dictionaries (each dict = one row)")

        # Extract headers from first row
        headers = list(data[0].keys())

        if not headers:
            raise ValueError("First dictionary is empty. Each row must have at least one field.")

        # Validate all rows have consistent structure
        for idx, row in enumerate(data, 1):
            missing_keys = set(headers) - set(row.keys())
            extra_keys = set(row.keys()) - set(headers)
            if missing_keys or extra_keys:
                print(
                    f"⚠️  Warning: Row {idx} has different structure than first row. "
                    f"Missing: {missing_keys or 'none'}, Extra: {extra_keys or 'none'}"
                )

        # Create directory if needed
        filepath = Path(filename)
        if filepath.parent != Path("."):
            filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV with UTF-8 encoding for international characters
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
        except IOError as e:
            raise IOError(f"Failed to write CSV file '{filename}': {e}")

        # Return success message with absolute path
        abs_path = filepath.resolve()
        num_columns = len(headers)
        return f"✅ Successfully saved {len(data)} rows × {num_columns} columns to CSV: {abs_path}"


# Create singleton instances for easy import
write_secret_tool = WriteSecretTool()
request_2fa_code_tool = Request2FACodeTool()
save_to_csv_tool = SaveToCSVTool()
