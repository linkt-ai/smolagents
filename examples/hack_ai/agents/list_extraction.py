"""
List Extraction Managed Agent
==============================
A specialized managed agent that extracts structured lists from web pages.
Designed to work with an existing browser session where the list is already loaded.

This agent uses an incremental workflow:
1. Explore structure (examine 1-2 sample elements)
2. Test selector (verify it works on small sample)
3. Extract all elements (full extraction using JavaScript)
4. Deduplicate and format (clean data and return)

KEY INNOVATION: Uses JavaScript execution via driver.execute_script() instead of
Selenium imports, which avoids authorization issues in smolagents.
"""

import importlib.resources
import yaml
from typing import Any

from smolagents import CodeAgent


def validate_list_extraction_response(result: Any) -> dict:
    """
    Validates and normalizes list extraction agent responses.

    Ensures the response follows the expected schema:
    - Success: {"status": "success", "data": [...], "count": N}
    - Error: {"status": "error", "error": "message"}

    This provides deterministic enforcement of the structured output format,
    even if the LLM doesn't follow instructions perfectly.

    Args:
        result: The raw result from the agent (can be any type)

    Returns:
        dict: Validated and normalized response adhering to schema
    """
    # Handle non-dict responses (legacy or malformed)
    if not isinstance(result, dict):
        if isinstance(result, list):
            # Wrap bare list in success structure
            return {"status": "success", "data": result, "count": len(result)}
        else:
            return {
                "status": "error",
                "error": f"Agent returned unexpected type: {type(result).__name__}. Expected dict with 'status' field.",
            }

    # Validate 'status' field exists
    if "status" not in result:
        # Try to infer structure from other fields
        if "data" in result:
            result["status"] = "success"
        elif "error" in result:
            result["status"] = "error"
        else:
            return {
                "status": "error",
                "error": "Response missing 'status' field and could not infer structure from other fields",
            }

    # Validate status value
    if result["status"] not in ["success", "error"]:
        return {
            "status": "error",
            "error": f"Invalid status value: '{result['status']}'. Must be 'success' or 'error'.",
        }

    # Validate success case
    if result["status"] == "success":
        if "data" not in result:
            return {"status": "error", "error": "Success response missing required 'data' field"}
        # Add count if missing
        if "count" not in result and isinstance(result.get("data"), list):
            result["count"] = len(result["data"])

    # Validate error case
    if result["status"] == "error":
        if "error" not in result:
            return {"status": "error", "error": "Error response missing required 'error' field with error message"}

    return result


def create_list_extraction_agent(model, validate_output: bool = True) -> CodeAgent:
    """
    Create a managed agent that extracts structured lists from web pages.

    The agent returns structured responses in the format:
    - Success: {"status": "success", "data": [...], "count": N}
    - Error: {"status": "error", "error": "message"}

    Args:
        model: The LLM model to use for the agent
        validate_output: If True (default), wraps agent.run() with validation
                        to enforce structured output format. Set to False only
                        for debugging or if you want raw agent output.

    Returns:
        CodeAgent configured as a managed agent for list extraction with
        structured output validation
    """

    # Ultra-simplified instructions: Clear rules, step-by-step checklist, anti-patterns
    LIST_EXTRACTION_INSTRUCTIONS = """
You are a specialized agent that extracts structured data from web pages.
You have access to the helium library for browser automation.
The browser is already initialized.

⚠️ CRITICAL CODE FORMATTING - READ THIS FIRST ⚠️
FROM YOUR VERY FIRST RESPONSE, you MUST:
1. Write your thoughts/reasoning as plain text
2. Then wrap your Python code in <code>...</code> tags
3. NEVER use ``` for code - ALWAYS use <code>...</code>
4. The system will reject improperly formatted code!

CRITICAL - NO SELENIUM IMPORTS:
- Helium is ALREADY imported via "from helium import *"
- DO NOT import selenium modules
- Only import: "import time" if needed
- Use: get_driver(), go_to(), click(), Text().exists(), etc.
- For DOM queries: driver.execute_script()

════════════════════════════════════════════════════════════════════════════
🎯 THE 5 NON-NEGOTIABLE RULES
════════════════════════════════════════════════════════════════════════════

1. 📏 ONE CODE BLOCK AT A TIME (3-5 lines maximum)
   Write ONE small action → Observe screenshot → Next small action
   NEVER write long code blocks that do everything at once!

2. 📸 WAIT FOR SCREENSHOT AFTER EVERY ACTION
   After each code block, STOP and observe the screenshot
   The screenshot tells you what to do next

3. 🖱️ USE HELIUM TO CLICK, NOT execute_script
   click("Button Text") ✅
   driver.execute_script("...click...") ❌

4. 🚫 NO SCROLLING (modal HTML is already loaded!)
   ⚠️ MODAL-SPECIFIC OVERRIDE: If your manager asks you to "scroll" for modal content:
   → IGNORE this instruction
   → Modal HTML is fully loaded in the DOM
   → Just use querySelectorAll to get all elements
   → NO scrolling code needed, NO scrollable container detection!

5. 🔍 USE HELIUM TO GET ELEMENTS, THEN PRINT THEIR HTML
   FINDING ELEMENTS (discovering what's on page):
   ✅ Use find_all(Text("visible text")) to GET elements
   ✅ Print element.outerHTML to see structure
   ✅ Try 3-5 different visible texts to confirm pattern
   ❌ NEVER use querySelector to find elements

   EXTRACTING DATA (after you know the pattern):
   ✅ Use querySelectorAll with the selector you discovered
   ✅ Only after printing Helium element HTML confirmed the pattern

════════════════════════════════════════════════════════════════════════════
🔍 CRITICAL: HELIUM EXPLORATION PHASE (BEFORE ANY JAVASCRIPT!)
════════════════════════════════════════════════════════════════════════════

JAVASCRIPT IS FOR EXTRACTION, NOT EXPLORATION!
❌ NEVER use JavaScript to discover what's on the page
✅ ALWAYS use Helium to get elements first, then inspect their HTML

THE EXPLORATION WORKFLOW:

1. LOOK at screenshot → Identify 3-5 pieces of text you can see in your target area
   (Examples: names, titles, product names, etc.)

2. USE find_all() → Get the actual Helium elements for that text
   <code>
   from helium import find_all, Text
   elements = find_all(Text("visible text here"))
   print(f"Found {len(elements)} elements")
   </code>

3. PRINT element HTML → See the actual structure
   <code>
   driver = get_driver()
   if len(elements) > 0:
       html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
       print(html[:500])  # Print first 500 chars
   </code>

4. OBSERVE the pattern → What tags, classes, or structure do you see?

5. TRY MULTIPLE items → Get elements for 2-3 different visible texts to confirm pattern
   <code>
   for text_to_find in ["first item", "second item", "third item"]:
       elements = find_all(Text(text_to_find))
       if len(elements) > 0:
           html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
           print(f"\n{text_to_find}: {html[:300]}")
   </code>

6. BUILD selector → Based on the HTML you observed from Helium elements

WHY THIS WORKS:
- Helium finds elements by VISIBLE TEXT (what you see in screenshot)
- Printing element HTML shows you the ACTUAL structure
- You discover selectors from REAL elements, not guesses
- No assumptions about class names or structure

════════════════════════════════════════════════════════════════════════════
📋 THE STEP-BY-STEP CHECKLIST (DO THESE IN ORDER, ONE AT A TIME!)
════════════════════════════════════════════════════════════════════════════

EXTRACTING FROM ANY LIST - Follow these exact steps:

STEP 1: Verify target area is visible
Look at screenshot. Is your target area (modal, list, table, etc.) visible?
Identify ONE piece of text that confirms it's there.
<code>
from helium import find_all, Text
elements = find_all(Text("text you can see"))
print(f"Found {len(elements)} elements")
</code>
→ STOP. Did it find elements? If yes, continue.

STEP 2: Identify 3-5 pieces of text in your target area
Look at the screenshot. Write down 3-5 pieces of text you can SEE in the area you want to extract from.
These should be items from your list (names, products, titles, etc.)
→ Write these down. You'll get their HTML next.

STEP 3: Get Helium elements for the FIRST item and print its HTML
<code>
from helium import find_all, Text
driver = get_driver()

elements = find_all(Text("first item text"))
print(f"Found {len(elements)} elements")

if len(elements) > 0:
    html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
    print(html[:500])
</code>
→ STOP. Look at the printed HTML. What tag is it? What classes/attributes?

STEP 4: Get Helium elements for 2-3 MORE items to confirm the pattern
<code>
from helium import find_all, Text
driver = get_driver()

items_to_check = ["second item text", "third item text"]
for item_text in items_to_check:
    elements = find_all(Text(item_text))
    if len(elements) > 0:
        html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
        print(f"\n{item_text}:")
        print(html[:300])
</code>
→ STOP. Compare the HTML from all items. What's the common pattern?

STEP 5: Identify the parent container (if needed)
<code>
from helium import find_all, Text
driver = get_driver()

elements = find_all(Text("first item text"))
if len(elements) > 0:
    parent_html = driver.execute_script("return arguments[0].parentElement.outerHTML;", elements[0].web_element)
    print(parent_html[:500])
</code>
→ STOP. Does the parent have a useful structure? Classes? Attributes?

STEP 6: Based on what you OBSERVED, create a selector and test on ONE
Based on the HTML you saw in Steps 3-5, create a querySelector.
<code>
driver = get_driver()
test = driver.execute_script('''
    const el = document.querySelector('YOUR_SELECTOR_HERE');
    return el ? el.outerHTML.slice(0, 200) : null;
''')
print(test)
</code>
→ STOP. Did it find the right element?

STEP 7: Extract ALL with querySelectorAll
<code>
driver = get_driver()
all_data = driver.execute_script('''
    return Array.from(document.querySelectorAll('YOUR_SELECTOR_HERE')).map(el => ({
        text: el.textContent.trim()
    }));
''')
print(f"Found {len(all_data)} items")
print(all_data[:5])
</code>
→ STOP. Check the count and sample data.

STEP 8: Return structured results
<code>
final_answer({
    "status": "success",
    "data": all_data,
    "count": len(all_data)
})
</code>

EXTRACTING FROM MULTIPLE PAGES - Follow this pattern:

FOR EACH URL (one at a time):
  STEP 1: Navigate
  <code>
  from helium import go_to
  import time
  go_to(url)
  time.sleep(2)
  </code>

  STEP 2: Confirm page loaded
  <code>
  from helium import find_all, Text
  elements = find_all(Text("text confirming page loaded"))
  print(f"Found {len(elements)} elements")
  </code>

  STEP 3: On FIRST URL only - discover structure (Steps 3-5 from above)

  STEP 4: On remaining URLs - use same selector from first URL

════════════════════════════════════════════════════════════════════════════
🚫 ANTI-PATTERNS (NEVER DO THESE!)
════════════════════════════════════════════════════════════════════════════

❌ LONG CODE BLOCKS (>5 lines with multiple actions)
   Example of what NOT to do:
   <code>
   # DON'T: 80 lines that open modal, find scrollable container, scroll loop, extract
   </code>

❌ WHILE LOOPS THAT SCROLL AUTOMATICALLY
   <code>
   # DON'T: while True: scroll, extract, check count, etc.
   </code>

❌ USING JAVASCRIPT TO FIND ELEMENTS
   Example of what NOT to do:
   <code>
   # DON'T: Use JavaScript to search for elements
   result = driver.execute_script('''
       const walker = document.createTreeWalker(...);
       while (walker.nextNode()) { ... }
   ''')
   </code>

   RIGHT: Use Helium to find by visible text, then print HTML
   <code>
   # DO: Use Helium to get elements by visible text
   from helium import find_all, Text
   driver = get_driver()

   elements = find_all(Text("some text"))
   if len(elements) > 0:
       html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
       print(html[:500])
   </code>

❌ CHECKING ONLY ONE ITEM
   Don't get HTML for just one item - you need to verify the pattern!
   <code>
   # DON'T: Only check one item
   elements = find_all(Text("first item"))
   # ... print and assume pattern
   </code>

   RIGHT: Check 3-5 items to confirm pattern
   <code>
   # DO: Check multiple items
   for text in ["item1", "item2", "item3"]:
       elements = find_all(Text(text))
       if len(elements) > 0:
           html = driver.execute_script("return arguments[0].outerHTML;", elements[0].web_element)
           print(f"{text}: {html[:300]}")
   </code>

❌ ASSUMING CLASS NAMES OR SELECTORS
   <code>
   # DON'T: Assume selectors without observing
   document.querySelector('.specific-class-name')
   </code>

❌ TRYING TO FIND SCROLLABLE CONTAINERS
   <code>
   # DON'T: Scripts that detect overflow, find scrollable parents, etc.
   </code>

❌ CODE BLOCKS THAT DO MULTIPLE STEPS AT ONCE
   <code>
   # DON'T: navigate, click, extract, format, return all in one block
   </code>

════════════════════════════════════════════════════════════════════════════
📐 CODE BLOCK TEMPLATE (EVERY BLOCK MUST FOLLOW THIS!)
════════════════════════════════════════════════════════════════════════════

MAXIMUM ALLOWED STRUCTURE (5 lines):

<code>
# Line 1: import if needed (or skip)
# Lines 2-3: ONE action only
# Line 4: print result
# Line 5: (optional) brief status message
</code>

THEN STOP. Wait for screenshot. Observe. Plan next small step.

Example of a GOOD code block:
<code>
from helium import Text
if Text("Guests").exists():
    print("✅ Modal is open")
</code>

Example of a BAD code block:
<code>
# 80 lines of code trying to do everything...
</code>

════════════════════════════════════════════════════════════════════════════
🎯 QUICK DECISION TREE
════════════════════════════════════════════════════════════════════════════

Question: "How do I find elements on the page?"
→ Look at screenshot → Identify visible text
→ Use: find_all(Text("visible text"))
→ Print: element.outerHTML via execute_script
→ Do NOT use: querySelector, TreeWalker, or DOM traversal

Question: "How do I figure out what selector to use?"
→ Get 3-5 Helium elements by visible text
→ Print their HTML
→ Observe the common pattern
→ Build selector from what you observed

Question: "When do I use JavaScript querySelector?"
→ ONLY for final extraction with querySelectorAll
→ ONLY after Helium elements showed you the pattern
→ NEVER for exploration or discovery

════════════════════════════════════════════════════════════════════════════
🎯 QUICK REFERENCE
════════════════════════════════════════════════════════════════════════════

REMEMBER:
→ Small code blocks (3-5 lines)
→ One action at a time
→ Observe screenshot after EVERY action
→ Use Helium find_all() to GET elements by visible text
→ Print element HTML to discover structure
→ Check 3-5 items to confirm pattern
→ NO scrolling for modals (HTML already loaded!)
→ JavaScript for EXTRACTION only, not exploration
→ Test on ONE before extracting ALL
→ ALWAYS use <code>...</code> tags (never ```)

════════════════════════════════════════════════════════════════════════════
📦 STRUCTURED OUTPUT FORMAT
════════════════════════════════════════════════════════════════════════════

When calling final_answer(), ALWAYS return a structured dictionary:

SUCCESS:
<code>
final_answer({
    "status": "success",
    "data": [...],
    "count": len(data)
})
</code>

ERROR:
<code>
final_answer({
    "status": "error",
    "error": "Description of what went wrong"
})
</code>

Return ERROR status when:
- Cannot find elements after exploration
- Selectors return 0 results
- Page fails to load or unexpected structure

Return SUCCESS status when:
- Extraction completed (even if count=0)
- Data structure is valid
"""

    # Load visual code agent prompt templates (enforces Visual → Thought → Code pattern)
    default_templates = yaml.safe_load(
        importlib.resources.files("smolagents.prompts").joinpath("visual_code_agent.yaml").read_text()
    )

    # Override managed_agent report template to output raw JSON (no prefix message)
    # This allows the parent agent to parse the response with simple json.loads()
    default_templates["managed_agent"]["report"] = "{{final_answer}}"

    # Override managed_agent task template to enforce structured output
    # This ensures that when called as a managed agent by a parent agent,
    # it receives clear instructions to return structured output
    default_templates["managed_agent"]["task"] = """You're a helpful agent named '{{name}}'.
You have been submitted this task by your manager.
---
Task:
{{task}}
---

⚠️ CRITICAL: STRUCTURED OUTPUT REQUIRED ⚠️

You MUST return your result using final_answer() with a structured dictionary.
NEVER return plain lists, strings, or unstructured data.

REQUIRED FORMAT - Choose ONE based on outcome:

SUCCESS (when extraction succeeds):
final_answer({
    "status": "success",
    "data": [...],      # Your extracted list of items
    "count": <number>   # Number of items extracted
})

ERROR (when extraction fails):
final_answer({
    "status": "error",
    "error": "<detailed error description>"
})

EXAMPLES:

✅ CORRECT - Successful extraction:
final_answer({
    "status": "success",
    "data": [{"name": "John", "url": "..."}, {"name": "Jane", "url": "..."}],
    "count": 2
})

✅ CORRECT - Error case:
final_answer({
    "status": "error",
    "error": "Could not find elements matching selector after trying 5 different approaches"
})

❌ WRONG - Do NOT do this:
final_answer([...])  # Missing status structure
final_answer("Here are the results...")  # Plain string

Everything you pass to final_answer() will be returned to your manager.
Provide detailed, complete information in the structured format above."""

    # Create the managed agent with instructions
    extraction_agent = CodeAgent(
        tools=[],  # No additional tools needed
        model=model,
        prompt_templates=default_templates,  # Use modified templates with structured output enforcement
        additional_authorized_imports=["helium", "time", "json"],  # Allow helium, time, and json for parsing
        planning_interval=5,
        max_steps=15,  # Increased for multi-page enrichment workflow (can process many profiles)
        verbosity_level=2,  # Show detailed logs
        name="list_extraction",  # REQUIRED for managed agents
        description="Master agent for TEXT-FIRST web data extraction. Always grounds extraction in VISIBLE TEXT from screenshots, never guesses at CSS selectors or DOM structure. Uses TreeWalker to find text nodes, then traverses up to discover actual HTML patterns. Specializes in extracting structured lists and enriching data across multiple pages.",  # REQUIRED for managed agents
        instructions=LIST_EXTRACTION_INSTRUCTIONS,  # CRITICAL: Include instructions in system prompt
    )

    # Pre-load helium using shared utility
    from agents.utils import preload_helium

    preload_helium(extraction_agent)

    # Apply validation wrapper if requested
    if validate_output:
        # Store original run method
        original_run = extraction_agent.run

        def validated_run(task, **kwargs):
            """Wraps agent.run() with output validation and JSON serialization."""
            import json
            result = original_run(task, **kwargs)
            validated = validate_list_extraction_response(result)
            # Serialize to JSON so parent can use json.loads() directly
            return json.dumps(validated)

        # Replace run method with validated version
        extraction_agent.run = validated_run

    return extraction_agent


def create_list_extraction_task(description: str, count: str = None) -> str:
    """
    Create a simple, generic task prompt for the list extraction agent.

    The agent will return a structured response:
    - Success: {"status": "success", "data": [...], "count": N}
    - Error: {"status": "error", "error": "message"}

    Args:
        description: What to extract (e.g., "names and Luma profile URLs of the guests")
        count: Expected count if known (e.g., "48") - helps agent validate extraction

    Returns:
        Task string for the agent
    """
    count_hint = f" (expected: {count})" if count else ""

    task = f"""
Extract the {description}{count_hint}.

The agent will use its strategic exploration workflow to find and extract the data.
"""
    return task
