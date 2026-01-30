from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffContact
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date

User = get_user_model()

class StaffContactViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        # StaffContactモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(StaffContact)
        # 必要な権限をユーザーに付与
        self.view_perm, _ = Permission.objects.get_or_create(codename='view_staffcontact', content_type=content_type)
        self.add_perm, _ = Permission.objects.get_or_create(codename='add_staffcontact', content_type=content_type)
        self.change_perm, _ = Permission.objects.get_or_create(codename='change_staffcontact', content_type=content_type)
        self.delete_perm, _ = Permission.objects.get_or_create(codename='delete_staffcontact', content_type=content_type)

        staff_content_type = ContentType.objects.get_for_model(Staff)
        self.view_staff_perm, _ = Permission.objects.get_or_create(codename='view_staff', content_type=staff_content_type)


        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm, self.view_staff_perm)

        # テスト用スタッフデータを作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            birth_date=date(1990, 1, 1),
            sex=1,
        )

    def test_contact_create_view_get(self):
        """登録画面へのGETリクエストが成功することをテスト"""
        response = self.client.get(reverse('staff:staff_contact_create', kwargs={'staff_id': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contact_form.html')

    def test_contact_create_view_post(self):
        """登録処理が成功することをテスト"""
        data = {
            'emergency_contact': '090-1234-5678',
            'relationship': '父',
            'postal_code': '1234567',
            'address1': '東京都',
            'address2': 'テスト区',
            'address3': 'テストビル101',
        }
        response = self.client.post(reverse('staff:staff_contact_create', kwargs={'staff_id': self.staff.pk}), data)
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        self.assertTrue(StaffContact.objects.filter(staff=self.staff).exists())
        contact = StaffContact.objects.get(staff=self.staff)
        self.assertEqual(contact.emergency_contact, '090-1234-5678')
        self.assertEqual(contact.relationship, '父')

    def test_contact_detail_view(self):
        """詳細画面へのGETリクエストが成功することをテスト"""
        contact = StaffContact.objects.create(
            staff=self.staff,
            emergency_contact='090-1111-2222',
            relationship='母'
        )
        response = self.client.get(reverse('staff:staff_contact_detail', kwargs={'staff_id': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contact_detail.html')
        self.assertContains(response, '090-1111-2222')
        self.assertContains(response, '母')

    def test_contact_edit_view_get(self):
        """編集画面へのGETリクエストが成功することをテスト"""
        contact = StaffContact.objects.create(
            staff=self.staff,
            emergency_contact='090-3333-4444',
            relationship='兄'
        )
        response = self.client.get(reverse('staff:staff_contact_edit', kwargs={'staff_id': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contact_form.html')
        self.assertContains(response, '090-3333-4444')

    def test_contact_edit_view_post(self):
        """更新処理が成功することをテスト"""
        contact = StaffContact.objects.create(
            staff=self.staff,
            emergency_contact='090-5555-6666',
            relationship='姉'
        )
        data = {
            'emergency_contact': '090-7777-8888',
            'relationship': '祖父',
            'postal_code': '7654321',
            'address1': '大阪府',
            'address2': 'テスト市',
            'address3': 'テストアパート202',
        }
        response = self.client.post(reverse('staff:staff_contact_edit', kwargs={'staff_id': self.staff.pk}), data)
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        contact.refresh_from_db()
        self.assertEqual(contact.emergency_contact, '090-7777-8888')
        self.assertEqual(contact.relationship, '祖父')

    def test_contact_delete_view_post(self):
        """削除処理が成功することをテスト"""
        contact = StaffContact.objects.create(
            staff=self.staff,
            emergency_contact='090-9999-0000',
            relationship='祖母'
        )
        response = self.client.post(reverse('staff:staff_contact_delete', kwargs={'staff_id': self.staff.pk}))
        self.assertEqual(response.status_code, 302) # スタッフ詳細ページへリダイレクト
        self.assertFalse(StaffContact.objects.filter(pk=contact.pk).exists())
