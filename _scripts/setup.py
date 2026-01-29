#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
開発環境セットアップスクリプト
データベースのリセット、スーパーユーザーの作成、サンプルデータのインポートを自動で行います。
"""
import os
import sys
import subprocess
from sample_data_config import SAMPLE_DATA_FILES

def run_command(command, description, env=None):
    """コマンドを実行し、結果を表示"""
    print(f"\n{description}")
    print(f"実行中: {command}")
    # 標準の環境変数を引き継ぎ、指定された環境変数を追加
    new_env = os.environ.copy()
    if env:
        new_env.update(env)

    result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', env=new_env)

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

def reset_database():
    """データベースをリセットし、マイグレーションを適用"""
    print("🔄 [1/4] データベースをリセットします...")

    # 1. データベースファイルを削除
    if os.path.exists('db.sqlite3'):
        try:
            os.remove('db.sqlite3')
            print("✅ db.sqlite3を削除しました")
        except PermissionError:
            print("❌ db.sqlite3が使用中です。開発サーバーやDBブラウザを終了してから再実行してください。")
            return False
        except Exception as e:
            print(f"❌ db.sqlite3の削除でエラーが発生しました: {e}")
            return False
    else:
        print("ℹ️ db.sqlite3は存在しません")

    # 2. マイグレーションを適用
    if not run_command("python manage.py migrate", "データベースマイグレーションの適用"):
        return False

    print("✅ [1/4] データベースのリセットが完了しました。")
    return True

def create_superuser():
    """スーパーユーザーを作成"""
    print("\n👤 [2/4] スーパーユーザーを作成します...")

    # 環境変数を設定
    superuser_env = {'DJANGO_SUPERUSER_PASSWORD': 'passwordforstudybase!'}

    # スーパーユーザー作成コマンドを実行
    command = "python manage.py createsuperuser --noinput --username admin --email admin@example.com"
    if not run_command(command, "スーパーユーザー (admin / admin@example.com) の作成", env=superuser_env):
        return False

    print("✅ [2/4] スーパーユーザーの作成が完了しました。")
    return True

def load_sample_data():
    """サンプルデータをインポート"""
    print("\n📊 [3/4] サンプルデータをインポートします...")

    # サンプルデータファイルの存在確認
    missing_files = [fp for fp, _ in SAMPLE_DATA_FILES if not os.path.exists(fp)]
    if missing_files:
        print("❌ 以下のサンプルデータファイルが見つかりません:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False

    # サンプルデータを順次読み込み
    for file_path, description in SAMPLE_DATA_FILES:
        if "group_permissions.json" in file_path:
            command = f"python manage.py import_group_permissions {file_path}"
        else:
            command = f"python manage.py loaddata {file_path}"

        if not run_command(command, description):
            return False

        # groups.json の直後にサンプルユーザーをインポート
        if "groups.json" in file_path:
            user_csv = "_sample_data/users.csv"
            if os.path.exists(user_csv):
                if not run_command(f"python manage.py import_users {user_csv}", "サンプルユーザーのインポート"):
                    return False

    print("✅ [3/4] サンプルデータのインポートが完了しました。")
    return True

def update_superuser_info():
    """スーパーユーザーの情報を更新"""
    print("\n✏️ [4/4] スーパーユーザーの情報を更新します...")

    command = "python manage.py update_superuser_info"
    if not run_command(command, "スーパーユーザーの姓名、メールアドレスを更新"):
        return False

    print("✅ [4/4] スーパーユーザーの情報の更新が完了しました。")
    return True

def main():
    """メイン処理"""
    print("🚀 開発環境のセットアップを開始します...")

    if not reset_database():
        sys.exit(1)

    if not create_superuser():
        sys.exit(1)

    if not load_sample_data():
        sys.exit(1)

    if not update_superuser_info():
        sys.exit(1)

    print("\n🎉 セットアップがすべて完了しました！")
    print("サーバーを起動するには、以下のコマンドを実行してください:")
    print("python manage.py runserver")

if __name__ == "__main__":
    main()
