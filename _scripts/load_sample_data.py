#!/usr/bin/env python
"""
サンプルデータインポートスクリプト
正しい順序でサンプルデータをインポートします。
"""

import os
import sys
import subprocess

def run_command(command, description):
    """コマンドを実行し、結果を表示"""
    print(f"\n{description}")
    print(f"実行中: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 成功")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ エラー")
        if result.stderr:
            print(result.stderr)
        return False
    return True

def main():
    print("📊 サンプルデータのインポートを開始します...")
    
    # サンプルデータファイルの存在確認
    sample_files = [
        "_sample_data/dropdowns.json",
        "_sample_data/parameters.json", 
        "_sample_data/menus.json",
        "_sample_data/master_qualifications.json",
        "_sample_data/master_skills.json",
        "_sample_data/master_employment_type.json",
        "_sample_data/master_bill_payment.json",
        "_sample_data/master_bill_bank.json",
        "_sample_data/master_bank.json",
        "_sample_data/master_bank_branch.json",
        "_sample_data/master_staff_agreement.json",
        "_sample_data/master_information.json",
        "_sample_data/master_mail_template.json",
        "_sample_data/master_job_category.json",
        "_sample_data/master_minimum_pay.json",
        "_sample_data/master_contract_pattern.json",
        "_sample_data/master_contract_terms.json",
        "_sample_data/master_business_content.json",
        "_sample_data/master_haken_responsibility_degree.json",
        "_sample_data/master_default_value.json",
        "_sample_data/master_client_regist_status.json",
        "_sample_data/master_staff_regist_status.json",
        "_sample_data/company.json",
        "_sample_data/company_department.json",
        "_sample_data/company_user.json",
        "_sample_data/staff.json",
        "_sample_data/staff_international.json",
        "_sample_data/staff_disability.json",
        "_sample_data/staff_contacted.json",
        "_sample_data/client.json",
        "_sample_data/client_department.json",
        "_sample_data/client_user.json",
        "_sample_data/client_contacted.json",
        "_sample_data/connect_client.json",
        "_sample_data/connect_staff.json",
        "_sample_data/contract_client.json",
        "_sample_data/contract_staff.json",
        "_sample_data/contract_client_haken.json"
    ]
    
    missing_files = []
    for file_path in sample_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 以下のサンプルデータファイルが見つかりません:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        sys.exit(1)
    
    # インポート順序（依存関係を考慮）
    import_commands = [
        ("python manage.py loaddata _sample_data/company.json", "会社データ"),
        ("python manage.py loaddata _sample_data/company_department.json", "部署データ"),
        ("python manage.py loaddata _sample_data/company_user.json", "自社担当者データ"),
        ("python manage.py loaddata _sample_data/dropdowns.json", "ドロップダウンデータ"),
        ("python manage.py loaddata _sample_data/parameters.json", "パラメータデータ"),
        ("python manage.py loaddata _sample_data/menus.json", "メニューデータ"),
        ("python manage.py loaddata _sample_data/master_qualifications.json", "資格マスタデータ"),
        ("python manage.py loaddata _sample_data/master_skills.json", "技能マスタデータ"),
        ("python manage.py loaddata _sample_data/master_employment_type.json", "雇用形態マスタデータ"),
        ("python manage.py loaddata _sample_data/master_bill_payment.json", "支払いサイトマスタデータ"),
        ("python manage.py loaddata _sample_data/master_bill_bank.json", "会社銀行マスタデータ"),
        ("python manage.py loaddata _sample_data/master_bank.json", "銀行マスタデータ"),
        ("python manage.py loaddata _sample_data/master_bank_branch.json", "銀行支店マスタデータ"),
        ("python manage.py loaddata _sample_data/master_staff_agreement.json", "スタッフ同意文言マスタデータ"),
        ("python manage.py loaddata _sample_data/master_information.json", "お知らせマスタデータ"),
        ("python manage.py loaddata _sample_data/master_mail_template.json", "メールテンプレートマスタデータ"),
        ("python manage.py loaddata _sample_data/master_job_category.json", "職種マスタデータ"),
        ("python manage.py loaddata _sample_data/master_minimum_pay.json", "最低賃金マスタデータ"),
        ("python manage.py loaddata _sample_data/master_contract_pattern.json", "契約書パターンマスタデータ"),
        ("python manage.py loaddata _sample_data/master_contract_terms.json", "契約文言マスタデータ"),
        ("python manage.py loaddata _sample_data/master_business_content.json", "業務内容マスタデータ"),
        ("python manage.py loaddata _sample_data/master_haken_responsibility_degree.json", "派遣責任の程度マスタデータ"),
        ("python manage.py loaddata _sample_data/master_default_value.json", "初期値マスタデータ"),
        ("python manage.py loaddata _sample_data/master_client_regist_status.json", "クライアント登録ステータスマスタデータ"),
        ("python manage.py loaddata _sample_data/master_staff_regist_status.json", "スタッフ登録ステータスマスタデータ"),
        ("python manage.py loaddata _sample_data/staff.json", "スタッフデータ"),
        ("python manage.py loaddata _sample_data/staff_international.json", "スタッフ外国籍情報データ"),
        ("python manage.py loaddata _sample_data/staff_disability.json", "スタッフ障害者情報データ"),
        ("python manage.py loaddata _sample_data/staff_contacted.json", "スタッフ連絡履歴データ"),
        ("python manage.py loaddata _sample_data/client.json", "クライアントデータ"),
        ("python manage.py loaddata _sample_data/client_department.json", "クライアント組織データ"),
        ("python manage.py loaddata _sample_data/client_user.json", "クライアント担当者データ"),
        ("python manage.py loaddata _sample_data/client_contacted.json", "クライアント連絡履歴データ"),
        ("python manage.py loaddata _sample_data/connect_client.json", "クライアント接続データ"),
        ("python manage.py loaddata _sample_data/connect_staff.json", "スタッフ接続データ"),
        ("python manage.py loaddata _sample_data/contract_client.json", "クライアント契約データ"),
        ("python manage.py loaddata _sample_data/contract_client_haken.json", "クライアント契約派遣データ"),
        ("python manage.py loaddata _sample_data/contract_staff.json", "スタッフ契約データ")
    ]
    
    for command, description in import_commands:
        if not run_command(command, description):
            print(f"❌ {description}のインポートでエラーが発生しました")
            sys.exit(1)

    # スーパーユーザーの姓名を更新
    update_superuser_command = "python manage.py update_superuser_name"
    if not run_command(update_superuser_command, "スーパーユーザーの姓名を更新"):
        print("❌ スーパーユーザーの姓名更新でエラーが発生しました")
        sys.exit(1)
    
    print("\n🎉 サンプルデータのインポートが完了しました！")
    print("\n📈 インポートされたデータ:")
    print("- ドロップダウン選択肢")
    print("- システムパラメータ")
    print("- メニュー設定")
    print("- 資格マスタ")
    print("- 技能マスタ")
    print("- 雇用形態マスタ")
    print("- 支払いサイトマスタ")
    print("- 会社銀行マスタ")
    print("- 銀行マスタ")
    print("- 銀行支店マスタ")
    print("- お知らせマスタ")
    print("- メールテンプレートマスタ")
    print("- 職種マスタ")
    print("- 最低賃金マスタ")
    print("- 契約書パターンマスタ")
    print("- 契約文言マスタ")
    print("- 業務内容マスタ")
    print("- 派遣責任の程度マスタ")
    print("- 初期値マスタ")
    print("- クライアント登録ステータスマスタ")
    print("- スタッフ登録ステータスマスタ")
    print("- 会社データ")
    print("- 部署データ")
    print("- 自社担当者データ")
    print("- スタッフデータ")
    print("- スタッフ外国籍情報")
    print("- スタッフ障害者情報")
    print("- スタッフ連絡履歴")
    print("- クライアントデータ")
    print("- クライアント組織データ")
    print("- クライアント担当者データ")
    print("- クライアント連絡履歴")
    print("- クライアント接続データ")
    print("- スタッフ接続データ")
    print("- クライアント契約データ")
    print("- クライアント契約派遣データ")
    print("- スタッフ契約データ")

if __name__ == "__main__":
    main()