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
        "_sample_data/staff.json",
        "_sample_data/staff_contacted.json",
        "_sample_data/client.json",
        "_sample_data/client_contacted.json"
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
        ("python manage.py loaddata _sample_data/dropdowns.json", "ドロップダウンデータ"),
        ("python manage.py loaddata _sample_data/parameters.json", "パラメータデータ"),
        ("python manage.py loaddata _sample_data/menus.json", "メニューデータ"),
        ("python manage.py loaddata _sample_data/staff.json", "スタッフデータ"),
        ("python manage.py loaddata _sample_data/staff_contacted.json", "スタッフ連絡履歴データ"),
        ("python manage.py loaddata _sample_data/client.json", "クライアントデータ"),
        ("python manage.py loaddata _sample_data/client_contacted.json", "クライアント連絡履歴データ"),
    ]
    
    for command, description in import_commands:
        if not run_command(command, description):
            print(f"❌ {description}のインポートでエラーが発生しました")
            sys.exit(1)
    
    print("\n🎉 サンプルデータのインポートが完了しました！")
    print("\n📈 インポートされたデータ:")
    print("- ドロップダウン選択肢")
    print("- システムパラメータ")
    print("- メニュー設定")
    print("- スタッフデータ")
    print("- スタッフ連絡履歴")
    print("- クライアントデータ")
    print("- クライアント連絡履歴")

if __name__ == "__main__":
    main()