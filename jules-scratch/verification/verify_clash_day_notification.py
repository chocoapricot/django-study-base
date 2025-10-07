import re
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # 1. Login
        page.goto("http://localhost:8000/accounts/login/")
        page.get_by_label("メールアドレス").fill("admin@example.com")
        page.get_by_label("パスワード").fill("password")
        page.get_by_role("button", name="ログイン").click()
        expect(page).to_have_url("http://localhost:8000/")

        # 2. Navigate to contract detail page
        contract_id = 6  # 承認済みの派遣契約
        page.goto(f"http://localhost:8000/contract/client/{contract_id}/detail/")

        # 3. Verify initial state
        notification_switch = page.locator("#issueClashDayNotificationSwitch")
        notification_label = page.locator("label[for='issueClashDayNotificationSwitch']")

        expect(notification_switch).not_to_be_checked()
        expect(notification_switch).to_be_enabled()
        expect(notification_label).not_to_contain_text("（") # Initially no date/user info

        # 4. Click the switch to issue the notification
        # Handle the confirmation dialog
        page.on("dialog", lambda dialog: dialog.accept())
        notification_switch.click()

        # 5. Verify final state after reload
        expect(page).to_have_url(f"http://localhost:8000/contract/client/{contract_id}/detail/")

        # Re-locate elements after page reload
        notification_switch = page.locator("#issueClashDayNotificationSwitch")
        notification_label = page.locator("label[for='issueClashDayNotificationSwitch']")

        expect(notification_switch).to_be_checked()
        expect(notification_switch).to_be_enabled() # Should still be enabled for re-issue

        # Check for the date and user info
        # Example: (2025/10/07 10:00:00　Admin)
        expect(notification_label).to_contain_text(re.compile(r"（\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}　Admin）"))

        # 6. Take screenshot
        page.screenshot(path="jules-scratch/verification/verification.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)