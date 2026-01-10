#!/usr/bin/env python
"""
初期セットアップユーティリティ
データベースのリセット、スーパーユーザー作成、サンプルデータ読み込みを行う
"""

import os
import sys
import subprocess
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

# 共通設定をインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_scripts'))
from sample_data_config import SAMPLE_DATA_FILES


# タスク管理用のグローバル辞書（本番環境ではRedisなどを使用すべき）
SETUP_TASKS: Dict[str, Dict[str, Any]] = {}


class SetupTask:
    """セットアップタスクの管理クラス"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = 'pending'  # pending, processing, completed, failed
        self.progress = 0
        self.total = 0
        self.current_step = ''
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.imported_count = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """タスク情報を辞書形式で返す"""
        elapsed_time = 0
        estimated_time_remaining = 0
        
        if self.start_time:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            
            if self.total > 0 and self.progress > 0:
                avg_time_per_item = elapsed_time / self.progress
                remaining_items = self.total - self.progress
                estimated_time_remaining = avg_time_per_item * remaining_items
        
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'total': self.total,
            'current_step': self.current_step,
            'errors': self.errors,
            'imported_count': self.imported_count,
            'elapsed_time_seconds': int(elapsed_time),
            'estimated_time_remaining_seconds': int(estimated_time_remaining),
        }


def create_setup_task() -> str:
    """新しいセットアップタスクを作成し、タスクIDを返す"""
    task_id = str(uuid.uuid4())
    SETUP_TASKS[task_id] = SetupTask(task_id)
    return task_id


def get_setup_task(task_id: str) -> Optional[SetupTask]:
    """タスクIDからセットアップタスクを取得"""
    return SETUP_TASKS.get(task_id)


def run_command(command: str, description: str, task: SetupTask) -> bool:
    """コマンドを実行し、結果を返す"""
    print(f"\n{description}")
    print(f"実行中: {command}")
    
    task.current_step = description
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 成功")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print("❌ エラー")
        error_msg = f"{description}でエラーが発生しました"
        if result.stderr:
            print(result.stderr)
            error_msg += f": {result.stderr}"
        task.errors.append(error_msg)
        return False


def reset_database(task: SetupTask) -> bool:
    """データベースをリセット（データのみクリア、テーブル構造は維持）"""
    task.current_step = 'データベースをリセット中...'
    
    # サーバー起動中でも動作するように、flushコマンドでデータのみ削除
    # （テーブル構造は維持されるため、ミドルウェアのDBアクセスでエラーが発生しない）
    if not run_command("python manage.py flush --noinput", "データベースのデータをクリア", task):
        return False
    
    # 新しいマイグレーションがある場合に適用
    if not run_command("python manage.py migrate", "マイグレーションの適用", task):
        return False
    
    return True


def create_superuser(task: SetupTask) -> bool:
    """スーパーユーザーを作成"""
    task.current_step = 'スーパーユーザーを作成中...'
    
    # 環境変数を設定
    os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'passwordforstudybase!'
    
    command = 'python manage.py createsuperuser --noinput --username admin --email admin@test.com'
    if not run_command(command, "スーパーユーザーの作成", task):
        return False
    
    return True


def load_sample_data(task: SetupTask) -> bool:
    """サンプルデータを読み込む"""
    task.current_step = 'サンプルデータを読み込み中...'
    
    # ファイルの存在確認
    missing_files = []
    for file_path, _ in SAMPLE_DATA_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        error_msg = "以下のサンプルデータファイルが見つかりません: " + ", ".join(missing_files)
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        return False
    
    # 総ステップ数を設定（各ファイルのみ）
    task.total = len(SAMPLE_DATA_FILES)
    task.progress = 0
    
    # サンプルデータを順次読み込み
    for file_path, description in SAMPLE_DATA_FILES:
        command = f"python manage.py loaddata {file_path}"
        if not run_command(command, description, task):
            return False
        task.progress += 1
        task.imported_count += 1
        # データベースロックを軽減するため、短い待機時間を追加
        time.sleep(0.1)
    
    return True


def import_sample_users(task: SetupTask) -> bool:
    """サンプルユーザーをインポート"""
    task.current_step = 'サンプルユーザーをインポート中...'

    csv_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '_sample_data', 'users.csv')
    if not os.path.exists(csv_file_path):
        error_msg = f"サンプルユーザーファイルが見つかりません: {csv_file_path}"
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        return False

    command = f"python manage.py import_users {csv_file_path}"
    if not run_command(command, "サンプルユーザーのインポート", task):
        return False

    return True


def copy_sample_photos(task: SetupTask) -> bool:
    """サンプル画像をコピー"""
    task.current_step = 'サンプル画像をコピー中...'
    
    import shutil
    from django.conf import settings
    
    sample_photos_dir = os.path.join(settings.BASE_DIR, '_sample_data', 'staff_photos')
    target_photos_dir = os.path.join(settings.MEDIA_ROOT, 'staff_files')
    
    if not os.path.exists(sample_photos_dir):
        print(f"ℹ️ サンプル画像ディレクトリが見つからないためスキップします: {sample_photos_dir}")
        return True
    
    if not os.path.exists(target_photos_dir):
        os.makedirs(target_photos_dir)
        
    copied_count = 0
    try:
        for filename in os.listdir(sample_photos_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                src_path = os.path.join(sample_photos_dir, filename)
                # ファイル名は {id}.jpg であることを想定
                dst_path = os.path.join(target_photos_dir, filename)
                shutil.copy2(src_path, dst_path)
                copied_count += 1
        
        print(f"✅ {copied_count}枚のサンプル画像をコピーしました")
        return True
    except Exception as e:
        error_msg = f"画像のコピー中にエラーが発生しました: {e}"
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        return False


def copy_company_seals(task: SetupTask) -> bool:
    """会社印のサンプルファイルをコピー"""
    task.current_step = '会社印のサンプルファイルをコピー中...'
    
    import shutil
    from django.conf import settings
    
    sample_seals_dir = os.path.join(settings.BASE_DIR, '_sample_data', 'company_seals')
    target_seals_dir = os.path.join(settings.MEDIA_ROOT, 'company_seals')
    
    if not os.path.exists(sample_seals_dir):
        print(f"ℹ️ 会社印サンプルディレクトリが見つからないためスキップします: {sample_seals_dir}")
        return True
    
    if not os.path.exists(target_seals_dir):
        os.makedirs(target_seals_dir)
        
    copied_count = 0
    try:
        for filename in os.listdir(sample_seals_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                src_path = os.path.join(sample_seals_dir, filename)
                dst_path = os.path.join(target_seals_dir, filename)
                shutil.copy2(src_path, dst_path)
                copied_count += 1
        
        print(f"✅ {copied_count}個の会社印サンプルファイルをコピーしました")
        return True
    except Exception as e:
        error_msg = f"会社印ファイルのコピー中にエラーが発生しました: {e}"
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        return False


def execute_setup(task_id: str):
    """セットアップ処理を実行（別スレッドで実行される）"""
    task = get_setup_task(task_id)
    if not task:
        return
    
    task.status = 'processing'
    task.start_time = datetime.now()
    
    try:
        # 1. データベースリセット
        if not reset_database(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return
        
        # 2. スーパーユーザー作成
        if not create_superuser(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return
        
        # 3. スーパーユーザーの姓名、メールアドレスを更新
        command = "python manage.py update_superuser_info"
        if not run_command(command, "スーパーユーザーの姓名、メールアドレスを更新", task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return
        
        # 4. サンプルデータ読み込み
        if not load_sample_data(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return

        # 5. サンプルユーザーのインポート
        if not import_sample_users(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return

        # 6. サンプル画像のコピー
        if not copy_sample_photos(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return

        # 7. 会社印サンプルファイルのコピー
        if not copy_company_seals(task):
            task.status = 'failed'
            task.end_time = datetime.now()
            return
        
        # 成功
        task.status = 'completed'
        task.end_time = datetime.now()
        print("\n🎉 初期セットアップが完了しました！")
        
    except Exception as e:
        error_msg = f"セットアップ中に予期しないエラーが発生しました: {e}"
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        task.status = 'failed'
        task.end_time = datetime.now()


def start_setup_async(task_id: str):
    """セットアップを非同期で開始"""
    thread = threading.Thread(target=execute_setup, args=(task_id,))
    thread.daemon = True
    thread.start()
