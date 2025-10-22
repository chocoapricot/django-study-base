from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.staff.models import Staff, StaffBank, StaffContact, StaffDisability, StaffMynumber, StaffInternational, StaffQualification, StaffSkill, StaffFile
from apps.master.models import Qualification, Skill, StaffRegistStatus, EmploymentType
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
        
        
        # マスターデータを作成
        self.regist_status = StaffRegistStatus.objects.create(
            name='正社員',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            sex=1,
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用資格・技能作成
        self.qualification_category = Qualification.objects.create(
            name='IT資格',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.qualification = Qualification.objects.create(
            name='基本情報技術者',
            level=2,
            parent=self.qualification_category,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.skill_category = Skill.objects.create(
            name='プログラミング',
            level=1,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.skill = Skill.objects.create(
            name='Python',
            level=2,
            parent=self.skill_category,
            is_active=True,
            display_order=1,
            created_by=self.user,
            updated_by=self.user
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
    
    def test_staff_bank_log(self):
        """スタッフ銀行情報のログ記録テスト"""
        # 銀行情報作成
        staff_bank = StaffBank.objects.create(
            staff=self.staff, bank_code='1234', branch_code='567',
            account_type='普通', account_number='1234567', account_holder='テスト タロウ'
        )
        # 作成ログが記録されていることを確認
        create_logs = AppLog.objects.filter(model_name='StaffBank', object_id=str(staff_bank.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)

        # 銀行情報を更新
        staff_bank.account_holder = 'テスト ジロウ'
        staff_bank.save()

        # 更新ログが記録されていることを確認
        update_logs = AppLog.objects.filter(model_name='StaffBank', object_id=str(staff_bank.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)

        # 更新ログの内容を確認（差分が含まれているログがあるか）
        diff_log_exists = any("口座名義" in log.object_repr for log in update_logs)
        self.assertTrue(diff_log_exists, "差分情報を含む更新ログが見つかりませんでした。")

    def test_staff_contact_log(self):
        """スタッフ連絡先情報のログ記録テスト"""
        staff_contact = StaffContact.objects.create(
            staff=self.staff, emergency_contact='090-1234-5678', relationship='父'
        )
        create_logs = AppLog.objects.filter(model_name='StaffContact', object_id=str(staff_contact.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)

        staff_contact.emergency_contact = '090-8765-4321'
        staff_contact.save()

        update_logs = AppLog.objects.filter(model_name='StaffContact', object_id=str(staff_contact.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)
        diff_log_exists = any("緊急連絡先" in log.object_repr for log in update_logs)
        self.assertTrue(diff_log_exists, "差分情報を含む更新ログが見つかりませんでした。")

    def test_staff_disability_log(self):
        """スタッフ障害者情報のログ記録テスト"""
        Dropdowns.objects.create(category='disability_type', value='physical', name='身体障害', active=True)
        staff_disability = StaffDisability.objects.create(
            staff=self.staff, disability_type='physical', disability_grade='1級'
        )
        create_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(staff_disability.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)

        staff_disability.disability_grade = '2級'
        staff_disability.save()

        update_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(staff_disability.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)
        diff_log_exists = any("等級" in log.object_repr for log in update_logs)
        self.assertTrue(diff_log_exists, "差分情報を含む更新ログが見つかりませんでした。")

        # 削除テスト
        disability_pk = staff_disability.pk
        staff_disability.delete()

        delete_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(disability_pk), action='delete')
        self.assertGreaterEqual(delete_logs.count(), 1)
        
        # 削除ログにスタッフ名が含まれていることを確認
        delete_log = delete_logs.first()
        self.assertIn(str(self.staff), delete_log.object_repr, "削除ログにスタッフ名が含まれていません。")

    def test_staff_mynumber_log(self):
        """スタッフマイナンバーのログ記録テスト"""
        staff_mynumber = StaffMynumber.objects.create(
            staff=self.staff, mynumber='123456789012'
        )
        create_logs = AppLog.objects.filter(model_name='StaffMynumber', object_id=str(staff_mynumber.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)

        staff_mynumber.mynumber = '210987654321'
        staff_mynumber.save()

        update_logs = AppLog.objects.filter(model_name='StaffMynumber', object_id=str(staff_mynumber.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)
        diff_log_exists = any("マイナンバー" in log.object_repr for log in update_logs)
        self.assertTrue(diff_log_exists, "差分情報を含む更新ログが見つかりませんでした。")

    def test_staff_international_log(self):
        """スタッフ外国籍情報のログ記録テスト"""
        from datetime import date
        staff_international = StaffInternational.objects.create(
            staff=self.staff, residence_card_number='AB123456CD', residence_status='Engineer',
            residence_period_from=date(2023, 1, 1), residence_period_to=date(2025, 1, 1)
        )
        create_logs = AppLog.objects.filter(model_name='StaffInternational', object_id=str(staff_international.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)

        staff_international.residence_status = 'Highly Skilled Professional'
        staff_international.save()

        update_logs = AppLog.objects.filter(model_name='StaffInternational', object_id=str(staff_international.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)
        diff_log_exists = any("在留資格" in log.object_repr for log in update_logs)
        self.assertTrue(diff_log_exists, "差分情報を含む更新ログが見つかりませんでした。")

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for staff_file in StaffFile.objects.all():
            if staff_file.file:
                try:
                    staff_file.file.delete()
                except:
                    pass

    def test_staff_detail_change_logs_include_deleted(self):
        """スタッフ詳細画面の変更履歴に削除されたオブジェクトのログが含まれることをテスト"""
        # 障害者情報を作成
        Dropdowns.objects.create(category='disability_type', value='physical', name='身体障害', active=True)
        staff_disability = StaffDisability.objects.create(
            staff=self.staff, disability_type='physical', disability_grade='1級'
        )
        
        # 作成ログが記録されることを確認
        create_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(staff_disability.pk), action='create')
        self.assertGreaterEqual(create_logs.count(), 1)
        
        # 障害者情報を更新
        staff_disability.disability_grade = '2級'
        staff_disability.save()
        
        # 更新ログが記録されることを確認
        update_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(staff_disability.pk), action='update')
        self.assertGreaterEqual(update_logs.count(), 1)
        
        # 障害者情報を削除
        disability_pk = staff_disability.pk
        staff_disability.delete()
        
        # 削除ログが記録されることを確認
        delete_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(disability_pk), action='delete')
        self.assertGreaterEqual(delete_logs.count(), 1)
        
        # スタッフ詳細画面のビューロジックをシミュレート
        from django.db import models as django_models
        
        # 現在存在する関連オブジェクトのIDリストを取得（削除後なので空）
        qualification_ids = list(self.staff.qualifications.values_list('pk', flat=True))
        skill_ids = list(self.staff.skills.values_list('pk', flat=True))
        file_ids = list(self.staff.files.values_list('pk', flat=True))

        # 1対1の関連オブジェクトのIDを取得（削除後なのでNone）
        mynumber_id = getattr(self.staff, 'mynumber', None) and self.staff.mynumber.pk
        contact_id = getattr(self.staff, 'contact', None) and self.staff.contact.pk
        bank_id = getattr(self.staff, 'bank', None) and self.staff.bank.pk
        international_id = getattr(self.staff, 'international', None) and self.staff.international.pk
        disability_id = getattr(self.staff, 'disability', None) and self.staff.disability.pk
        payroll_id = getattr(self.staff, 'payroll', None) and self.staff.payroll.pk

        # 修正後のクエリロジック（削除されたオブジェクトのIDを事前に取得）
        deleted_object_ids = {}
        for model_name in ['StaffQualification', 'StaffSkill', 'StaffFile', 'StaffMynumber', 
                           'StaffContact', 'StaffBank', 'StaffInternational', 'StaffDisability', 'StaffPayroll']:
            deleted_logs = AppLog.objects.filter(
                model_name=model_name,
                object_repr__icontains=str(self.staff),
                action='delete'
            ).values_list('object_id', flat=True)
            if deleted_logs:
                deleted_object_ids[model_name] = list(deleted_logs)
        
        # 現在存在するオブジェクトのIDと削除されたオブジェクトのIDを統合
        all_qualification_ids = [str(pk) for pk in qualification_ids] + deleted_object_ids.get('StaffQualification', [])
        all_skill_ids = [str(pk) for pk in skill_ids] + deleted_object_ids.get('StaffSkill', [])
        all_file_ids = [str(pk) for pk in file_ids] + deleted_object_ids.get('StaffFile', [])
        all_mynumber_ids = ([str(mynumber_id)] if mynumber_id else []) + deleted_object_ids.get('StaffMynumber', [])
        all_contact_ids = ([str(contact_id)] if contact_id else []) + deleted_object_ids.get('StaffContact', [])
        all_bank_ids = ([str(bank_id)] if bank_id else []) + deleted_object_ids.get('StaffBank', [])
        all_international_ids = ([str(international_id)] if international_id else []) + deleted_object_ids.get('StaffInternational', [])
        all_disability_ids = ([str(disability_id)] if disability_id else []) + deleted_object_ids.get('StaffDisability', [])
        all_payroll_ids = ([str(payroll_id)] if payroll_id else []) + deleted_object_ids.get('StaffPayroll', [])
        
        change_logs_query = AppLog.objects.filter(
            django_models.Q(model_name='Staff', object_id=str(self.staff.pk)) |
            django_models.Q(model_name='StaffQualification', object_id__in=all_qualification_ids) |
            django_models.Q(model_name='StaffSkill', object_id__in=all_skill_ids) |
            django_models.Q(model_name='StaffFile', object_id__in=all_file_ids) |
            django_models.Q(model_name='StaffMynumber', object_id__in=all_mynumber_ids) |
            django_models.Q(model_name='StaffContact', object_id__in=all_contact_ids) |
            django_models.Q(model_name='StaffBank', object_id__in=all_bank_ids) |
            django_models.Q(model_name='StaffInternational', object_id__in=all_international_ids) |
            django_models.Q(model_name='StaffDisability', object_id__in=all_disability_ids) |
            django_models.Q(model_name='StaffPayroll', object_id__in=all_payroll_ids) |
            django_models.Q(model_name='ConnectStaff', object_id=str(self.staff.pk)),
            action__in=['create', 'update', 'delete']
        )

        change_logs = change_logs_query.order_by('-timestamp')
        
        
        # 削除されたオブジェクトのすべてのログが含まれていることを確認
        disability_logs = [log for log in change_logs if log.model_name == 'StaffDisability']
        disability_create_logs = [log for log in disability_logs if log.action == 'create']
        disability_update_logs = [log for log in disability_logs if log.action == 'update']
        disability_delete_logs = [log for log in disability_logs if log.action == 'delete']
        
        self.assertGreater(len(disability_create_logs), 0, "削除された障害者情報の作成ログが変更履歴に含まれていません。")
        self.assertGreater(len(disability_update_logs), 0, "削除された障害者情報の更新ログが変更履歴に含まれていません。")
        self.assertGreater(len(disability_delete_logs), 0, "削除された障害者情報の削除ログが変更履歴に含まれていません。")
        
        # 各ログの内容を確認
        create_log = disability_create_logs[0]
        update_log = disability_update_logs[0]
        delete_log = disability_delete_logs[0]
        
        self.assertIn(str(self.staff), create_log.object_repr, "作成ログにスタッフ名が含まれていません。")
        self.assertIn("等級", update_log.object_repr, "更新ログに変更内容が含まれていません。")
        self.assertIn(str(self.staff), delete_log.object_repr, "削除ログにスタッフ名が含まれていません。")

    def test_staff_change_history_list_include_deleted(self):
        """スタッフ変更履歴一覧画面に削除されたオブジェクトのログが含まれることをテスト"""
        # 障害者情報を作成
        Dropdowns.objects.create(category='disability_type', value='physical', name='身体障害', active=True)
        staff_disability = StaffDisability.objects.create(
            staff=self.staff, disability_type='physical', disability_grade='1級'
        )
        
        # 障害者情報を削除
        disability_pk = staff_disability.pk
        staff_disability.delete()
        
        # 削除ログが記録されることを確認
        delete_logs = AppLog.objects.filter(model_name='StaffDisability', object_id=str(disability_pk), action='delete')
        self.assertGreaterEqual(delete_logs.count(), 1)
        
        # スタッフ変更履歴一覧ビューをテスト
        from django.urls import reverse
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('staff:staff_change_history_list', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        
        # レスポンスのコンテキストから変更履歴を取得
        change_logs = response.context['change_logs']
        
        # 削除ログが含まれていることを確認
        disability_delete_logs = [log for log in change_logs if log.model_name == 'StaffDisability' and log.action == 'delete']
        self.assertGreater(len(disability_delete_logs), 0, "変更履歴一覧に削除された障害者情報のログが含まれていません。")
        
        # 削除ログにスタッフ名が含まれていることを確認
        delete_log = disability_delete_logs[0]
        self.assertIn(str(self.staff), delete_log.object_repr, "削除ログにスタッフ名が含まれていません。")