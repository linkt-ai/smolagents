"""
Luma Event Attendee Extractor with Google OAuth
================================================
Advanced browser agent that:
1. Uses a managed sub-agent to sign into Google
2. Uses Google OAuth to sign into Luma
3. Navigates to the "Hack AI" event
4. Extracts the full list of attendees with names and profile URLs

Demonstrates managed agents, OAuth flows, authenticated session handling,
and detailed data extraction from dynamic web pages.
Designed for live demo with visible browser.
"""

import importlib.resources

import yaml
from dotenv import load_dotenv

from smolagents import CodeAgent

# Import shared browser driver utilities
from driver import initialize_browser_with_reuse, save_screenshot

# Import our managed agents from the agents module
from agents.google_auth import create_google_login_agent
from agents.list_extraction import create_list_extraction_agent
from agents.utils import (
    load_litellm_model,
    preload_helium,
    print_credential_status,
    register_screenshot_callback,
    validate_credentials,
)

# Import custom CSV export tool
from tools import save_to_csv_tool


def initialize_main_agent(model, google_login_agent, list_extraction_agent):
    """
    Create the main CodeAgent configured for Luma browsing with managed sub-agents.

    Args:
        model: The LLM model to use
        google_login_agent: The managed agent that handles Google authentication
        list_extraction_agent: The managed agent that extracts lists from web pages

    Returns:
        CodeAgent with managed sub-agents for Google login and list extraction
    """
    # Enhanced helium instructions for authenticated Luma access
    LUMA_INSTRUCTIONS = """
You are a specialized agent for navigating Luma and extracting event information.
You have access to the helium library for browser automation.
The browser is already initialized and managed.
We've already ran "from helium import *"


OBSERVATION-BASED WORKFLOW:
This is NOT a "write all the code at once" task. You MUST:
1. Take ONE action (navigate, click, etc.)
2. Wait for the screenshot in the next observation
3. ANALYZE what you see in the screenshot
4. Decide the next action based on what you OBSERVE
5. Repeat

DO NOT:
- Write massive code blocks that do everything at once
- Assume button text without checking the screenshot
- Guess CSS selectors or element structures
- Make assumptions about page content

DO:
- Check the screenshot after EVERY action
- Look for elements by examining what's actually visible
- Use generic click("text") based on what you SEE
- Work incrementally: action → observe → action → observe

IMPORTANT REMINDERS:
- Work incrementally - ONE step at a time
- After EACH action, you will receive a screenshot. ALWAYS check the screenshot before deciding the next action
- ANALYZE the screenshot before taking the next action
- Use generic click("text") with EXACT text you see in screenshots
- DO NOT assume button text or CSS selectors
- DO NOT write one giant code block that does everything
- The screenshot after each action is your source of truth. Use EXACT text you see in screenshots when clicking elements
- Be pragmatic and use common sense. Base all your actions in observations, and take actions that are grounded in your observations.


EFFICIENT CODE PATTERNS:
GOOD - Small, observable steps:
<code>
go_to('lu.ma')
time.sleep(2)
print("Loaded homepage")
</code>
[Wait for screenshot, analyze it, then...]
<code>
click("Sign in")  # Based on what I saw in the screenshot
time.sleep(2)
</code>

BAD - Everything at once:
<code>
go_to('lu.ma')
time.sleep(2)
click("Sign in")
time.sleep(2)
click("Continue with Google")
# ... 50 more lines ...
final_answer(results)
</code>

Remember: Screenshot → Observe → Action → Screenshot → Observe → Action


════════════════════════════════════════════════════════════════════════════
📦 WORKING WITH MANAGED AGENTS
════════════════════════════════════════════════════════════════════════════

Your managed agents return structured dictionaries. Parse them with json.loads():
<code>
import json
result = list_extraction(task="...")
data = json.loads(result)['data']  # This variable persists!
</code>

# Later steps can use 'data' directly:
<code>
enriched = list_extraction(task="...", additional_args={"data": data})
</code>

CRITICAL RULES:
1. ✅ Parse immediately - don't re-dispatch agents to parse for you
2. ✅ Variables persist across steps - store results once, reuse them. NEVER copy-paste JSON.
3. ❌ NEVER pass unparsed strings to tools like save_to_csv
    """.strip()

    # Load visual code agent prompt templates (enforces Visual → Thought → Code pattern)
    visual_templates = yaml.safe_load(
        importlib.resources.files("smolagents.prompts").joinpath("visual_code_agent.yaml").read_text()
    )

    return CodeAgent(
        tools=[save_to_csv_tool],  # Custom CSV export tool for saving attendee data
        model=model,
        prompt_templates=visual_templates,  # Use visual code agent templates
        managed_agents=[google_login_agent, list_extraction_agent],  # Add both managed agents
        additional_authorized_imports=["helium", "time", "json"],  # Allow helium, time, and json for parsing managed agent responses
        step_callbacks=[save_screenshot],  # Capture screenshots after each step
        max_steps=25,  # More steps for login + navigation + data extraction
        planning_interval=5,
        verbosity_level=2,  # Show detailed logs
        instructions=LUMA_INSTRUCTIONS,
    )


def main():
    """
    Main demo function: Use managed agent for Google login, then access Luma via OAuth
    and retrieve registered events.
    """
    # Load environment variables (Vertex AI credentials, etc.)
    load_dotenv()

    # Initialize the visible browser (shared session for all agents)
    # This will check for existing Chrome sessions and offer to reuse them
    global driver
    driver = initialize_browser_with_reuse()

    # Load the model (Vertex AI Gemini 2.5 Pro via LiteLLM)
    print("🤖 Loading Vertex AI model...")
    flash_model = load_litellm_model("vertex_ai/gemini-2.5-flash", thinking={"enabled": True})
    pro_model = load_litellm_model("vertex_ai/gemini-2.5-pro", thinking={"enabled": True})

    # Create the Google login managed agent
    print("🔐 Creating Google login managed agent...")
    google_login_agent = create_google_login_agent(flash_model)
    register_screenshot_callback(google_login_agent)

    # Create the list extraction managed agent
    print("📋 Creating list extraction managed agent...")
    list_extraction_agent = create_list_extraction_agent(pro_model)
    register_screenshot_callback(list_extraction_agent)

    # Create the main Luma agent with both managed sub-agents
    print("🔧 Initializing main Luma agent with managed sub-agents...")
    agent = initialize_main_agent(pro_model, google_login_agent, list_extraction_agent)
    preload_helium(agent)

    # Verify credentials are in environment
    if not validate_credentials(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"]):
        return

    # Print credential status for debugging
    print_credential_status(["GOOGLE_EMAIL", "GOOGLE_PASSWORD"])

    # Define the demo task (credentials loaded securely from environment)
    task = """
Please help me get the full attendee list for the "Hack AI" event on Luma, along with their
Luma profile and LinkedIn profile URLs (if available).

HIGH-LEVEL TASK FLOW:
1. If not already on the Luma page, navigate to https://luma.com.
2. Check to see if you are already logged in. If you are not, click the
    sign in button and then authenticate with Google. You have a teammate that
    can assist you in completing the Google oAuth flow.
3. Navigate to the Hack AI event page. Open the atendee list modal and ask your list extracor
    to extract tthe full set of names and luma profile URLs. You MUST visually confirm the modal
    is open BEFORE delegating to your teammate to extract the content.
4. Pass this complete list of extracted names and profiles back to your extraction assistant, and
    ask them to visit the Luma profile pages in order to enrich the lsit with LinkedIn URLs.
5. Save the complete atendee list with name, Luma profile URL, and LinkedIn profile URL columns.

IMPORTANT NOTES:
- You are responsible for high-level task flow.
- You should navigate through the pages and delegate tasks to your teammates when necessary.
- Do NOT over assign agency to your teammates, they are specialized experts.
- You MUST save the final result to a CSV file before your task is considered complete.
- Pass the path of the saved CSV file to the final_answer tool when you are finished.

HINTS (Use these to help out in the process):
- You may ALREADY be logged in on Luma, don't use the google auth teammate unless you
    are not currently authenticated
- Make SURE that you navigate to the Hack AI event detail page AND visually CONFIRM that you
    have opened the atendee modal, before you delegate tasks to your list extraction temmate
- DO NOT tell your list extraction teammate to scroll in the event modal, this will just
    confuse them. Let them handle the strategy for extracting all of the names.
    """

    # Run the agent!
    print("🚀 Starting Luma authenticated access task...\n")
    print(f"\nTask: {task}\n")

    result = agent.run(task)

    print("\n" + "=" * 80)
    print("HACK AI EVENT - ATTENDEE LIST:")
    print("=" * 80)
    print(result)
    print("=" * 80)


if __name__ == "__main__":
    main()
