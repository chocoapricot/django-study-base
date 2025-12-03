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
    
    # サンプルデータファイルのリスト
    sample_files = [
        ("_sample_data/dropdowns.json", "ドロップダウンデータ"),
        ("_sample_data/parameters.json", "パラメータデータ"),
        ("_sample_data/master_user_parameter.json", "ユーザーパラメータマスタデータ"),
        ("_sample_data/menus.json", "メニューデータ"),
        ("_sample_data/master_qualifications.json", "資格マスタデータ"),
        ("_sample_data/master_skills.json", "技能マスタデータ"),
        ("_sample_data/master_bill_payment.json", "支払いサイトマスタデータ"),
        ("_sample_data/master_bill_bank.json", "会社銀行マスタデータ"),
        ("_sample_data/master_bank.json", "銀行マスタデータ"),
        ("_sample_data/master_bank_branch.json", "銀行支店マスタデータ"),
        ("_sample_data/master_staff_agreement.json", "スタッフ同意文言マスタデータ"),
        ("_sample_data/master_information.json", "お知らせマスタデータ"),
        ("_sample_data/master_mail_template.json", "メールテンプレートマスタデータ"),
        ("_sample_data/master_job_category.json", "職種マスタデータ"),
        ("_sample_data/master_minimum_pay.json", "最低賃金マスタデータ"),
        ("_sample_data/master_phrase_template_title.json", "汎用文言タイトルマスタデータ"),
        ("_sample_data/master_phrase_template.json", "汎用文言テンプレートマスタデータ"),
        ("_sample_data/master_default_value.json", "初期値マスタデータ"),
        ("_sample_data/master_client_regist_status.json", "クライアント登録ステータスマスタデータ"),
        ("_sample_data/master_staff_regist_status.json", "スタッフ登録ステータスマスタデータ"),
        ("_sample_data/master_worktime_pattern.json", "就業時間パターンマスタデータ"),
        ("_sample_data/master_worktime_pattern_work.json", "就業時間パターン勤務時間マスタデータ"),
        ("_sample_data/master_worktime_pattern_break.json", "就業時間パターン休憩時間マスタデータ"),
        ("_sample_data/master_overtime_pattern.json", "時間外算出パターンマスタデータ"),
        ("_sample_data/master_employment_type.json", "雇用形態マスタデータ"),
        ("_sample_data/master_contract_pattern.json", "契約書パターンマスタデータ"),
        ("_sample_data/master_contract_terms.json", "契約文言マスタデータ"),
        ("_sample_data/company.json", "会社データ"),
        ("_sample_data/company_department.json", "部署データ"),
        ("_sample_data/company_user.json", "自社担当者データ"),
        ("_sample_data/staff.json", "スタッフデータ"),
        ("_sample_data/staff_international.json", "スタッフ外国籍情報データ"),
        ("_sample_data/staff_disability.json", "スタッフ障害者情報データ"),
        ("_sample_data/staff_contacted.json", "スタッフ連絡履歴データ"),
        ("_sample_data/client.json", "クライアントデータ"),
        ("_sample_data/client_department.json", "クライアント組織データ"),
        ("_sample_data/client_user.json", "クライアント担当者データ"),
        ("_sample_data/client_contacted.json", "クライアント連絡履歴データ"),
        ("_sample_data/connect_client.json", "クライアント接続データ"),
        ("_sample_data/connect_staff.json", "スタッフ接続データ"),
        ("_sample_data/contract_client.json", "クライアント契約データ"),
        ("_sample_data/contract_client_haken.json", "クライアント契約派遣データ"),
        ("_sample_data/contract_staff.json", "スタッフ契約データ"),
        ("_sample_data/contract_assignment.json", "契約アサインメントデータ"),
    ]
    
    # ファイルの存在確認
    missing_files = []
    for file_path, _ in sample_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        error_msg = "以下のサンプルデータファイルが見つかりません: " + ", ".join(missing_files)
        print(f"❌ {error_msg}")
        task.errors.append(error_msg)
        return False
    
    # 総ステップ数を設定（各ファイルのみ）
    task.total = len(sample_files)
    task.progress = 0
    
    # サンプルデータを順次読み込み
    for file_path, description in sample_files:
        command = f"python manage.py loaddata {file_path}"
        if not run_command(command, description, task):
            return False
        task.progress += 1
        task.imported_count += 1
        # データベースロックを軽減するため、短い待機時間を追加
        time.sleep(0.1)
    
    return True


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
