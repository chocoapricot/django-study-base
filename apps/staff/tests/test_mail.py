from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from ..models import Staff, StaffContacted
from ...master.models import StaffRegistStatus, EmploymentType
from ...system.logs.models import MailLog
from ..forms_mail import StaffMailForm
from ...system.notifications.models import Notification
from ...system.settings.models import Dropdowns

User = get_user_model()


class StaffMailTest(TestCase):
    """スタッフメール送信機能のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # スタッフ閲覧権限を付与
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_staff')
        self.user.user_permissions.add(permission)
        
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
        
        # 連絡種別のドロップダウンを作成（StaffMailForm内部で使用）
        Dropdowns.objects.get_or_create(category='contact_type', value='50', defaults={'name': 'メール', 'active': True, 'disp_seq': 1})

        self.staff_email = 'tanaka@example.com'
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email=self.staff_email,
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            created_by=self.user,
            updated_by=self.user
        )
        
        # スタッフに対応するユーザーを作成
        self.staff_user = User.objects.create_user(
            username='staff_user_login',
            email=self.staff_email,
            password='password'
        )

        self.staff_no_email = Staff.objects.create(
            name_last='佐藤',
            name_first='花子',
            name_kana_last='サトウ',
            name_kana_first='ハナコ',
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_staff_mail_send_view_with_email(self):
        """メールアドレスありのスタッフのメール送信画面表示テスト"""
        url = reverse('staff:staff_mail_send', kwargs={'pk': self.staff.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '田中 太郎 へのメール送信')
        self.assertContains(response, 'tanaka@example.com')
    
    def test_staff_mail_send_view_without_email(self):
        """メールアドレスなしのスタッフのメール送信画面アクセステスト"""
        url = reverse('staff:staff_mail_send', kwargs={'pk': self.staff_no_email.pk})
        response = self.client.get(url)
        
        # メールアドレスがない場合はリダイレクトされる
        self.assertEqual(response.status_code, 302)
    
    def test_staff_mail_form_valid_data(self):
        """メール送信フォームの正常データテスト"""
        form_data = {
            'to_email': 'tanaka@example.com',
            'subject': 'テストメール',
            'body': 'これはテストメールです。',
            'send_notification': True,
        }
        
        form = StaffMailForm(staff=self.staff, user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_staff_mail_form_invalid_email(self):
        """メール送信フォームの不正なメールアドレステスト"""
        form_data = {
            'to_email': 'wrong@example.com',  # スタッフのメールアドレスと異なる
            'subject': 'テストメール',
            'body': 'これはテストメールです。',
            'send_notification': True,
        }
        
        form = StaffMailForm(staff=self.staff, user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('宛先メールアドレスが正しくありません', str(form.errors))
    
    def test_mail_send_success(self):
        """メール送信成功テスト"""
        form_data = {
            'to_email': 'tanaka@example.com',
            'subject': 'テストメール',
            'body': 'これはテストメールです。',
            'send_notification': True,
        }
        
        form = StaffMailForm(staff=self.staff, user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
        
        success, message = form.send_mail()
        self.assertTrue(success)
        self.assertEqual(message, "メールを送信しました。")
        
        # メールが送信されたかチェック
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.subject, 'テストメール')
        self.assertEqual(sent_mail.to, ['tanaka@example.com'])
        
        # メールログが作成されたかチェック
        mail_log = MailLog.objects.filter(to_email='tanaka@example.com').first()
        self.assertIsNotNone(mail_log)
        self.assertEqual(mail_log.status, 'sent')
        self.assertEqual(mail_log.subject, 'テストメール')
        
        # 連絡履歴が作成されたかチェック
        contact_history = StaffContacted.objects.filter(staff=self.staff).first()
        self.assertIsNotNone(contact_history)
        self.assertIn('メール送信: テストメール', contact_history.content)

        # 通知が作成されたかチェック（新規追加分）
        self.assertEqual(Notification.objects.filter(user=self.staff_user).count(), 1)
    
    def test_mail_send_without_contact_history(self):
        """連絡履歴保存なしのメール送信テスト（現在は常に保存されるため、保存されることを確認）"""
        form_data = {
            'to_email': 'tanaka@example.com',
            'subject': 'テストメール',
            'body': 'これはテストメールです。',
            'send_notification': False,
        }
        
        form = StaffMailForm(staff=self.staff, user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
        
        success, message = form.send_mail()
        self.assertTrue(success)
        
        # メールログは作成される
        mail_log = MailLog.objects.filter(to_email='tanaka@example.com').first()
        self.assertIsNotNone(mail_log)
        
        # 連絡履歴は常に作成される（仕様変更）
        contact_history = StaffContacted.objects.filter(staff=self.staff).first()
        self.assertIsNotNone(contact_history)

        # 通知は作成されない（send_notification=Falseのため）
        self.assertEqual(Notification.objects.filter(user=self.staff_user).count(), 0)
    
    def test_staff_mail_send_post(self):
        """メール送信POSTリクエストテスト"""
        url = reverse('staff:staff_mail_send', kwargs={'pk': self.staff.pk})
        
        post_data = {
            'to_email': 'tanaka@example.com',
            'subject': 'テストメール',
            'body': 'これはテストメールです。',
            'send_notification': True,
        }
        
        response = self.client.post(url, post_data)
        
        # 送信成功後はスタッフ詳細画面にリダイレクト
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('staff:staff_detail', kwargs={'pk': self.staff.pk}))
        
        # メールが送信されたかチェック
        self.assertEqual(len(mail.outbox), 1)
        
        # メールログが作成されたかチェック
        self.assertTrue(MailLog.objects.filter(to_email='tanaka@example.com').exists())
        
        # 連絡履歴が作成されたかチェック
        self.assertTrue(StaffContacted.objects.filter(staff=self.staff).exists())

        # 通知が作成されたかチェック
        self.assertEqual(Notification.objects.filter(user=self.staff_user).count(), 1)

    def test_mail_send_page_renders_notification_checkbox(self):
        """メール送信ページに通知チェックボックスが表示されることを確認"""
        url = reverse('staff:staff_mail_send', args=[self.staff.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="send_notification"')
        self.assertContains(response, '通知を送る')

    def test_mail_send_does_not_fail_if_user_not_exists(self):
        """ユーザーが存在しない場合でもエラーにならず、通知だけ作成されないことを確認"""
        # ユーザーが存在しない別のスタッフを作成
        other_staff = Staff.objects.create(
            name_last='山田',
            name_first='二郎',
            email='no_user@example.com',
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('staff:staff_mail_send', args=[other_staff.pk])
        data = {
            'to_email': 'no_user@example.com',
            'subject': 'ユーザーなし',
            'body': '本文',
            'send_notification': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # 通知が作成されていないことを確認（ユーザーがいないので）
        self.assertEqual(Notification.objects.filter(title='ユーザーなし').count(), 0)
