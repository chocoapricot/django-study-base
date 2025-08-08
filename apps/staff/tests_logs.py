from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.staff.models import Staff, StaffQualification, StaffSkill, StaffFile
from apps.master.models import Qualification, Skill
from apps.system.logs.models import AppLog
from apps.system.settings.models import Dropdowns

User = get_user_model()

class StaffLogsTestCase(TestCase):
    def setUp(self):
        """テスト用データの準備"""
        # テスト用ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staff', 'add_staff', 'change_staff', 'delete_staff',
                'view_staffqualification', 'add_staffqualification', 'change_staffqualification', 'delete_staffqualification',
                'view_staffskill', 'add_staffskill', 'change_staffskill', 'delete_staffskill',
                'view_stafffile', 'add_stafffile', 'change_stafffile', 'delete_stafffile'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用ドロップダウン作成
        Dropdowns.objects.create(
            category='sex',
            value='1',
            name='男性',
            active=True,
            disp_seq=1
        )
        
        Dropdowns.objects.create(
            category='regist_form',
            value='1',
            name='正社員',
            active=True,
            disp_seq=1
        )
        
        # テスト用スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            sex=1,
            regist_form_code=1,
            email='staff@example.com'
        )
        
        # テスト用資格・技能作成
        self.qualification_category = Qualification.objects.create(
            name='IT資格',
            level=1,
            is_active=True,
            display_order=1
        )
        
        self.qualification = Qualification.objects.create(
            name='基本情報技術者',
            level=2,
            parent=self.qualification_category,
            is_active=True,
            display_order=1
        )
        
        self.skill_category = Skill.objects.create(
            name='プログラミング',
            level=1,
            is_active=True,
            display_order=1
        )
        
        self.skill = Skill.objects.create(
            name='Python',
            level=2,
            parent=self.skill_category,
            is_active=True,
            display_order=1
        )
        
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_staff_qualification_log(self):
        """スタッフ資格のログ記録テスト"""
        # 資格追加前のログ数を記録
        initial_log_count = AppLog.objects.filter(model_name='StaffQualification').count()
        
        # 資格追加
        staff_qualification = StaffQualification.objects.create(
            staff=self.staff,
            qualification=self.qualification,
            acquired_date='2024-01-01'
        )
        
        # ログが作成されたことを確認（少なくとも1つ以上）
        self.assertGreater(AppLog.objects.filter(model_name='StaffQualification').count(), initial_log_count)
        
        # 最新のログを確認
        latest_log = AppLog.objects.latest('timestamp')
        self.assertEqual(latest_log.action, 'create')
        self.assertEqual(latest_log.model_name, 'StaffQualification')
        self.assertEqual(latest_log.object_id, str(staff_qualification.pk))
        
        # 資格更新
        staff_qualification.score = 800
        staff_qualification.save()
        
        # 更新ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='StaffQualification', action='update').count(), 0)
        
        # 資格削除
        staff_qualification.delete()
        
        # 削除ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='StaffQualification', action='delete').count(), 0)
        
        # 削除ログを確認
        delete_log = AppLog.objects.latest('timestamp')
        self.assertEqual(delete_log.action, 'delete')
        self.assertEqual(delete_log.model_name, 'StaffQualification')
    
    def test_staff_skill_log(self):
        """スタッフ技能のログ記録テスト"""
        initial_log_count = AppLog.objects.filter(model_name='StaffSkill').count()
        
        # 技能追加
        staff_skill = StaffSkill.objects.create(
            staff=self.staff,
            skill=self.skill,
            acquired_date='2024-01-01',
            years_of_experience=3
        )
        
        # ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='StaffSkill').count(), initial_log_count)
        
        # 最新のログを確認
        latest_log = AppLog.objects.latest('timestamp')
        self.assertEqual(latest_log.action, 'create')
        self.assertEqual(latest_log.model_name, 'StaffSkill')
        self.assertEqual(latest_log.object_id, str(staff_skill.pk))
    
    def test_staff_file_log(self):
        """スタッフファイルのログ記録テスト"""
        initial_log_count = AppLog.objects.filter(model_name='StaffFile').count()
        
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        # ファイル追加
        staff_file = StaffFile.objects.create(
            staff=self.staff,
            file=test_file,
            description="テストファイル"
        )
        
        # ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='StaffFile').count(), initial_log_count)
        
        # 最新のログを確認
        latest_log = AppLog.objects.latest('timestamp')
        self.assertEqual(latest_log.action, 'create')
        self.assertEqual(latest_log.model_name, 'StaffFile')
        self.assertEqual(latest_log.object_id, str(staff_file.pk))
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for staff_file in StaffFile.objects.all():
            if staff_file.file:
                try:
                    staff_file.file.delete()
                except:
                    pass