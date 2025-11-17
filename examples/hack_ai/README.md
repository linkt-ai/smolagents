# Hack AI Demo: Multi-Agent Browser Automation

An advanced demonstration of autonomous web browsing agents built with smolagents, showcasing:
- **Visual-grounded execution** to prevent hallucinations
- **Managed sub-agents** for modular task delegation
- **Secure credential handling** via environment variables
- **Human-in-the-loop 2FA** support
- **Screenshot-driven workflow** for observable agent behavior

## What This Demo Does

The demo extracts a complete attendee list from a Luma event page (https://lu.ma), including:
1. **Google OAuth authentication** - Automated login via Google account
2. **Event navigation** - Find and access the "Hack AI" event
3. **Attendee extraction** - Extract all guest names and Luma profile URLs from modal
4. **Profile enrichment** - Visit each profile to extract LinkedIn URLs
5. **CSV export** - Save structured data with name, Luma URL, and LinkedIn URL columns

This demonstrates a real-world workflow requiring authentication, dynamic content interaction, data extraction, and multi-page enrichment.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    luma_attendees.py (Main Orchestrator)         │
│  - Initializes browser with session reuse                       │
│  - Orchestrates high-level task flow                            │
│  - Delegates to specialized sub-agents                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ google_auth  │      │list_extraction│     │ save_to_csv  │
│   Agent      │      │    Agent      │     │    Tool      │
├──────────────┤      ├──────────────┤      ├──────────────┤
│- OAuth flow  │      │- Modal extract│     │- Export data │
│- 2FA handling│      │- Multi-page   │     │- UTF-8 safe  │
│- Secure creds│      │  enrichment   │     │- Validation  │
└──────────────┘      └──────────────┘      └──────────────┘
        │                     │
        ▼                     ▼
┌─────────────────────────────────────┐
│         Shared Utilities             │
│  - driver.py (browser mgmt)         │
│  - tools.py (secure I/O)            │
│  - agents/utils.py (common funcs)   │
└─────────────────────────────────────┘
```

### Visual → Thought → Code Workflow

All agents use a screenshot-driven execution pattern:

```
Visual:  "I can see a modal with 'Attendees (127)' header and a list of 8 visible names..."
         ↓
Thought: "I need to extract all attendee names. Let me first explore the structure."
         ↓
Code:    <code>
         from helium import find_all, Text
         elements = find_all(Text("Alice Johnson"))
         print(f"Found {len(elements)} elements")
         </code>
         ↓
Observe screenshot → Next action
```

This pattern **prevents hallucinations** by forcing agents to ground actions in literal visual observations.

---

## Core Components

### 📄 `luma_attendees.py` - Main Orchestrator

**Purpose:** High-level task orchestration and workflow coordination.

**Key Responsibilities:**
- Initialize browser with session reuse support
- Load LLM models (Vertex AI Gemini 2.5 Pro/Flash)
- Create and register managed sub-agents
- Coordinate multi-step workflow:
  1. Navigate to Luma → Check login status → Delegate to Google auth if needed
  2. Navigate to event page → Open attendee modal → Delegate to list extraction
  3. Extract attendee data → Pass to enrichment agent for LinkedIn URLs
  4. Save complete dataset to CSV

**Design Pattern:** Managed agent orchestrator with visual grounding

**Configuration:**
```python
agent = CodeAgent(
    tools=[save_to_csv_tool],
    managed_agents=[google_login_agent, list_extraction_agent],
    prompt_templates=visual_templates,  # Visual → Thought → Code
    additional_authorized_imports=["helium", "time", "json"],
    step_callbacks=[save_screenshot],
    max_steps=25,
    planning_interval=5
)
```

---

### 🔧 `tools.py` - Secure Tools

Custom tools for safe credential handling and data export.

#### **WriteSecretTool**

Securely writes credentials to browser input fields without exposing values in prompts/logs.

**Mechanism:**
- Secrets stored as environment variables: `AGENT_SECRET__<NAME>`
- Agent calls: `write_secret("GOOGLE_EMAIL")`
- Tool retrieves `AGENT_SECRET__GOOGLE_EMAIL` and writes to active input field
- Value never appears in LLM prompts, memory, or logs

**Usage:**
```python
# In agent code:
write_secret("GOOGLE_EMAIL")     # Writes email from env var
write_secret("GOOGLE_PASSWORD")  # Writes password from env var
```

**Environment Setup:**
```bash
export AGENT_SECRET__GOOGLE_EMAIL="user@gmail.com"
export AGENT_SECRET__GOOGLE_PASSWORD="secure_password"
```

#### **Request2FACodeTool**

Human-in-the-loop tool for 2FA verification during authentication.

**Mechanism:**
- Agent detects 2FA page in screenshot
- Calls `request_2fa_code()` to pause and prompt user
- User enters code via terminal (5-minute timeout)
- Agent receives code and continues authentication

**Usage:**
```python
# In agent code:
code = request_2fa_code()  # Pauses for user input
write(code)                # Enters code in verification field
click("Next")
```

**Output:**
```
🔐 2FA VERIFICATION REQUIRED
The agent needs your 2FA code to continue authentication.
Please check your phone/authenticator app for the code.
You have 5 minutes to enter the code.
2FA Confirmation Code: _
```

#### **SaveToCSVTool**

Exports structured data to CSV with UTF-8 encoding and validation.

**Features:**
- Accepts list of dictionaries (each dict = one row)
- Automatic header generation from dictionary keys
- UTF-8 encoding for international characters
- Validates data structure and provides clear error messages

**Usage:**
```python
# In agent code:
data = [
    {"name": "Alice", "luma_url": "https://lu.ma/user/alice", "linkedin_url": "https://linkedin.com/in/alice"},
    {"name": "Bob", "luma_url": "https://lu.ma/user/bob", "linkedin_url": "https://linkedin.com/in/bob"}
]
save_to_csv(data=data, filename="hack_ai_attendees.csv")
```

**Output:**
```
✅ Successfully saved 2 rows × 3 columns to CSV: /path/to/hack_ai_attendees.csv
```

---

### 🌐 `driver.py` - Browser Management

Shared utilities for browser initialization and screenshot capture.

#### **Browser Initialization Functions**

**`initialize_browser()`**
- Starts new Chrome with anti-detection measures
- Removes automation flags to avoid CAPTCHAs
- Enables remote debugging on port 9222 for session reuse
- Returns WebDriver instance

**Anti-Detection Features:**
```python
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
```

**`initialize_browser_with_reuse()`**
- Checks for existing Chrome session on port 9222
- Prompts user to connect or start fresh
- **Benefits:** Skip re-authentication, faster startup, preserve session state
- Used by main orchestrator for demo workflow

**`require_existing_chrome(port=9222)`**
- Connects to existing Chrome session (required - won't start new browser)
- Used by scripts that assume user already navigated to target page
- Exits with helpful error if no Chrome found

**`connect_to_existing_chrome(port=9222)`**
- Low-level function to connect via remote debugging protocol
- Used by reuse/require functions

**`is_chrome_running_on_port(port)`**
- Checks if Chrome is accessible on specified port
- Returns True if remote debugging is available

#### **Screenshot Callback**

**`save_screenshot(memory_step: ActionStep, agent: CodeAgent)`**
- Callback registered to agent's step_callbacks
- Captures PNG screenshot after each action
- Stores in agent memory for LLM to "see"
- Handles window switching gracefully (e.g., OAuth popup closes)
- Adds current URL to observations

**Integration:**
```python
from driver import save_screenshot

agent = CodeAgent(
    step_callbacks=[save_screenshot],
    ...
)
```

---

### 🤖 `agents/` - Managed Sub-Agents

The `agents/` directory contains specialized managed agents that handle specific tasks.

#### **Managed Agent Pattern**

All agents follow this structure:

```python
def create_agent_name(model) -> CodeAgent:
    """Factory function that creates a configured CodeAgent."""

    INSTRUCTIONS = """
    Detailed instructions for the agent...
    Enforces Visual → Thought → Code pattern
    """

    # Import tools (deferred to avoid circular dependencies)
    from tools import some_tool

    agent = CodeAgent(
        name="agent_name",           # REQUIRED for managed agents
        description="Capabilities",  # REQUIRED for parent agent
        instructions=INSTRUCTIONS,   # Embedded in system prompt
        tools=[some_tool],
        model=model,
        prompt_templates=visual_templates,
        additional_authorized_imports=["helium", "time"],
        max_steps=15,
        verbosity_level=2
    )

    # Pre-load common imports
    preload_helium(agent)

    return agent
```

#### **🔐 Google Authentication Agent** (`agents/google_auth.py`)

**Purpose:** Handles Google account authentication including OAuth redirects and 2FA.

**Key Features:**
- **Dual mode support:**
  - Standalone: Navigates to accounts.google.com
  - OAuth: Detects when already on Google auth page
- **Secure credentials:** Uses WriteSecretTool to avoid exposing passwords
- **2FA support:** Human-in-the-loop via Request2FACodeTool
- **Screenshot-driven:** Analyzes page state before each action (detects 2FA pages, verification prompts, etc.)

**Workflow:**
1. Verify browser access
2. Navigate to Google (if not already on auth page)
3. Enter email → Click Next
4. Wait for password page → Enter password → Click Next
5. **CRITICAL CHECKPOINT:** Analyze screenshot for 2FA indicators
6. If 2FA detected:
   - Click "Try another way" → Select SMS option
   - Request code from user → Enter code → Submit
7. Verify login success → Return final answer

**Environment Variables:**
- `AGENT_SECRET__GOOGLE_EMAIL` - Google account email
- `AGENT_SECRET__GOOGLE_PASSWORD` - Google account password

**Usage:**
```python
from agents.google_auth import create_google_login_agent, create_google_login_task

google_login_agent = create_google_login_agent(model)
task = create_google_login_task()
result = google_login_agent.run(task)
```

#### **📋 List Extraction Agent** (`agents/list_extraction.py`)

**Purpose:** Extracts structured data from web pages using TEXT-FIRST discovery methodology.

**Key Innovation:** Never guesses CSS selectors. Always grounds extraction in visible text from screenshots.

**Core Philosophy:**
```
❌ WRONG: document.querySelector('.attendee-card')  ← Guessing at class names
✅ RIGHT: Find "Alice Johnson" visible text → Print element HTML → Build selector from observed structure
```

**Workflow:**

**Phase 1: TEXT-FIRST Exploration**
1. Look at screenshot → Identify 3-5 pieces of visible text
2. Use `find_all(Text("visible text"))` to get Helium elements
3. Print element HTML via `driver.execute_script("return arguments[0].outerHTML", element.web_element)`
4. Check multiple items (3-5) to confirm pattern
5. Build selector from observed HTML structure

**Phase 2: JavaScript Extraction**
1. Test selector on ONE element
2. Extract ALL with `querySelectorAll`
3. Return structured response

**Phase 3: Multi-Page Enrichment** (if needed)
1. Navigate to first URL → Explore structure
2. Extract data using discovered selector
3. Navigate to remaining URLs → Apply same selector
4. Aggregate results

**Structured Output:**

All responses follow this schema:
```python
# Success
{
    "status": "success",
    "data": [...],
    "count": 127
}

# Error
{
    "status": "error",
    "error": "Description of what went wrong"
}
```

Output validation is enforced via `validate_list_extraction_response()` wrapper.

**Key Techniques:**

1. **TECHNIQUE 1:** Find visible text and traverse DOM (PRIMARY)
   ```python
   elements = find_all(Text("Alice Johnson"))
   html = driver.execute_script("return arguments[0].outerHTML", elements[0].web_element)
   ```

2. **TECHNIQUE 2:** Extract multiple items by text pattern
   ```python
   for name in ["Alice", "Bob", "Carol"]:
       elements = find_all(Text(name))
       # Print HTML to confirm pattern
   ```

3. **TECHNIQUE 3:** Print HTML when text search fails (FALLBACK)
   ```python
   driver.execute_script("return document.body.innerHTML")[:5000]
   ```

4. **TECHNIQUE 4:** Navigate to URLs for enrichment
   ```python
   go_to(profile_url)
   time.sleep(2)
   ```

5. **TECHNIQUE 5:** Build processing loop
   ```python
   for url in urls:
       go_to(url)
       # Extract LinkedIn URL using discovered selector
   ```

6. **TECHNIQUE 6:** Sample before scaling (explore 2 samples first)
   ```python
   # Try first 2 profiles to discover pattern
   # Then apply to all remaining profiles
   ```

**Usage:**
```python
from agents.list_extraction import create_list_extraction_agent

list_extraction_agent = create_list_extraction_agent(model)

# Parent agent delegates:
result = list_extraction(task="Extract all guest names and Luma profile URLs from the open modal")
data = json.loads(result)['data']  # Parse structured response
```

#### **🔧 Shared Utilities** (`agents/utils.py`)

Common functions used across all agents.

**`register_screenshot_callback(agent: CodeAgent)`**
- Registers screenshot callback from driver.py to agent

**`validate_credentials(required_secrets: list[str]) -> bool`**
- Validates that required environment secrets are set
- Returns False and prints helpful errors if missing

**`print_credential_status(required_secrets: list[str])`**
- Prints credential status for debugging (masks passwords)

**`preload_helium(agent: CodeAgent)`**
- Pre-loads helium imports via `agent.python_executor("from helium import *")`
- Agents can use helium functions without explicit imports

**`load_litellm_model(model_id: str, **kwargs)`**
- Loads LiteLLM model with custom kwargs
- Supports Vertex AI, OpenAI, Anthropic, and 100+ providers

---

## Key Design Patterns

### 1. Visual Grounding to Prevent Hallucinations

**Problem:** Agents hallucinate about page state (e.g., "the modal is open" when it's not)

**Solution:** Visual → Thought → Code pattern enforced via `visual_code_agent.yaml` templates

**Example:**
```
Visual: "I can see a screenshot showing the lu.ma event page with a purple 'Guests' button
         in the top right section of the event card. The button displays '127' next to it."

Thought: "I need to click this button to open the attendee modal."

Code:   <code>
        from helium import click
        click("Guests")
        </code>

[Screenshot received showing modal is now open]

Visual: "A modal overlay has appeared with header 'Attendees (127)' and a scrollable list
         showing 8 visible attendee names: 'Alice Johnson', 'Bob Smith', ..."
```

The Visual observation forces the agent to **describe literal page content**, not logical states.

### 2. One-Action-Per-Code-Block Incremental Workflow

**Problem:** Agents write massive code blocks that fail midway with no observability

**Solution:** Limit to ONE action per code block (3-5 lines max)

**Example:**
```python
# ✅ GOOD - One action
<code>
from helium import click
click("Guests")
print("Clicked Guests button")
</code>

# ❌ BAD - Multiple actions
<code>
# 80 lines of code:
# Navigate, click, extract, format, return...
</code>
```

After each code block, agent receives screenshot and observes results before next action.

### 3. TEXT-FIRST Extraction Methodology

**Problem:** Guessing CSS selectors leads to brittle extraction

**Solution:** Always find elements by visible text first, then inspect HTML structure

**Workflow:**
```python
# Step 1: Find element by visible text
elements = find_all(Text("Alice Johnson"))

# Step 2: Print element HTML to discover structure
html = driver.execute_script("return arguments[0].outerHTML", elements[0].web_element)
print(html)  # Output: <a class="attendee-link" href="...">Alice Johnson</a>

# Step 3: Build selector from observed structure
selector = "a.attendee-link"

# Step 4: Extract all with discovered selector
all_data = driver.execute_script('''
    return Array.from(document.querySelectorAll('a.attendee-link')).map(el => ({
        name: el.textContent.trim(),
        url: el.href
    }));
''')
```

No assumptions. No guessing. Ground all extraction in visible text.

### 4. Browser Session Reuse

**Problem:** Re-authentication is slow and interrupts workflow

**Solution:** Chrome remote debugging on port 9222 for session persistence

**Workflow:**
```python
# First run:
driver = initialize_browser_with_reuse()
# Starts Chrome with --remote-debugging-port=9222
# User logs in, script completes

# Keep Chrome window open!

# Second run:
driver = initialize_browser_with_reuse()
# Detects existing Chrome session
# Offers to connect: "Connect to existing session? (y/n)"
# If 'y': Connects instantly, skips login ✨
```

**Benefits:**
- ⚡ Instant reconnection (no startup delay)
- 🔐 Skip authentication (already logged in)
- 💾 Preserve session state (cookies, tabs, etc.)

### 5. Secure Credential Handling

**Problem:** Credentials in prompts/logs expose sensitive data

**Solution:** Environment variable storage + tool-based injection

**Architecture:**
```
Environment Variables               Agent Memory/Prompts
─────────────────────              ──────────────────
AGENT_SECRET__GOOGLE_EMAIL    →    write_secret("GOOGLE_EMAIL")
  (hidden from LLM)                   (no value exposed)
                                            ↓
                                    WriteSecretTool retrieves
                                    env var and writes to input
                                            ↓
                                    Browser receives value
                                    (never visible to LLM)
```

**Benefits:**
- ✅ Credentials never appear in LLM prompts
- ✅ Credentials never appear in agent memory
- ✅ Credentials never appear in logs or screenshots
- ✅ Tool execution is atomic (retrieve + write)

### 6. Human-in-the-Loop 2FA

**Problem:** 2FA codes can't be automated, but manual intervention breaks agent flow

**Solution:** Request2FACodeTool pauses agent, prompts user, resumes with code

**Workflow:**
```
Agent detects 2FA page in screenshot
     ↓
Agent calls: request_2fa_code()
     ↓
Tool pauses execution and displays prompt:
─────────────────────────────────────────
🔐 2FA VERIFICATION REQUIRED
Please check your phone for the code.
You have 5 minutes to enter the code.
2FA Confirmation Code: _
─────────────────────────────────────────
     ↓
User enters: 123456
     ↓
Tool returns "123456" to agent
     ↓
Agent continues: write(code) → click("Next")
```

**Benefits:**
- ✅ Agent workflow remains autonomous (no manual code injection)
- ✅ User interaction is scoped to verification only
- ✅ 5-minute timeout prevents indefinite blocking
- ✅ Clear prompts guide user through process

---

## Prerequisites & Setup

### 1. Install Dependencies

```bash
# Core dependencies
pip install helium-selenium python-dotenv Pillow litellm

# Or install smolagents with all extras
pip install "smolagents[all]"
```

### 2. Configure Environment Variables

#### **Google Cloud Vertex AI (Recommended)**

Create `.env` file:
```bash
# Copy example template
cp .env.example .env
```

Edit `.env`:
```bash
# Vertex AI configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
VERTEXAI_PROJECT=your-gcp-project-id
VERTEXAI_LOCATION=us-central1

# Google account credentials for Luma login
AGENT_SECRET__GOOGLE_EMAIL=your-google-email@gmail.com
AGENT_SECRET__GOOGLE_PASSWORD=your-secure-password
```

**Setting up Vertex AI:**
1. Create a GCP project at console.cloud.google.com
2. Enable Vertex AI API
3. Create service account with "Vertex AI User" role
4. Download JSON key file
5. Set `GOOGLE_APPLICATION_CREDENTIALS` to key file path

#### **Alternative: Use OpenAI**

If you prefer OpenAI, modify `luma_attendees.py` line 174:

```python
# Change from:
pro_model = load_litellm_model("vertex_ai/gemini-2.5-pro", thinking={"enabled": True})

# To:
pro_model = load_litellm_model("gpt-4o", thinking={"enabled": True})
```

Then add to `.env`:
```bash
OPENAI_API_KEY=your-openai-api-key
```

### 3. Verify Setup

```bash
# Check that credentials are set
python -c "
from agents.utils import validate_credentials
validate_credentials(['GOOGLE_EMAIL', 'GOOGLE_PASSWORD'])
"
```

Expected output:
```
================================================================================
🔐 CHECKING CREDENTIALS
================================================================================
✅ AGENT_SECRET__GOOGLE_EMAIL: user@gmail.com
✅ AGENT_SECRET__GOOGLE_PASSWORD: ********** (hidden)
================================================================================
```

---

## Running the Demo

### First Run (Full Authentication)

```bash
cd examples/hack_ai
python luma_attendees.py
```

**What happens:**
1. Chrome browser opens (visible window)
2. Script navigates to Luma
3. Agent detects not logged in
4. Google auth agent handles login:
   - Enters email from `AGENT_SECRET__GOOGLE_EMAIL`
   - Enters password from `AGENT_SECRET__GOOGLE_PASSWORD`
   - If 2FA detected: Prompts you for code
5. Agent navigates to "Hack AI" event
6. Opens attendee modal
7. List extraction agent extracts all names + Luma URLs
8. Agent visits each profile to extract LinkedIn URLs
9. Saves complete dataset to `hack_ai_attendees.csv`

**Terminal output:**
```
🌐 Starting new Chrome session...
💡 TIP: After this script finishes, keep the Chrome window open!
   Next time you run the script, you can reconnect to skip login.
================================================================================

🤖 Loading Vertex AI model...
🔐 Creating Google login managed agent...
📋 Creating list extraction managed agent...
🔧 Initializing main Luma agent with managed sub-agents...

🔐 CHECKING CREDENTIALS
================================================================================
✅ AGENT_SECRET__GOOGLE_EMAIL: user@gmail.com
✅ AGENT_SECRET__GOOGLE_PASSWORD: ********** (hidden)
================================================================================

🚀 Starting Luma authenticated access task...

📸 Captured screenshot: (1400, 1200) pixels
[Agent workflow begins...]
```

### Subsequent Runs (Session Reuse)

**Keep Chrome window open after first run!**

```bash
python luma_attendees.py
```

**What happens:**
```
🔍 EXISTING CHROME SESSION DETECTED
================================================================================
Found Chrome instance with remote debugging on port 9222

Benefits of connecting:
  • Skip re-authentication (already logged in)
  • Faster startup (browser already running)
  • Preserve session state (cookies, tabs, etc.)

Connect to existing session? (y/n): y

🔗 Connecting to existing Chrome session...
✅ Connected! Current URL: https://lu.ma/hackai
================================================================================
```

Agent reconnects instantly and continues from current page state. **No re-authentication required!**

---

## Output

### Terminal Output

```
================================================================================
HACK AI EVENT - ATTENDEE LIST:
================================================================================
/path/to/hack_ai_attendees.csv
================================================================================
```

### CSV File (`hack_ai_attendees.csv`)

```csv
name,luma_url,linkedin_url
Alice Johnson,https://lu.ma/user/alice,https://linkedin.com/in/alicejohnson
Bob Smith,https://lu.ma/user/bob,https://linkedin.com/in/bobsmith
Carol White,https://lu.ma/user/carol,https://linkedin.com/in/carolwhite
...
```

---

## Troubleshooting

### Chrome doesn't open

**Symptom:** Script hangs or errors when initializing browser

**Fixes:**
```bash
# Check Chrome/Chromium is installed
which google-chrome

# Verify helium-selenium installation
pip install --upgrade helium-selenium selenium

# Check ChromeDriver is compatible with your Chrome version
# helium auto-downloads chromedriver, but manual update may help
```

### Credentials not found

**Symptom:** Error message "MISSING CREDENTIALS" or "Secret 'GOOGLE_EMAIL' not found"

**Fixes:**
```bash
# Verify environment variables are set
echo $AGENT_SECRET__GOOGLE_EMAIL
echo $AGENT_SECRET__GOOGLE_PASSWORD

# If empty, check .env file exists and is loaded
cat .env

# Load manually if needed
export AGENT_SECRET__GOOGLE_EMAIL="user@gmail.com"
export AGENT_SECRET__GOOGLE_PASSWORD="your-password"
```

### 2FA timeout

**Symptom:** "2FA code input timed out after 5 minutes"

**Fixes:**
- Retrieve code faster (check phone/authenticator immediately)
- Use SMS 2FA instead of authenticator app (agent prefers SMS)
- Run script again (Chrome session may still be logged in)

### Agent gets stuck or loops

**Symptom:** Agent repeats same action multiple times

**Fixes:**
- Increase `max_steps` in agent configuration (current: 25)
- Try more capable model: GPT-4o, Claude 3.5 Sonnet, or Gemini 2.5 Pro
- Check screenshot is being captured (look for "📸 Captured screenshot" messages)
- Verify visual templates are loaded (check logs for "Loading visual templates")

### Modal extraction fails

**Symptom:** Agent can't extract attendee list from modal

**Fixes:**
- Verify modal is visible in browser window before agent tries to extract
- Check that agent visually confirms modal is open before delegating to list_extraction
- Review screenshot to ensure modal header is visible ("Attendees (127)")
- Agent should describe modal contents in Visual observation before extraction

### Session reuse not working

**Symptom:** Can't connect to existing Chrome session

**Fixes:**
```bash
# Check Chrome is running with remote debugging
lsof -i :9222

# Expected output:
# COMMAND   PID   USER   FD   TYPE   DEVICE SIZE/OFF NODE NAME
# Google    1234  user   123u IPv4   0x...      0t0  TCP localhost:9222 (LISTEN)

# If not running, start Chrome manually with debugging:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome_debug_profile &
```

### Vertex AI authentication fails

**Symptom:** "Could not automatically determine credentials" or "PermissionDenied"

**Fixes:**
```bash
# Verify service account JSON exists
cat $GOOGLE_APPLICATION_CREDENTIALS

# Test authentication
gcloud auth application-default login

# Check service account has Vertex AI User role
gcloud projects get-iam-policy $VERTEXAI_PROJECT \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"
```

---

## Customization

### Change the Event

Edit task in `luma_attendees.py` line 200:

```python
task = """
Please help me get the full attendee list for the "Your Event Name" event on Luma...
"""
```

### Use Different Model

Edit `luma_attendees.py` lines 174-175:

```python
# Current (Vertex AI)
flash_model = load_litellm_model("vertex_ai/gemini-2.5-flash", thinking={"enabled": True})
pro_model = load_litellm_model("vertex_ai/gemini-2.5-pro", thinking={"enabled": True})

# OpenAI
flash_model = load_litellm_model("gpt-4o-mini", thinking={"enabled": True})
pro_model = load_litellm_model("gpt-4o", thinking={"enabled": True})

# Anthropic
flash_model = load_litellm_model("claude-3-5-haiku-latest", thinking={"enabled": True})
pro_model = load_litellm_model("claude-3-5-sonnet-latest", thinking={"enabled": True})
```

### Add Custom Extraction Fields

Edit list extraction task to include additional data points:

```python
# In luma_attendees.py or create custom task
task = """
Extract the following for each attendee:
- Full name
- Luma profile URL
- LinkedIn profile URL
- Company name (if visible on profile)
- Job title (if visible on profile)
"""
```

Agent will adapt extraction strategy based on task requirements.

### Export to Different Format

Replace SaveToCSVTool with custom export tool:

```python
# Create new tool in tools.py
class SaveToJSONTool(Tool):
    name = "save_to_json"
    description = "Saves structured data to JSON file"

    def forward(self, data: list[dict], filename: str) -> str:
        import json
        from pathlib import Path

        filepath = Path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return f"✅ Saved {len(data)} records to {filepath.resolve()}"

# Use in agent
save_to_json_tool = SaveToJSONTool()
agent = CodeAgent(tools=[save_to_json_tool], ...)
```

---

## Design Principles Summary

### 1. **Visual Grounding**
   - Every action starts with visual observation
   - Prevents hallucinations about UI state
   - Forces agents to describe literal page content

### 2. **Incremental Execution**
   - One action per code block (3-5 lines max)
   - Screenshot after each action
   - Observable progress at each step

### 3. **Text-First Discovery**
   - Never guess CSS selectors
   - Always find elements by visible text first
   - Inspect HTML to discover actual structure

### 4. **Secure by Design**
   - Credentials in environment, never in prompts
   - Tool-based injection (atomic operations)
   - No sensitive data in logs or memory

### 5. **Human-in-the-Loop**
   - Pause for 2FA verification
   - Clear prompts guide user
   - Timeout protection (5 minutes)

### 6. **Modular Architecture**
   - Managed sub-agents for specialized tasks
   - Reusable tools and utilities
   - Clean separation of concerns

---

## Next Steps

- **Add more agents:** LinkedIn scraper, email notifier, calendar integration
- **Improve error handling:** Retry logic, fallback strategies
- **Add unit tests:** Mock models, test agent factories
- **Optimize performance:** Parallel extraction, caching, batch processing
- **Expand tool library:** More export formats, data validation, enrichment services

---

## Questions?

For questions about:
- **Agent design:** See `agents/README.md`
- **Browser automation:** See driver.py documentation
- **Custom tools:** See tools.py examples
- **smolagents framework:** See main project README or https://huggingface.co/docs/smolagents

For issues or improvements, open a discussion or pull request.
