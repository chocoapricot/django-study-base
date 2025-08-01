# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.system.logs.models import AppLog
from apps.system.logs.utils import log_model_action, log_view_detail, log_user_action

User = get_user_model()


class Command(BaseCommand):
    help = 'AppLogのテストデータを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='作成するログの数（デフォルト: 10）'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # テスト用ユーザーを取得（存在しない場合は最初のユーザーを使用）
        user = User.objects.first()
        if not user:
            self.stdout.write(
                self.style.ERROR('ユーザーが存在しません。先にユーザーを作成してください。')
            )
            return

        self.stdout.write(f'テストユーザー: {user.username}')
        
        # テストデータを作成
        created_count = 0
        
        for i in range(count):
            # 様々なアクションのテストログを作成
            actions = ['create', 'update', 'delete', 'view', 'login', 'logout']
            models = ['User', 'Staff', 'Client', 'TestModel']
            
            action = actions[i % len(actions)]
            model_name = models[i % len(models)]
            
            AppLog.objects.create(
                user=user,
                action=action,
                model_name=model_name,
                object_id=str(i + 1),
                object_repr=f'テスト{model_name}#{i + 1}の{action}操作',
                version=i + 1 if action in ['create', 'update'] else None
            )
            created_count += 1

        # ユーティリティ関数のテスト
        class DummyModel:
            def __init__(self, pk, name):
                self.pk = pk
                self.name = name
            
            def __str__(self):
                return self.name

        # テスト用ダミーオブジェクト
        dummy_obj = DummyModel(999, 'テストオブジェクト')
        
        # ユーティリティ関数を使用してログを作成
        log_model_action(user, 'create', dummy_obj, version=1)
        log_view_detail(user, dummy_obj)
        log_user_action(user, 'login', 'テストログイン操作')
        
        created_count += 3

        self.stdout.write(
            self.style.SUCCESS(
                f'正常に{created_count}件のAppLogテストデータを作成しました。'
            )
        )
        
        # 作成されたログの確認
        total_logs = AppLog.objects.count()
        self.stdout.write(f'現在のAppLog総数: {total_logs}件')
        
        # 最新の5件を表示
        recent_logs = AppLog.objects.order_by('-timestamp')[:5]
        self.stdout.write('\n最新の5件:')
        for log in recent_logs:
            self.stdout.write(f'  - {log}')