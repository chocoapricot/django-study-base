from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.master.views import master_index_list, get_category_count, get_data_count
from apps.master.models import Qualification, Skill

User = get_user_model()

class Command(BaseCommand):
    help = 'マスタ一覧ビューのテスト'

    def handle(self, *args, **options):
        self.stdout.write('マスタ一覧ビューのテスト開始...')
        
        # テストユーザーを作成または取得
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # テストデータを作成
        # 資格カテゴリとデータ
        qual_category, created = Qualification.objects.get_or_create(
            name='テスト資格カテゴリ',
            level=1,
            defaults={
                'description': 'テスト用の資格カテゴリ',
                'created_by': user,
                'updated_by': user
            }
        )
        
        qual1, created = Qualification.objects.get_or_create(
            name='テスト資格1',
            level=2,
            parent=qual_category,
            defaults={
                'description': 'テスト用の資格1',
                'created_by': user,
                'updated_by': user
            }
        )
        
        # 技能カテゴリとデータ
        skill_category, created = Skill.objects.get_or_create(
            name='テスト技能カテゴリ',
            level=1,
            defaults={
                'description': 'テスト用の技能カテゴリ',
                'created_by': user,
                'updated_by': user
            }
        )
        
        skill1, created = Skill.objects.get_or_create(
            name='テスト技能1',
            level=2,
            parent=skill_category,
            defaults={
                'description': 'テスト用の技能1',
                'created_by': user,
                'updated_by': user
            }
        )
        
        # データ集計関数のテスト
        self.stdout.write('データ集計関数のテスト:')
        qual_category_count = get_category_count(Qualification)
        qual_data_count = get_data_count(Qualification)
        skill_category_count = get_category_count(Skill)
        skill_data_count = get_data_count(Skill)
        
        self.stdout.write(f'  資格カテゴリ数: {qual_category_count}')
        self.stdout.write(f'  資格データ数: {qual_data_count}')
        self.stdout.write(f'  技能カテゴリ数: {skill_category_count}')
        self.stdout.write(f'  技能データ数: {skill_data_count}')
        
        # リクエストファクトリーを使用してビューをテスト
        factory = RequestFactory()
        request = factory.get('/master/')
        request.user = user
        
        try:
            response = master_index_list(request)
            self.stdout.write(f'ビューレスポンス: {response.status_code}')
            
            if hasattr(response, 'context_data') and response.context_data:
                masters = response.context_data.get('masters', [])
                self.stdout.write(f'マスタ数: {len(masters)}')
                for master in masters:
                    self.stdout.write(f'  - {master["name"]}: カテゴリ{master["category_count"]}件, データ{master["data_count"]}件')
            else:
                self.stdout.write('コンテキストデータが取得できませんでした')
                
        except Exception as e:
            self.stdout.write(f'エラー: {e}')
        
        self.stdout.write('テスト完了')