"""
Hack AI Agents Module
=====================
Specialized managed agents for the Hack AI demo.

This module contains production-ready agents that can be orchestrated
by parent agents to accomplish complex multi-step tasks.

Available Agents:
- google_auth: Handles Google authentication and OAuth flows
- list_extraction: Extracts structured data from web pages using TEXT-FIRST methodology

Shared Utilities:
- utils: Common helper functions for agent configuration and credential management
"""

from agents.google_auth import create_google_login_agent, create_google_login_task
from agents.list_extraction import create_list_extraction_agent, create_list_extraction_task
from agents.utils import (
    load_litellm_model,
    preload_helium,
    print_credential_status,
    register_screenshot_callback,
    validate_credentials,
)

__all__ = [
    "create_google_login_agent",
    "create_google_login_task",
    "create_list_extraction_agent",
    "create_list_extraction_task",
    "load_litellm_model",
    "preload_helium",
    "print_credential_status",
    "register_screenshot_callback",
    "validate_credentials",
]
