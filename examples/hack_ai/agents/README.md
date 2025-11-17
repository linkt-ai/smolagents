# Hack AI Agents Module

This module contains specialized managed agents for the Hack AI demo. Each agent is designed to handle a specific task and can be orchestrated by a parent agent.

## Agent Catalog

### 🔐 Google Authentication Agent (`google_auth.py`)

**Purpose:** Handles Google account authentication flows including OAuth redirects and 2FA verification.

**Key Features:**
- Dual mode support: standalone login or OAuth redirect handling
- Secure credential management via environment variables
- Human-in-the-loop 2FA support (SMS, authenticator apps)
- Screenshot-driven interaction (analyzes page state before acting)

**Usage:**
```python
from agents.google_auth import create_google_login_agent

# Create the agent
google_login_agent = create_google_login_agent(model)

# Use as standalone agent
task = create_google_login_task()
result = google_login_agent.run(task)

# Or use as managed sub-agent
main_agent = CodeAgent(
    managed_agents=[google_login_agent],
    ...
)
```

**Environment Variables Required:**
- `AGENT_SECRET__GOOGLE_EMAIL` - Google account email
- `AGENT_SECRET__GOOGLE_PASSWORD` - Google account password

**Dependencies:**
- `tools.write_secret_tool` - Securely writes credentials to input fields
- `tools.request_2fa_code_tool` - Human-in-the-loop 2FA code collection

---

### 📋 List Extraction Agent (`list_extraction.py`)

**Purpose:** Extracts structured data from web pages using TEXT-FIRST discovery methodology.

**Key Features:**
- **TEXT-FIRST approach:** Always grounds extraction in visible text from screenshots (never guesses at CSS selectors)
- **TreeWalker-based DOM traversal:** Finds text nodes and traverses up to discover actual HTML structure
- **Multi-page enrichment:** Can visit multiple URLs to enrich data (e.g., scraping LinkedIn URLs from profile pages)
- **Incremental exploration:** Samples first, then scales to full extraction

**Usage:**
```python
from agents.list_extraction import create_list_extraction_agent, create_list_extraction_task

# Create the agent
list_extraction_agent = create_list_extraction_agent(model)

# Create a task
task = create_list_extraction_task(
    description="names and Luma profile URLs of the guests attending the event",
    count="48"  # Optional: helps validate extraction completeness
)

# Run standalone
result = list_extraction_agent.run(task)

# Or use as managed sub-agent
main_agent = CodeAgent(
    managed_agents=[list_extraction_agent],
    ...
)
```

**Core Philosophy:**
```
❌ WRONG: querySelector('.attendee-list') ← Guessing at class names
✅ RIGHT: Find "48 Guests" visible text → Traverse up → Extract links from container
```

**Key Techniques:**
1. **TECHNIQUE 1:** Find visible text and traverse DOM (PRIMARY)
2. **TECHNIQUE 2:** Extract multiple items by text pattern
3. **TECHNIQUE 3:** Print HTML when text search fails (FALLBACK)
4. **TECHNIQUE 4:** Navigate to URLs
5. **TECHNIQUE 5:** Build processing loop with text-based extraction
6. **TECHNIQUE 6:** Sample before scaling (explore 2 samples first)

**Dependencies:**
- None (uses only helium and JavaScript execution)

---

## Architecture

### Managed Agent Pattern

All agents in this module follow the **managed agent** pattern:

```python
def create_agent(model) -> CodeAgent:
    """
    Factory function that creates a configured CodeAgent.

    Returns:
        CodeAgent with:
        - name: Required for managed agent identification
        - description: Required for parent agent to understand capabilities
        - instructions: Built-in system prompt (always included)
        - tools: Agent-specific tools
        - additional_authorized_imports: Allowed Python modules
    """
    agent = CodeAgent(
        name="agent_name",  # REQUIRED
        description="What this agent does",  # REQUIRED
        instructions=INSTRUCTIONS,  # CRITICAL: always included
        tools=[...],
        model=model,
        ...
    )

    # Pre-load common imports
    agent.python_executor("from helium import *")

    return agent
```

### Key Principles

1. **Instructions as System Prompt:** Instructions are embedded in the agent via the `instructions` parameter, ensuring they're always present even when called as a managed sub-agent.

2. **Deferred Tool Imports:** Tools are imported inside factory functions to avoid circular dependencies and module load-time issues.

3. **Pre-loaded Imports:** Common imports like `from helium import *` are pre-loaded via `python_executor()` so agents don't need to import them explicitly.

4. **Screenshot-Driven Workflow:** All agents work incrementally—take action → get screenshot → analyze → next action. No massive code blocks.

5. **Human-in-the-Loop Support:** Critical operations (2FA, etc.) can pause for human input via custom tools.

---

## Shared Utilities

These utilities have been refactored into `agents/utils.py` for reuse across all agents:

### Screenshot Callback

**Location:** `agents/utils.py:register_screenshot_callback()`

**Used by:**
- `luma_events_with_login.py` (main agent)
- All managed agents when tested standalone

**Usage:**
```python
from agents.utils import register_screenshot_callback

agent = create_my_agent(model)
register_screenshot_callback(agent)
# Agent will now capture screenshots after each action
```

### Browser Initialization

**Currently in:** `driver.py`

**Functions:**
- `initialize_browser()` - Start new Chrome with anti-detection
- `initialize_browser_with_reuse()` - Offer to reuse existing Chrome session
- `require_existing_chrome()` - Connect to existing Chrome (no new browser)
- `connect_to_existing_chrome()` - Low-level connection to remote debugging port
- `is_chrome_running_on_port()` - Check if Chrome is accessible

**Used by:**
- `luma_events_with_login.py` - Main orchestrator
- Standalone agent test scripts

**Should stay in:** `driver.py` (browser utilities are project-level, not agent-specific)

### Credential Validation

**Location:** `agents/utils.py:validate_credentials()` and `print_credential_status()`

**Used by:**
- `luma_events_with_login.py` (main orchestrator)
- Any script that needs to verify environment secrets

**Usage:**
```python
from agents.utils import validate_credentials, print_credential_status

# Validate required secrets (returns False and prints errors if missing)
if not validate_credentials(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]):
    return  # Exit early

# Print credential status for debugging (masks passwords)
print_credential_status(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"])
```

### Helium Pre-loading

**Location:** `agents/utils.py:preload_helium()`

**Used by:**
- All agents that use helium for browser automation

**Usage:**
```python
from agents.utils import preload_helium

agent = CodeAgent(...)
preload_helium(agent)
# Agent can now use helium functions without explicit imports
```

### Task Creation Helpers

**Location:**
- `agents/google_auth.py:create_google_login_task()`
- `agents/list_extraction.py:create_list_extraction_task(description, count)`

**Pattern:** Simple string formatting functions that create task prompts

**Kept in:** Respective agent files (task-specific, not shared)

---

## Shared Utilities API Reference

The `agents/utils.py` module provides the following functions:

### `register_screenshot_callback(agent: CodeAgent) -> None`
Registers screenshot callback to capture screenshots after each agent action.

**Parameters:**
- `agent`: CodeAgent instance to add callback to

**Example:**
```python
from agents.utils import register_screenshot_callback
register_screenshot_callback(my_agent)
```

### `validate_credentials(required_secrets: list[str]) -> bool`
Validates that required environment secrets are set.

**Parameters:**
- `required_secrets`: List of secret names without `AGENT_SECRET__` prefix (e.g., `["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]`)

**Returns:**
- `True` if all secrets are set, `False` otherwise (prints helpful error messages)

**Example:**
```python
from agents.utils import validate_credentials
if not validate_credentials(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]):
    return  # Exit if credentials missing
```

### `print_credential_status(required_secrets: list[str]) -> None`
Prints the status of required credentials for debugging (masks passwords).

**Parameters:**
- `required_secrets`: List of secret names without `AGENT_SECRET__` prefix

**Example:**
```python
from agents.utils import print_credential_status
print_credential_status(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"])
# Output:
# 🔐 CHECKING CREDENTIALS
# ✅ AGENT_SECRET__GOOGLE_EMAIL: user@gmail.com
# ✅ AGENT_SECRET__GOOGLE_PASSWORD: ********** (hidden)
```

### `preload_helium(agent: CodeAgent) -> None`
Pre-loads helium imports into the agent's Python executor.

**Parameters:**
- `agent`: CodeAgent instance to pre-load imports into

**Example:**
```python
from agents.utils import preload_helium
agent = CodeAgent(...)
preload_helium(agent)
# Agent can now use: go_to(), click(), write(), etc.
```

---

## Benefits of Shared Utilities

The refactoring to `agents/utils.py` provides:

- ✅ **DRY** - Don't repeat yourself across multiple files
- ✅ **Consistency** - All agents use the same patterns
- ✅ **Maintainability** - Fix once, apply everywhere
- ✅ **Testability** - Shared utils can be unit tested
- ✅ **Discoverability** - Clear API with documentation
- ✅ **Type Safety** - Proper type hints for better IDE support

---

## Testing

Each agent can be tested in three modes:

### 1. Unit Testing (Not Yet Implemented)

```python
# tests/test_google_auth.py
def test_google_login_agent_creation():
    from agents.google_auth import create_google_login_agent

    model = MockModel()
    agent = create_google_login_agent(model)

    assert agent.name == "google_login"
    assert "Handles Google account authentication" in agent.description
```

### 2. Standalone Mode

Each agent has a `if __name__ == "__main__"` block for standalone testing:

```bash
# Test Google auth agent
python -m agents.google_auth

# Test list extraction agent
python -m agents.list_extraction
```

### 3. Integration Mode

Test as managed sub-agents in full workflow:

```bash
python luma_events_with_login.py
```

---

## Best Practices

### When Creating New Agents

1. **Follow the factory pattern:** `create_<agent_name>_agent(model) -> CodeAgent`
2. **Always set name and description:** Required for managed agents
3. **Embed instructions in system prompt:** Use `instructions=` parameter
4. **Import tools inside factory:** Avoid circular dependencies
5. **Pre-load common imports:** Use `python_executor("from helium import *")`
6. **Provide task helpers:** Optional `create_<agent_name>_task()` functions

### Code Structure

```python
"""
Agent Name and Purpose
======================
Brief description of what this agent does.
"""

from smolagents import CodeAgent


def create_agent(model) -> CodeAgent:
    """Create the agent with configuration."""

    INSTRUCTIONS = """
    Detailed instructions for the agent...
    """

    # Import tools (deferred)
    from tools import some_tool

    agent = CodeAgent(
        name="agent_name",
        description="...",
        instructions=INSTRUCTIONS,
        tools=[some_tool],
        model=model,
        ...
    )

    # Pre-load imports
    agent.python_executor("from helium import *")

    return agent


def create_task() -> str:
    """Optional: Create task prompt."""
    return """Task description..."""


# Standalone test mode
if __name__ == "__main__":
    # Test the agent independently
    ...
```

### Screenshot-Driven Development

All agents should:
- ✅ Work incrementally (one action → screenshot → observe → next action)
- ✅ Analyze screenshots before acting
- ✅ Use exact text from screenshots for click() commands
- ✅ Never guess at CSS selectors or element structure
- ❌ Never write massive code blocks that do everything at once

---

## Migration Notes

### From Old Structure

**Before refactoring:**
```
examples/hack_ai/
  ├── google_login_agent.py      (427 lines)
  ├── list_extraction_agent.py   (579 lines)
  └── luma_events_with_login.py
```

**After refactoring:**
```
examples/hack_ai/
  ├── agents/
  │   ├── __init__.py
  │   ├── README.md
  │   ├── google_auth.py         (301 lines - cleaner!)
  │   └── list_extraction.py     (495 lines - cleaner!)
  ├── driver.py
  ├── tools.py
  └── luma_events_with_login.py
```

**Key Changes:**
1. ✅ Removed standalone test code from agent files (was duplicating driver.py)
2. ✅ Simplified imports (tools imported inside factories)
3. ✅ Clearer module organization (agents/ subdirectory)
4. ✅ Better separation of concerns

### Breaking Changes

**None!** The refactoring maintains backward compatibility:

```python
# Old import (still works if old files exist)
from google_login_agent import create_google_login_agent

# New import (recommended)
from agents.google_auth import create_google_login_agent
```

---

## Roadmap

### Phase 1: Module Organization (✅ Complete)
- [x] Create `agents/` subdirectory
- [x] Extract Google auth agent
- [x] Extract list extraction agent
- [x] Update main script imports
- [x] Document module structure

### Phase 2: Shared Utilities (✅ Complete)
- [x] Create `agents/utils.py`
- [x] Refactor screenshot callback registration
- [x] Refactor credential validation
- [x] Add shared pre-loading utilities
- [x] Update all agents to use utils
- [x] Export utils from `agents/__init__.py`

### Phase 3: Testing Infrastructure (Future)
- [ ] Add unit tests for agent factories
- [ ] Add integration tests for agent orchestration
- [ ] Add mock models for testing
- [ ] CI/CD pipeline for agent tests

### Phase 4: Additional Agents (Future)
- [ ] LinkedIn scraper agent
- [ ] Email notification agent
- [ ] Calendar integration agent
- [ ] Data enrichment agent

---

## Questions?

For questions about:
- **Agent design patterns:** See "Best Practices" section
- **Refactoring decisions:** See "Shared Utilities" and "Future Refactoring" sections
- **Usage examples:** See individual agent docstrings or "Usage" sections
- **Testing:** See "Testing" section

For issues or improvements, consult the main project README or open a discussion.
