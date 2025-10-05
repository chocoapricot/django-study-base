import re
from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # ログイン
    page.goto("http://localhost:8000/accounts/login/")
    page.get_by_label("メールアドレス").fill("admin@example.com")
    page.get_by_label("パスワード").fill("password")
    page.get_by_role("button", name="ログイン").click()
    expect(page).to_have_url("http://localhost:8000/")

    # 契約種別選択ページへ
    page.goto("http://localhost:8000/contract/client/create/?client_contract_type_code=10")

    # クライアント選択
    page.get_by_role("button", name="選択").click()
    # モーダルが表示されるのを待つ
    expect(page.get_by_role("heading", name="クライアント選択")).to_be_visible()
    # 最初のクライアントを選択
    page.locator('.modal-body a.list-group-item').first.click()
    # モーダルが閉じるのを待つ
    expect(page.get_by_role("heading", name="クライアント選択")).not_to_be_visible()


    # フォームのスクリーンショット
    page.screenshot(path="jules-scratch/verification/01_form_view.png")

    # フォーム入力
    page.get_by_label("契約名").fill("請求単位テスト契約")
    page.get_by_label("職種").select_option(label="エンジニア")
    page.get_by_label("契約パターン").select_option(label="クライアント向け基本契約")
    page.get_by_label("契約開始日").fill("2025-10-01")
    page.get_by_label("契約終了日").fill("2026-09-30")
    page.get_by_label("契約金額").fill("1000000")
    page.get_by_label("請求単位").select_option(label="月額")
    page.get_by_label("契約内容").fill("請求単位のテスト")

    # 保存
    page.get_by_role("button", name="保存").click()

    # 詳細ページの表示を待つ
    expect(page.get_by_role("heading", name="クライアント契約詳細")).to_be_visible()

    # 詳細ページの金額表示を確認
    amount_element = page.locator("th:has-text('契約金額') + td")
    expect(amount_element).to_contain_text("¥1,000,000")
    expect(amount_element).to_contain_text("/ 月額")

    # 詳細ページのスクリーンショット
    page.screenshot(path="jules-scratch/verification/02_detail_view.png")

    # 一覧ページへ移動
    page.get_by_role("link", name="戻る").click()
    expect(page.get_by_role("heading", name="クライアント契約一覧")).to_be_visible()

    # 一覧ページの金額表示を確認
    list_amount_element = page.locator("tbody > tr").first.locator("td.text-end")
    expect(list_amount_element).to_contain_text("¥1,000,000")
    expect(list_amount_element).to_contain_text("/ 月額")

    # 一覧ページのスクリーンショット
    page.screenshot(path="jules-scratch/verification/03_list_view.png")


    # 後片付け
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)