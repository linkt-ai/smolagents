"""
Google Login Managed Agent
==========================
A specialized managed agent that handles Google account authentication.
Designed to work within a browser session managed by a parent agent.

This is a NAIVE implementation for initial testing. It will be enhanced later
with more robust error handling, 2FA support, and secure credential management.
"""

import importlib.resources
import yaml

from smolagents import CodeAgent


def create_google_login_agent(model) -> CodeAgent:
    """
    Create a managed agent that handles Google login flow.

    Args:
        model: The LLM model to use for the agent

    Returns:
        CodeAgent configured as a managed agent for Google authentication
    """

    # Helium instructions specifically for Google login
    GOOGLE_LOGIN_INSTRUCTIONS = """
You are a specialized agent that handles Google account login.
You have access to the helium library for browser automation.
The browser is already initialized and managed by the parent agent.

⚠️ CRITICAL CODE FORMATTING - READ THIS FIRST ⚠️
FROM YOUR VERY FIRST RESPONSE, you MUST:
1. Write your thoughts/reasoning as plain text
2. Then wrap your Python code in <code>...</code> tags
3. NEVER output code without <code> tags - the system will reject it

Example of CORRECT first response:
I will check browser access and start the login process.
<code>
import time
from helium import get_driver
driver = get_driver()
print(f"Browser ready: {driver is not None}")
</code>

Example of WRONG first response (will cause parsing errors):
I will check browser access.
import time
from helium import get_driver  # ❌ NO! This will fail - missing <code> tags

CRITICAL - NO IMPORTS NEEDED:
- Helium is ALREADY imported via "from helium import *" - DO NOT import it again
- Tools (write_secret, request_2fa_code) are ALREADY available - DO NOT import them
- Only import the time module: "import time"
- Use helium functions directly: go_to(), click(), write(), get_driver(), etc.
- Use tools directly: write_secret("SECRET_NAME"), request_2fa_code()

Your task is to sign into Google with the provided credentials.

IMPORTANT - Browser Session:
The browser is already running and managed by the parent agent. You share the same
browser session via helium's global driver state. DO NOT try to start a new browser.
Simply use helium functions like go_to(), click(), write(), etc.

USAGE MODES:
This agent supports two usage modes:
1. Standalone: Called directly to log into Google (will navigate to accounts.google.com)
2. OAuth: Called when already on a Google auth page (e.g., after clicking "Sign in with Google" on another site)
The agent automatically detects which mode to use based on the current URL.

GOOGLE LOGIN FLOW:
1. Verify browser access and import time module
<code>
import time
# NO helium imports needed - already available!
driver = get_driver()
if driver is None:
    final_answer("ERROR: Browser driver not accessible. Browser must be initialized before calling this agent.")
print(f"Browser driver accessible: {driver is not None}")
</code>

2. Navigate to Google sign-in page (if needed) and enter email
<code>
# Check if already on Google auth page (e.g., from OAuth redirect)
driver = get_driver()
current_url = driver.current_url
if "accounts.google.com" not in current_url:
    print("Not on Google auth page, navigating...")
    go_to('https://accounts.google.com')
    time.sleep(2)
else:
    print(f"Already on Google auth page: {current_url}")
    time.sleep(1)
# Enter email - CRITICAL: Use exact secret name GOOGLE_EMAIL (not GOOGLE_USERNAME)
# NO import needed - write_secret is already available as a tool!
write_secret("GOOGLE_EMAIL")
time.sleep(1)  # Brief pause before clicking
click("Next")
</code>

3. Wait for password page, then enter password and submit
<code>
time.sleep(3)  # Wait for page transition
# CRITICAL: Use exact secret name GOOGLE_PASSWORD
# NO import needed - write_secret is already available as a tool!
write_secret("GOOGLE_PASSWORD")
time.sleep(1)  # Brief pause before clicking
click("Next")
</code>

4. MANDATORY: Check screenshot for 2FA - DO NOT SKIP THIS STEP
<code>
time.sleep(4)  # Wait for authentication to process
driver = get_driver()
current_url = driver.current_url
print(f"Current URL after password: {current_url}")
# DO NOT PROCEED TO STEP 6 - YOU MUST ANALYZE THE SCREENSHOT FIRST
</code>

CRITICAL CHECKPOINT - After step 4, you MUST receive a screenshot and ANALYZE it.
Look at the screenshot carefully for these indicators:

IF YOU SEE ANY OF THESE, YOU MUST DO STEP 5 (2FA):
- "2-Step Verification" text
- "Verify it's you" heading
- "Get a verification code" button/link
- Phone number prompts (e.g., "••• ••• 1234")
- Authenticator app prompts
- "Try another way" link
- Any verification code input field

IF YOU SEE NONE OF THESE (you're on a different page like lu.ma or account settings), SKIP TO STEP 6.

5. IF AND ONLY IF you saw 2FA indicators in the screenshot, handle 2FA:

IMPORTANT: Work incrementally - do ONE action, get screenshot, analyze, then next action.

5a. Click "Try another way" to see verification options
<code>
time.sleep(2)  # Brief pause to ensure page is ready
click("Try another way")
time.sleep(2)  # Wait for options to appear
</code>

After step 5a, ANALYZE THE SCREENSHOT to see available 2FA methods.

5b. Select SMS/text message option (PREFERRED - do NOT use authenticator app)
Look in the screenshot for text like:
- "Get a verification code at ••• ••• 1234" (shows masked phone number)
- "Text message" or "SMS"
- Any option mentioning sending a code to your phone

AVOID these options:
- "Google Authenticator app"
- "Google prompt on your phone"
- "Security key"

<code>
# Click the SMS/text message option - use EXACT text from screenshot
# Common patterns to look for:
click("Get a verification code at")  # If you see masked phone number
# OR
# click("Text message")  # If you see this option
time.sleep(3)  # Wait for SMS to be sent and page to update
</code>

5c. Request 2FA code from user and enter it
<code>
# This will pause and prompt the user to enter their 2FA code
# NO import needed - request_2fa_code is already available as a tool!
code = request_2fa_code()
print(f"Received 2FA code: {code}")
</code>

5d. Enter the code and submit
<code>
# Use write() to enter the code (NOT type() - that doesn't exist in helium)
write(code)  # Write to currently focused field
# OR if the field is not focused:
# write(code, into="Enter code")  # Specify the field
time.sleep(1)  # Brief pause before submitting
click("Next")
time.sleep(3)  # Wait for verification to complete
</code>

6. ONLY AFTER confirming no 2FA or completing 2FA, verify login and return success
<code>
driver = get_driver()
current_url = driver.current_url
print(f"Final URL after all authentication: {current_url}")
# Check that we're NOT on a Google auth page anymore
if "accounts.google.com" in current_url and "verification" not in current_url.lower():
    print("Still on Google auth page - login may not be complete")
final_answer("Successfully logged into Google account")
</code>

IMPORTANT NOTES:
- ⚠️ CRITICAL: ALWAYS use <code>...</code> tags around ALL Python code from your FIRST response
- WITHOUT <code> tags, the code parser will fail and you'll get an error
- ⚠️ CRITICAL: DO NOT import helium or tools - they are already available!
  - Helium functions (go_to, click, write, get_driver, etc.) are PRE-LOADED
  - Tools (write_secret, request_2fa_code) are PRE-LOADED
  - ONLY import time: "import time"
- After each code block, you'll get an updated screenshot
- For 2FA: Use request_2fa_code() to get the code, then write(code) to enter it
- Use write() NOT type() - type() doesn't exist in helium
- Prefer SMS/text message 2FA over authenticator app
- Work incrementally during 2FA: click option, get screenshot, request code, get screenshot, enter code
- DO NOT make assumptions about element locations - use what you see in screenshots
- If login fails, return a clear error message with what went wrong

EFFICIENT CODE PATTERNS:
GOOD - Consolidated actions, NO unnecessary imports:
<code>
# Only import time, nothing else!
import time
go_to('https://accounts.google.com')
time.sleep(2)
write_secret("GOOGLE_EMAIL")  # Tool already available - no import!
time.sleep(1)
click("Next")
</code>

BAD - Separate blocks, or trying to import tools:
<code>
from helium import go_to  # ❌ NO! Already available
from agent_tools import write_secret  # ❌ NO! Tools already available
go_to('https://accounts.google.com')
</code>

COMMON ISSUES:
- Email field might have different text like "Email or phone"
- Password field might not load immediately - wait and check screenshot
- Google might ask to verify it's you - look for verification options
- Button text might be "Next" or "Continue" - check the screenshot
- 2FA pages vary: authenticator app, SMS, backup codes, security keys
- "Try another way" might be a link or button - check the screenshot
- Text message option might show your masked phone number
- Use partial text matches if exact match fails (e.g., "Get a verification code at" instead of full phone number)

When done (success or failure), return a clear message using final_answer().
"""

    # Import tools (deferred to avoid issues at module load time)
    from tools import request_2fa_code_tool, write_secret_tool

    # Load visual code agent prompt templates (enforces Visual → Thought → Code pattern)
    visual_templates = yaml.safe_load(
        importlib.resources.files("smolagents.prompts").joinpath("visual_code_agent.yaml").read_text()
    )

    # Create the managed agent with instructions
    # This ensures the instructions are ALWAYS part of the system prompt,
    # even when the agent is called as a managed agent by another agent
    login_agent = CodeAgent(
        tools=[write_secret_tool, request_2fa_code_tool],  # Secure credential and 2FA tools
        model=model,
        prompt_templates=visual_templates,  # Use visual code agent templates
        additional_authorized_imports=["helium", "time"],  # Allow helium and time
        max_steps=25,  # Google login can take multiple steps (increased for 2FA handling)
        planning_interval=5,
        verbosity_level=2,  # Show detailed logs
        name="google_login",  # REQUIRED for managed agents
        description="Handles Google account authentication in the current browser session. Navigates through the Google login flow, enters credentials securely via environment variables, handles 2FA verification via human-in-the-loop, and returns success/failure status.",  # REQUIRED for managed agents
        instructions=GOOGLE_LOGIN_INSTRUCTIONS,  # CRITICAL: Include instructions in system prompt
    )

    # Pre-load helium using shared utility
    from agents.utils import preload_helium

    preload_helium(login_agent)

    return login_agent


def create_google_login_task() -> str:
    """
    Create a task prompt for the Google login agent.

    Credentials are loaded from environment variables:
    - AGENT_SECRET__GOOGLE_EMAIL: Your Google account email
    - AGENT_SECRET__GOOGLE_PASSWORD: Your Google account password

    2FA codes are requested from the user via human-in-the-loop using the
    request_2fa_code() tool with a 5-minute timeout.

    Returns:
        Task string for the agent
    """
    task = """
Please log into Google using the credentials stored in environment variables.

IMPORTANT:
- Combine related actions in single code blocks
- Import time once at the start, then reuse it
- ALWAYS wrap code in <code>...</code> tags

CRITICAL - EXACT SECRET NAMES TO USE:
The write_secret tool requires EXACT secret names. Use these EXACT names:
- write_secret("GOOGLE_EMAIL") for the email address (NOT "GOOGLE_USERNAME")
- write_secret("GOOGLE_PASSWORD") for the password

DO NOT use variations like "GOOGLE_USERNAME", "EMAIL", "USERNAME", etc.
If you use the wrong name, the tool will show you which secrets ARE available.

Follow the Google login flow:
1. Import time and verify browser access
2. Navigate to Google + enter email + click Next (all in one code block)
3. Wait for password page + enter password + click Next (all in one code block)
4. MANDATORY: Wait and check screenshot for 2FA/verification page

AFTER STEP 4 - CRITICAL CHECKPOINT:
You MUST analyze the screenshot before proceeding. DO NOT skip to step 6.

IF YOU SEE 2FA/VERIFICATION IN THE SCREENSHOT:
5a. Click "Try another way" + select text message option (combined)
5b. Use request_2fa_code() + enter code + submit (combined)
6. Verify login and return success

Work efficiently - combine waits with actions in the same code blocks.
The request_2fa_code() tool has a 5-minute timeout for user input.
"""
    return task
