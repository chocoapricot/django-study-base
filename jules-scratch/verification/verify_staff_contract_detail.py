import re
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in
    page.goto("http://localhost:8000/accounts/login/")
    page.get_by_label("メールアドレス").fill("admin")
    page.get_by_label("パスワード").fill("admin")
    page.get_by_role("button", name="ログイン").click()
    page.wait_for_url("http://localhost:8000/staff/")

    # Go to staff list and create a new staff
    page.goto("http://localhost:8000/staff/")
    page.get_by_role("link", name="新規登録").click()
    page.get_by_label("姓").fill("Test")
    page.get_by_label("名").fill("User")
    page.get_by_label("メールアドレス").fill("testuser@example.com")
    page.get_by_role("button", name="登録").click()

    # Get the staff ID from the URL
    staff_id_match = re.search(r"/staff/detail/(\d+)/", page.url)
    staff_id = staff_id_match.group(1)

    # Create a staff contract
    page.goto(f"http://localhost:8000/contract/staff/create/?staff={staff_id}")
    page.get_by_label("契約名").fill("Test Contract")
    page.get_by_label("契約パターン").select_option("1")
    page.get_by_label("契約開始日").fill("2025-01-01")
    page.get_by_role("button", name="登録").click()

    # Get the contract ID from the URL
    contract_id_match = re.search(r"/contract/staff/(\d+)/", page.url)
    contract_id = contract_id_match.group(1)

    # Go to the staff contract detail page
    page.goto(f"http://localhost:8000/contract/staff/{contract_id}/")

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)