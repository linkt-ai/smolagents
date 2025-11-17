"""
Shared Utilities for Hack AI Agents
====================================
Common functions used across multiple agents.

This module provides reusable utilities that reduce code duplication
and ensure consistency across all agents in the Hack AI demo.
"""

import os
from smolagents import CodeAgent
from smolagents.agents import ActionStep


def register_screenshot_callback(agent: CodeAgent) -> None:
    """
    Register screenshot callback to an agent.

    This function adds the screenshot callback from driver.py to the agent's
    step callbacks, enabling automatic screenshot capture after each action.

    Args:
        agent: CodeAgent instance to add callback to

    Example:
        >>> from agents.utils import register_screenshot_callback
        >>> agent = create_my_agent(model)
        >>> register_screenshot_callback(agent)
    """
    from driver import save_screenshot

    agent.step_callbacks.register(ActionStep, save_screenshot)


def validate_credentials(required_secrets: list[str]) -> bool:
    """
    Validate that required secrets are set in environment.

    Checks for the presence of environment variables with the AGENT_SECRET__ prefix
    and prints helpful error messages if any are missing.

    Args:
        required_secrets: List of secret names (without AGENT_SECRET__ prefix)
                         Example: ["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]

    Returns:
        True if all secrets are set, False otherwise (prints error messages)

    Example:
        >>> from agents.utils import validate_credentials
        >>> if not validate_credentials(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]):
        ...     return  # Exit early if credentials missing
    """
    missing = []
    for secret in required_secrets:
        env_var = f"AGENT_SECRET__{secret}"
        if not os.getenv(env_var):
            missing.append(secret)

    if missing:
        print("=" * 80)
        print("❌ MISSING CREDENTIALS")
        print("=" * 80)
        for secret in missing:
            print(f"  - AGENT_SECRET__{secret}")
        print()
        print("Please set these environment variables or add to .env file")
        print()
        print("Example (bash):")
        for secret in missing:
            print(f'  export AGENT_SECRET__{secret}="your-value-here"')
        print()
        print("Or add to .env file:")
        for secret in missing:
            print(f'  AGENT_SECRET__{secret}=your-value-here')
        print("=" * 80)
        return False

    return True


def preload_helium(agent: CodeAgent) -> None:
    """
    Pre-load helium imports into agent's Python executor.

    This allows agents to use helium functions (go_to, click, write, etc.)
    without explicitly importing them in their code blocks.

    Args:
        agent: CodeAgent instance to pre-load imports into

    Example:
        >>> from agents.utils import preload_helium
        >>> agent = CodeAgent(...)
        >>> preload_helium(agent)
        >>> # Agent can now use: go_to(), click(), write(), etc.
    """
    agent.python_executor("from helium import *")


def print_credential_status(required_secrets: list[str]) -> None:
    """
    Print the status of required credentials (for debugging/verification).

    Shows which credentials are set and which are missing, masking the actual values
    for security.

    Args:
        required_secrets: List of secret names (without AGENT_SECRET__ prefix)

    Example:
        >>> from agents.utils import print_credential_status
        >>> print_credential_status(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"])
        🔐 CHECKING CREDENTIALS
        ================================================================================
        ✅ AGENT_SECRET__GOOGLE_EMAIL: user@gmail.com
        ✅ AGENT_SECRET__GOOGLE_PASSWORD: ********** (hidden)
        ================================================================================
    """
    print("=" * 80)
    print("🔐 CHECKING CREDENTIALS")
    print("=" * 80)

    for secret in required_secrets:
        env_var = f"AGENT_SECRET__{secret}"
        value = os.getenv(env_var)
        if value:
            # Show email addresses, hide passwords
            if "EMAIL" in secret.upper() or "USERNAME" in secret.upper():
                print(f"✅ {env_var}: {value}")
            else:
                print(f"✅ {env_var}: ********** (hidden)")
        else:
            print(f"❌ {env_var}: NOT SET")

    print("=" * 80)
    print()


def load_litellm_model(model_id: str, **kwargs):
    """
    Load a LiteLLM model with custom kwargs.

    This is a specialized model loader for LiteLLM that allows passing
    additional configuration parameters beyond what the standard CLI
    load_model function supports.

    Args:
        model_id: The model ID to use (e.g., "vertex_ai/gemini-2.5-pro")
        **kwargs: Additional keyword arguments to pass to LiteLLMModel
                  Common options:
                  - temperature: Sampling temperature (0.0-1.0)
                  - max_tokens: Maximum tokens to generate
                  - top_p: Nucleus sampling parameter
                  - api_key: API key for the model provider
                  - api_base: Base URL for API endpoint
                  - response_format: Output format specification
                  And any other LiteLLM-supported parameters

    Returns:
        LiteLLMModel instance configured with the provided parameters

    Example:
        >>> from agents.utils import load_litellm_model
        >>> # Basic usage
        >>> model = load_litellm_model("vertex_ai/gemini-2.5-pro")
        >>>
        >>> # With custom parameters
        >>> model = load_litellm_model(
        ...     "vertex_ai/gemini-2.5-flash",
        ...     temperature=0.7,
        ...     max_tokens=2000,
        ...     top_p=0.95
        ... )
    """
    from smolagents import LiteLLMModel

    return LiteLLMModel(model_id=model_id, **kwargs)
