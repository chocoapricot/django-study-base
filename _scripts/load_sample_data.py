#!/usr/bin/env python
"""
サンプルデータインポートスクリプト
正しい順序でサンプルデータをインポートします。
"""

import os
import sys
import subprocess

# 共通設定をインポート
from sample_data_config import SAMPLE_DATA_FILES


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
    missing_files = []
    for file_path, _ in SAMPLE_DATA_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 以下のサンプルデータファイルが見つかりません:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        sys.exit(1)
    
    # サンプルデータを順次読み込み
    for file_path, description in SAMPLE_DATA_FILES:
        command = f"python manage.py loaddata {file_path}"
        if not run_command(command, description):
            print(f"❌ {description}のインポートでエラーが発生しました")
            sys.exit(1)

    # スーパーユーザーの姓名を更新
    update_superuser_command = "python manage.py update_superuser_info"
    if not run_command(update_superuser_command, "スーパーユーザーの姓名、メールアドレスを更新"):
        print("❌ スーパーユーザーの更新でエラーが発生しました")
        sys.exit(1)
    
    print("\n🎉 サンプルデータのインポートが完了しました！")
    print("\n📈 インポートされたデータ:")
    for _, description in SAMPLE_DATA_FILES:
        print(f"- {description}")


if __name__ == "__main__":
    main()