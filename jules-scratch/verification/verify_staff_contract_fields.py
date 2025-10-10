import re
from playwright.sync_api import Page, expect

def test_staff_contract_new_fields(page: Page):
    # 1. ログイン
    page.goto("http://localhost:8000/accounts/login/")
    page.get_by_label("メールアドレス").fill("admin@example.com")
    page.get_by_label("パスワード").fill("password")
    page.get_by_role("button", name="ログイン").click()

    # ログイン後のダッシュボードにいることを確認
    expect(page.get_by_role("heading", name="ホーム")).to_be_visible()

    # 2. スタッフ契約詳細ページに移動 (サンプルデータのPK=1を使用)
    # まず編集ページに移動して値を設定
    contract_pk = 1
    page.goto(f"http://localhost:8000/contract/staff/{contract_pk}/update/")

    # 3. 新しいフィールドに値を入力
    work_location_text = "東京本社ビル 10F"
    business_content_text = "新規プロジェクトの要件定義と基本設計"

    page.get_by_label("就業場所").fill(work_location_text)
    page.get_by_label("業務内容").fill(business_content_text)

    # 4. 保存
    page.get_by_role("button", name="保存").click()

    # 5. 詳細ページにリダイレクトされたことを確認し、スクリーンショットを撮る
    expect(page).to_have_url(re.compile(f".*/contract/staff/{contract_pk}/$"))
    expect(page.get_by_role("heading", name=re.compile("スタッフ契約詳細"))).to_be_visible()

    # 新しいフィールドが表示されていることを確認
    expect(page.get_by_text(work_location_text)).to_be_visible()
    expect(page.get_by_text(business_content_text)).to_be_visible()

    page.screenshot(path="jules-scratch/verification/staff_contract_verification.png")