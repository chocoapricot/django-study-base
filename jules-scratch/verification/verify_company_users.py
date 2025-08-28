import re
from playwright.sync_api import sync_playwright, Page, expect

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Login
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.get_by_label("Login").fill("testuser")
        page.get_by_label("Password").fill("testpass123")
        page.get_by_role("button", name="Sign In").click()

        # Go to company detail page
        page.goto("http://127.0.0.1:8000/company/")

        # Wait for the page to load and check for the title
        expect(page).to_have_title(re.compile("会社情報"))

        # Take a screenshot
        page.screenshot(path="jules-scratch/verification/verification.png")

        browser.close()

if __name__ == '__main__':
    main()
