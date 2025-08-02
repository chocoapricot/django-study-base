#!/usr/bin/env python
"""
データベースリセットスクリプト
データベースを削除して、正しい順序でマイグレーションを適用します。
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
    print("🔄 データベースリセットを開始します...")
    
    # 1. データベースファイルを削除
    if os.path.exists('db.sqlite3'):
        try:
            os.remove('db.sqlite3')
            print("✅ db.sqlite3を削除しました")
        except PermissionError:
            print("❌ db.sqlite3が使用中です。開発サーバーやDBブラウザを終了してから再実行してください。")
            sys.exit(1)
        except Exception as e:
            print(f"❌ db.sqlite3の削除でエラーが発生しました: {e}")
            sys.exit(1)
    else:
        print("ℹ️ db.sqlite3は存在しません")
    
    # 2. マイグレーションを適用
    commands = [
        ("python manage.py migrate", "データベースマイグレーションの適用"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"❌ {description}でエラーが発生しました")
            sys.exit(1)
    
    print("\n🎉 データベースマイグレーションが完了しました！")
    print("\n次のステップ:")
    print("1. スーパーユーザーを作成: python manage.py createsuperuser")
    print("   ※サンプルデータが参照するため、ID=1のユーザーを作成してください")
    print("2. サンプルデータをインポート: python _scripts/load_sample_data.py")
    print("3. 開発サーバーを起動: python manage.py runserver")

if __name__ == "__main__":
    main()