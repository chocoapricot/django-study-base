"""
スタッフ管理側の外国籍情報申請機能のテスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from datetime import date, timedelta

from apps.profile.models import StaffProfile, StaffProfileInternational
from apps.connect.models import ConnectStaff, ConnectInternationalRequest
from apps.staff.models import Staff

User = get_user_model()


class StaffInternationalRequestViewTest(TestCase):
    """スタッフ管理側の外国籍情報申請ビューのテスト"""

    def setUp(self):
        self.client = Client()

        # 管理者ユーザー
        self.admin_user = User.objects.create_user(
            username='admin_view',
            email='admin_view@example.com',
            password='adminpass123'
        )

        # スタッフ権限を付与
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staff',
                'change_staff',
                'view_staffprofileinternational',
                'add_staffprofileinternational',
                'change_staffprofileinternational'
            ]
        )
        self.admin_user.user_permissions.set(permissions)

        # 申請者ユーザー
        self.staff_user = User.objects.create_user(
            username='staffuser_view',
            email='staff_view@example.com',
            password='staffpass123'
        )

        # スタッフマスター
        self.staff = Staff.objects.create(
            name_last='申請',
            name_first='太郎',
            name_kana_last='シンセイ',
            name_kana_first='タロウ',
            email='staff_view@example.com',
            regist_form_code=1,
            sex=1
        )

        # スタッフプロフィール
        self.staff_profile = StaffProfile.objects.create(
            user=self.staff_user,
            name_last='申請',
            name_first='太郎',
            name_kana_last='シンセイ',
            name_kana_first='タロウ',
            email='staff_view@example.com'
        )

        # 接続情報
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff_view@example.com',
            status='approved'
        )

        # 外国籍情報
        self.international_profile = StaffProfileInternational.objects.create(
            staff_profile=self.staff_profile,
            residence_card_number='REQUEST1234567890',
            residence_status='技術・人文知識・国際業務',
            residence_period_from=date.today(),
            residence_period_to=date.today() + timedelta(days=365)
        )

        # 外国籍情報申請
        self.international_request = ConnectInternationalRequest.objects.create(
            connect_staff=self.connect_staff,
            profile_international=self.international_profile,
            status='pending'
        )

        self.client.login(username='admin_view', password='adminpass123')

    def test_staff_detail_shows_international_request(self):
        """スタッフ詳細画面で外国籍情報申請が表示されるテスト"""
        response = self.client.get(reverse('staff:staff_detail', kwargs={'pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報申請')
        self.assertContains(response, '未承認')

    def test_international_request_detail_view(self):
        """外国籍情報申請詳細ビューのテスト"""
        response = self.client.get(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'REQUEST1234567890')
        self.assertContains(response, '技術・人文知識・国際業務')
        self.assertContains(response, '承認')
        self.assertContains(response, '却下')

    def test_international_request_approve(self):
        """外国籍情報申請承認のテスト"""
        response = self.client.post(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk}),
            data={'action': 'approve'}
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト

        # 申請が承認されているか確認
        self.international_request.refresh_from_db()
        self.assertEqual(self.international_request.status, 'approved')

    def test_international_request_reject(self):
        """外国籍情報申請却下のテスト"""
        response = self.client.post(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk}),
            data={'action': 'reject'}
        )
        self.assertEqual(response.status_code, 302)  # リダイレクト

        # 申請が却下されているか確認
        updated_request = ConnectInternationalRequest.objects.get(pk=self.international_request.pk)
        self.assertEqual(updated_request.status, 'rejected')

        # 関連する外国籍情報は削除されずに保持されているか確認
        self.assertTrue(
            StaffProfileInternational.objects.filter(pk=self.international_profile.pk).exists()
        )

    def test_international_request_detail_without_permission(self):
        """権限なしでの外国籍情報申請詳細アクセステスト"""
        # 権限を削除
        self.admin_user.user_permissions.clear()

        response = self.client.get(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': self.international_request.pk})
        )
        self.assertEqual(response.status_code, 403)  # 権限エラー

    def test_international_request_detail_nonexistent_request(self):
        """存在しない申請へのアクセステスト"""
        response = self.client.get(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)  # Not Found

    def test_international_request_detail_nonexistent_staff(self):
        """存在しないスタッフへのアクセステスト"""
        response = self.client.get(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': 99999, 'pk': self.international_request.pk})
        )
        self.assertEqual(response.status_code, 404)  # Not Found


class StaffInternationalRequestIntegrationTest(TestCase):
    """外国籍情報申請の統合テスト"""

    def setUp(self):
        self.client = Client()

        # 管理者ユーザー
        self.admin_user = User.objects.create_user(
            username='admin_integration',
            email='admin_integration@example.com',
            password='adminpass123'
        )

        # 必要な権限を付与
        admin_permissions = Permission.objects.filter(
            codename__in=[
                'view_staff',
                'change_staff',
                'view_staffprofileinternational',
                'add_staffprofileinternational',
                'change_staffprofileinternational'
            ]
        )
        self.admin_user.user_permissions.set(admin_permissions)

        # 申請者ユーザー
        self.staff_user = User.objects.create_user(
            username='staffuser_integration',
            email='staff_integration@example.com',
            password='staffpass123'
        )

        # 申請者権限を付与
        staff_permissions = Permission.objects.filter(
            codename__in=[
                'view_staffprofileinternational',
                'add_staffprofileinternational',
                'change_staffprofileinternational',
                'delete_staffprofileinternational'
            ]
        )
        self.staff_user.user_permissions.set(staff_permissions)

        # スタッフマスター
        self.staff = Staff.objects.create(
            name_last='統合',
            name_first='太郎',
            name_kana_last='トウゴウ',
            name_kana_first='タロウ',
            email='staff_integration@example.com',
            regist_form_code=1,
            sex=1
        )

        # スタッフプロフィール
        self.staff_profile = StaffProfile.objects.create(
            user=self.staff_user,
            name_last='統合',
            name_first='太郎',
            name_kana_last='トウゴウ',
            name_kana_first='タロウ',
            email='staff_integration@example.com'
        )

        # 接続情報
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='9876543210987',
            email='staff_integration@example.com',
            status='approved'
        )

    def test_full_international_request_workflow(self):
        """外国籍情報申請の完全なワークフローテスト"""
        # 1. スタッフユーザーでログインして申請
        self.client.login(username='staffuser_integration', password='staffpass123')

        form_data = {
            'residence_card_number': 'INTEGRATION1234567890',
            'residence_status': '特定活動',
            'residence_period_from': date.today().strftime('%Y-%m-%d'),
            'residence_period_to': (date.today() + timedelta(days=1095)).strftime('%Y-%m-%d')
        }

        response = self.client.post(reverse('profile:international_edit'), data=form_data)
        self.assertEqual(response.status_code, 302)

        # 2. データと申請が作成されているか確認
        international = StaffProfileInternational.objects.get(staff_profile=self.staff_profile)
        self.assertEqual(international.residence_card_number, 'INTEGRATION1234567890')

        request = ConnectInternationalRequest.objects.get(connect_staff=self.connect_staff)
        self.assertEqual(request.profile_international, international)
        self.assertEqual(request.status, 'pending')

        # 3. 管理者でログインして申請確認
        self.client.login(username='admin_integration', password='adminpass123')

        response = self.client.get(reverse('staff:staff_detail', kwargs={'pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '外国籍情報申請')

        # 4. 申請詳細確認
        response = self.client.get(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': request.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'INTEGRATION1234567890')
        self.assertContains(response, '特定活動')

        # 5. 申請承認
        response = self.client.post(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': request.pk}),
            data={'action': 'approve'}
        )
        self.assertEqual(response.status_code, 302)

        # 6. 承認されているか確認
        request.refresh_from_db()
        self.assertEqual(request.status, 'approved')

        # 7. スタッフ詳細で申請が表示されなくなっているか確認
        response = self.client.get(reverse('staff:staff_detail', kwargs={'pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        # 承認済みの申請は表示されない（pendingのみ表示）
        self.assertNotContains(response, '外国籍情報申請')

    def test_international_request_rejection_workflow(self):
        """外国籍情報申請却下ワークフローテスト"""
        # 1. スタッフユーザーでログインして申請
        self.client.login(username='staffuser_integration', password='staffpass123')

        form_data = {
            'residence_card_number': 'REJECT1234567890',
            'residence_status': '研修',
            'residence_period_from': date.today().strftime('%Y-%m-%d'),
            'residence_period_to': (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
        }

        response = self.client.post(reverse('profile:international_edit'), data=form_data)
        self.assertEqual(response.status_code, 302)

        # 2. 申請を取得
        request = ConnectInternationalRequest.objects.get(connect_staff=self.connect_staff)
        international_pk = request.profile_international.pk

        # 3. 管理者でログインして申請却下
        self.client.login(username='admin_integration', password='adminpass123')

        response = self.client.post(
            reverse('staff:staff_international_request_detail',
                   kwargs={'staff_pk': self.staff.pk, 'pk': request.pk}),
            data={'action': 'reject'}
        )
        self.assertEqual(response.status_code, 302)

        # 4. 申請が却下され、外国籍情報は保持されているか確認
        # 申請レコードが存在するか確認
        self.assertTrue(
            ConnectInternationalRequest.objects.filter(pk=request.pk).exists()
        )

        # 申請ステータスを確認
        updated_request = ConnectInternationalRequest.objects.get(pk=request.pk)
        self.assertEqual(updated_request.status, 'rejected')

        # 外国籍情報は削除されずに保持されているか確認
        self.assertTrue(
            StaffProfileInternational.objects.filter(pk=international_pk).exists()
        )