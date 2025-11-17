"""
Shared Browser Driver Utilities
================================
Reusable utilities for browser automation with Selenium and Helium.

Provides:
- Chrome initialization with anti-detection measures
- Session reuse via remote debugging protocol
- Screenshot capture for agent workflows
- Connection to existing Chrome sessions

Used by: luma_events_with_login.py, list_extraction_agent.py, google_login_agent.py
"""

from io import BytesIO
from time import sleep

import helium
import PIL.Image
from selenium import webdriver

from smolagents import CodeAgent
from smolagents.agents import ActionStep


def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    """
    Callback that captures a screenshot after each agent action.
    Handles window switching gracefully when windows close (e.g., OAuth popups).

    Args:
        memory_step: The agent's action step to attach screenshot to
        agent: The agent instance (unused but required by callback signature)
    """
    sleep(1.5)  # Wait for dynamic content to load
    driver = helium.get_driver()

    if driver is None:
        memory_step.observations = "⚠️ ERROR: No browser driver available"
        return

    # Try to capture screenshot from current window
    try:
        png_bytes = driver.get_screenshot_as_png()
    except Exception:
        # Window closed (e.g., OAuth popup) - switch to first available window
        handles = driver.window_handles
        if not handles:
            memory_step.observations = "⚠️ ERROR: All browser windows have been closed"
            return

        driver.switch_to.window(handles[0])
        try:
            png_bytes = driver.get_screenshot_as_png()
        except Exception as e:
            memory_step.observations = f"⚠️ ERROR: Cannot capture screenshot: {e}"
            return

    # Store screenshot in agent memory
    image = PIL.Image.open(BytesIO(png_bytes))
    memory_step.observations_images = [image.copy()]
    print(f"📸 Captured screenshot: {image.size} pixels")

    # Add current URL to observations
    url_info = f"Current URL: {driver.current_url}"
    memory_step.observations = (
        url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
    )


def is_chrome_running_on_port(port):
    """
    Check if Chrome is running with remote debugging on specified port.

    Args:
        port: Port number to check (e.g., 9222)

    Returns:
        True if Chrome is accessible on the port, False otherwise
    """
    try:
        import requests

        response = requests.get(f"http://localhost:{port}/json/version", timeout=0.5)
        return response.status_code == 200
    except Exception:
        return False


def connect_to_existing_chrome(port=9222):
    """
    Connect to existing Chrome instance via remote debugging.

    Args:
        port: Remote debugging port (default: 9222)

    Returns:
        WebDriver connected to existing Chrome session

    Raises:
        Exception: If connection fails
    """
    chrome_options = webdriver.ChromeOptions()

    # Connect to existing Chrome session via debugging port
    chrome_options.add_experimental_option("debuggerAddress", f"localhost:{port}")

    # Create driver connected to existing session
    driver = webdriver.Chrome(options=chrome_options)

    # Tell helium to use this driver
    helium.set_driver(driver)

    # Apply same anti-detection JavaScript as in new sessions
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def initialize_browser():
    """
    Initialize Chrome browser with visible window for demo purposes.
    Configured to avoid CAPTCHA detection by appearing as a real user.
    Enables remote debugging on port 9222 for session reuse.

    Returns:
        WebDriver instance for the newly created Chrome session
    """
    chrome_options = webdriver.ChromeOptions()

    # Window configuration - larger window for better event viewing
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--window-size=1400,1200")
    chrome_options.add_argument("--window-position=0,0")
    chrome_options.add_argument("--disable-pdf-viewer")

    # Anti-detection measures to avoid CAPTCHAs
    # 1. Remove automation flags that websites detect
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # 2. Set realistic user agent (recent Chrome on macOS)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    # 3. Additional flags to appear more human-like
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")  # Sometimes helps with detection

    # 4. Enable remote debugging for session reuse
    # This allows reconnecting to the same Chrome instance in future script runs
    chrome_options.add_argument("--remote-debugging-port=9222")

    # headless=False makes the browser visible for the demo!
    driver = helium.start_chrome(headless=False, options=chrome_options)

    # 5. Execute JavaScript to remove webdriver property completely
    # This is a backup in case the flag wasn't fully removed
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def initialize_browser_with_reuse():
    """
    Initialize browser with option to reuse existing Chrome session.

    Checks for existing Chrome with remote debugging on port 9222.
    If found, prompts user to connect or start fresh.
    If not found, starts new Chrome with debugging enabled.

    Returns:
        WebDriver instance (either connected to existing or newly created)
    """
    port = 9222

    # Check for existing Chrome session with remote debugging
    if is_chrome_running_on_port(port):
        print("\n" + "=" * 80)
        print("🔍 EXISTING CHROME SESSION DETECTED")
        print("=" * 80)
        print(f"Found Chrome instance with remote debugging on port {port}")
        print()
        print("Benefits of connecting:")
        print("  • Skip re-authentication (already logged in)")
        print("  • Faster startup (browser already running)")
        print("  • Preserve session state (cookies, tabs, etc.)")
        print()

        response = input("Connect to existing session? (y/n): ").strip().lower()

        if response == 'y':
            print("\n🔗 Connecting to existing Chrome session...")
            try:
                driver = connect_to_existing_chrome(port)
                print(f"✅ Connected! Current URL: {driver.current_url}")
                print("=" * 80)
                print()
                return driver
            except Exception as e:
                print(f"❌ Failed to connect: {e}")
                print("Falling back to new Chrome session...")
                print()

    # Start new Chrome session with debugging enabled
    print("\n🌐 Starting new Chrome session...")
    print("💡 TIP: After this script finishes, keep the Chrome window open!")
    print("   Next time you run the script, you can reconnect to skip login.")
    print("=" * 80)
    print()

    return initialize_browser()


def require_existing_chrome(port=9222):
    """
    Connect to existing Chrome session (required - will not start new browser).

    This function is designed for scripts that should only work with an existing
    browser session, like list_extraction_agent.py which assumes the user has
    already navigated to the desired page.

    Args:
        port: Remote debugging port to check (default: 9222)

    Returns:
        WebDriver connected to existing Chrome session

    Raises:
        SystemExit: If no Chrome session found on the port
    """
    if not is_chrome_running_on_port(port):
        print("\n" + "=" * 80)
        print("❌ ERROR: No Chrome session found")
        print("=" * 80)
        print(f"Could not find Chrome with remote debugging on port {port}")
        print()
        print("This script requires an existing Chrome session.")
        print("Please start Chrome with remote debugging first:")
        print()
        print('  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\')
        print('    --remote-debugging-port=9222 \\')
        print('    --user-data-dir=/tmp/chrome_debug_profile &')
        print()
        print("Then navigate to the page you want to extract data from,")
        print("and run this script again.")
        print("=" * 80)
        import sys
        sys.exit(1)

    print("\n🔗 Connecting to existing Chrome session...")
    try:
        driver = connect_to_existing_chrome(port)
        print(f"✅ Connected! Current URL: {driver.current_url}")
        print("=" * 80)
        print()
        return driver
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("=" * 80)
        import sys
        sys.exit(1)
