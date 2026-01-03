"""
Debug IMS Login Page Structure
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

IMS_BASE_URL = os.getenv("IMS_BASE_URL")

def debug_login_page():
    """Open login page and capture its structure"""
    with sync_playwright() as p:
        # Launch browser (visible)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"Opening: {IMS_BASE_URL}")
        page.goto(IMS_BASE_URL, wait_until="networkidle")

        # Wait a bit for page to fully load
        page.wait_for_timeout(2000)

        # Take screenshot
        screenshot_path = "debug_login_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n[OK] Screenshot saved: {screenshot_path}")

        # Get page title
        title = page.title()
        print(f"[OK] Page Title: {title}")

        # Get current URL
        current_url = page.url
        print(f"[OK] Current URL: {current_url}")

        # Check for login form elements
        print("\n=== Checking for login form elements ===")

        # Check various possible selectors
        selectors_to_check = [
            ('input[name="userId"]', 'User ID input (name="userId")'),
            ('input[name="username"]', 'Username input (name="username")'),
            ('input[name="id"]', 'ID input (name="id")'),
            ('input[type="text"]', 'Text inputs'),
            ('input[type="password"]', 'Password inputs'),
            ('input[name="password"]', 'Password input (name="password")'),
            ('input[name="passwd"]', 'Password input (name="passwd")'),
            ('button[type="submit"]', 'Submit buttons'),
            ('input[type="submit"]', 'Submit inputs'),
            ('form', 'Forms on page'),
        ]

        for selector, description in selectors_to_check:
            try:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    print(f"[FOUND] {count} element(s): {description}")
                    # Get details of first element
                    if count > 0:
                        first = elements.first
                        try:
                            attrs = {}
                            for attr in ['id', 'name', 'type', 'class', 'placeholder']:
                                val = first.get_attribute(attr)
                                if val:
                                    attrs[attr] = val
                            if attrs:
                                print(f"  First element attributes: {attrs}")
                        except:
                            pass
                else:
                    print(f"[NOT FOUND] {description}")
            except Exception as e:
                print(f"[ERROR] checking {description}: {e}")

        # Get all input elements
        print("\n=== All Input Elements ===")
        all_inputs = page.locator("input").all()
        for i, input_elem in enumerate(all_inputs):
            try:
                attrs = {
                    'tag': 'input',
                    'type': input_elem.get_attribute('type') or 'text',
                    'name': input_elem.get_attribute('name') or '(no name)',
                    'id': input_elem.get_attribute('id') or '(no id)',
                    'class': input_elem.get_attribute('class') or '(no class)',
                    'placeholder': input_elem.get_attribute('placeholder') or ''
                }
                print(f"Input #{i+1}: {attrs}")
            except Exception as e:
                print(f"Input #{i+1}: Error - {e}")

        # Get HTML of the body (first 5000 chars)
        print("\n=== Page HTML (first 5000 chars) ===")
        try:
            html_content = page.content()
            print(html_content[:5000])

            # Save full HTML
            html_path = "debug_login_page.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n[OK] Full HTML saved: {html_path}")
        except Exception as e:
            print(f"Error getting HTML: {e}")

        print("\n=== Debug session complete ===")
        print("Press Enter to close browser...")
        input()

        browser.close()

if __name__ == "__main__":
    debug_login_page()
