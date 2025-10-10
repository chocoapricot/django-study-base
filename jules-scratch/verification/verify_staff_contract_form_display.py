import re
from playwright.sync_api import Page, expect

def test_staff_contract_form_display(page: Page):
    # 1. ログイン
    page.goto("http://localhost:8000/accounts/login/")
    page.get_by_label("メールアドレス").fill("admin@example.com")
    page.get_by_label("パスワード").fill("password")
    page.get_by_role("button", name="ログイン").click()

    # ログイン後のダッシュボードにいることを確認
    expect(page.get_by_role("heading", name="ホーム")).to_be_visible()

    # 2. スタッフ契約編集ページに移動 (サンプルデータのPK=1を使用)
    contract_pk = 1
    page.goto(f"http://localhost:8000/contract/staff/{contract_pk}/update/")

    # 3. 新しいフィールドのラベルが表示されていることを確認
    expect(page.get_by_label("就業場所")).to_be_visible()
    expect(page.get_by_label("業務内容")).to_be_visible()

    # 4. スクリーンショットを撮る
    page.screenshot(path="jules-scratch/verification/staff_contract_form_display.png")