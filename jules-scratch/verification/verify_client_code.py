import re
from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. Log in
    page.goto("http://127.0.0.1:8000/accounts/login/")
    page.get_by_label("メールアドレス").fill("testuser")
    page.get_by_label("パスワード").fill("testpassword")
    page.get_by_role("button", name="ログイン").click()

    # Wait for navigation to the profile page, which indicates successful login
    expect(page).to_have_url("http://127.0.0.1:8000/accounts/profile/")

    # 2. Navigate to the client list
    page.goto("http://127.0.0.1:8000/client/")

    # 3. Find a client and navigate to its detail page
    # We'll click on the first client in the list.
    # The sample data should create clients, so we expect at least one.
    first_client_link = page.get_by_role("row").nth(1).get_by_role("link").first

    # Get the client name to use in the screenshot filename
    client_name_text = first_client_link.inner_text()

    first_client_link.click()

    # 4. Verify we are on the detail page and take a screenshot
    expect(page.get_by_role("heading", name=re.compile(client_name_text))).to_be_visible()

    # Check for the client code's presence
    expect(page.get_by_text(re.compile("クライアントコード"))).to_be_visible()

    page.screenshot(path="jules-scratch/verification/verification.png")

    # Clean up
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)